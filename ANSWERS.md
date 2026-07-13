# Assessment Technical Answers


---

## 1. Async Failure Modes of Thread-Locals (Section 3)

### Why do thread-locals leak under async/ASGI views?
In a synchronous WSGI application, Django maps each request to a single dedicated Operating System (OS) thread. The request lifecycle starts and ends on the same thread, making `threading.local()` safe for isolating request context.

However, in an asynchronous ASGI application:
1. **Single Thread Interleaving**: A single OS thread runs an event loop that schedules many concurrent coroutines (async tasks).
2. **Task Switching**: When a coroutine pauses at an `await` statement, the event loop yields control and runs another coroutine on that same OS thread.
3. **Leaked State**: If coroutine A stores its tenant context in a `threading.local()`, coroutine B (running on the same thread during A's pause) will read A's context, leaking isolation.

### The Solution: `contextvars`
Python's `contextvars.ContextVar` is designed for async execution.
- When an async task starts, Python copies the current context.
- Modifications made within a task are isolated to that task and its descendants.
- When a task pauses, its context is swapped out, ensuring that concurrently interleaved tasks cannot read or overwrite each other's variables.

---

## 2. The N+1 Query Twist & DB Joins (Section 1)

### How can a "no code change" deployment trigger an N+1 performance incident?
A view containing an N+1 query pattern can remain undiscovered for a long time under low-volume conditions. However, the system can break suddenly due to:
1. **Data Volume Growth**: If a user previously had 3 orders, the view executed $1 + 2(3) = 7$ queries (fast). If a database migration, bulk upload, or customer activity increases orders to 250, the view suddenly executes $1 + 2(250) = 501$ queries, resulting in database connection exhaustion or gateway timeouts.
2. **Fixture/Seed Changes**: A test database or staging environment with a small dataset hides N+1 queries. A seed update that inflates relations immediately causes timeouts.
3. **Unrelated Model Modifications**: If an unrelated developer adds a new field or a custom property to the `Customer` model (e.g. fetching a profile picture or a preference list via a lazy DB lookup), and that property is accessed in the serializer, a previously harmless view becomes an N+1 query.

### SQL-Level Database Joins
- **`select_related` (SQL JOIN)**: Performs an `INNER JOIN` or `LEFT OUTER JOIN` at the database level. The database joins the tables and returns a single unified result set in **one query**. Best suited for single-value relationships (foreign key or one-to-one).
- **`prefetch_related` (Separate Subquery)**: Performs a separate SQL query (e.g., `SELECT ... WHERE order_id IN (...)`). It retrieves all related items in a single additional query and performs the relationship mapping in Python memory. This is necessary for multi-value relations (many-to-many or reverse foreign keys) because SQL-joining them would duplicate parent rows and inflate payload sizes.

---

## 3. Background Task Reliability (Section 2)

### What happens if a worker receives a SIGKILL mid-task?
By default, Celery acknowledges tasks immediately when they are retrieved from the queue (`acks_late = False`). If the worker receives a `SIGKILL` mid-task:
- The task is already removed from the broker.
- The task is lost forever and never completes.

### The Solution: Crash-Safety Configuration
We configure Celery with:
- **`acks_late = True`**: The task is only acknowledged (removed from the queue) *after* it completes successfully or raises a permanent error. If the worker crashes before sending the acknowledgment, Redis keeps the message.
- **`task_reject_on_worker_lost = True`**: If a worker subprocess is terminated (e.g. by `SIGKILL` or OOM killer), the Celery supervisor catches it, rejects the task, and tells Redis to requeue it for redelivery.

### Dead-Letter Queue (DLQ) Integration
If a task fails permanently or rate limit retries are exhausted, it will retry up to `max_retries=5` with exponential backoff.
Once exhausted, the `MaxRetriesExceededError` exception is caught, and the task metadata, payload, and error trace are saved to the `FailedJob` database model. This ensures that the message is never silently discarded and can be manually audited.

---

## 4. Written Answers (Section 4)

### Answer B: Pagination Strategies (Offset vs. Cursor)

#### Limit/Offset Pagination (`LimitOffsetPagination`)
- **How it works**: Uses SQL `LIMIT m OFFSET n`.
- **Database Impact**: To skip $n$ rows, the database must scan all $n$ rows from disk, sort them, and discard them. As the offset increases (e.g. page 10,000), performance degrades exponentially.
- **Mutation Instability**: If a new row is inserted or deleted while a user is scrolling, the entire dataset offsets. This causes users to see duplicate items or skip items entirely.

#### Cursor Pagination (`CursorPagination`)
- **How it works**: Uses a stable ordering key (like an indexed `created_at` or `id`) and filters based on the last seen value: `WHERE (created_at, id) > (last_created_at, last_id) LIMIT m`.
- **Database Impact**: The query scans only the next $m$ rows using the index. Performance remains constant ($O(\log N)$) regardless of dataset size.
- **Mutation Stability**: Safe against concurrent writes because it references a specific point in the index, ensuring no duplicates or skipped rows.
- **Limitation**: Users cannot jump to an arbitrary page (e.g., "Go to page 50") and must navigate sequentially.

---

### Answer C: File Upload Security (5 Vectors & Mitigations)

1. **Remote Code Execution (RCE) via Executable Uploads**
   - *Vector*: An attacker uploads a PHP, Python, or bash script and executes it via the webserver.
   - *Mitigation*: Restrict allowed extensions and perform MIME-type verification server-side using content sniffing. Set up the webserver to disable execution permissions in the uploads directory.

2. **Path Traversal via Filename Manipulation**
   - *Vector*: An attacker uploads a file named `../../etc/passwd` or `../../views/index.html` to overwrite system files.
   - *Mitigation*: Never trust `request.FILES['name']`. Always sanitize filenames using Django's `get_valid_filename()`, or generate a secure, random UUID-based name for storage.

3. **Storage inside the Webroot**
   - *Vector*: Files are stored in a public folder, allowing attackers to request uploaded files directly.
   - *Mitigation*: Store uploaded files outside of the application's root directory or on an isolated storage service (e.g., AWS S3, Cloudflare R2). Serve them via django views, signed temporary URLs, or configure the webserver to send files using `X-Sendfile`.

4. **Decompression Denial of Service (Zip Bombs)**
   - *Vector*: An attacker uploads a small 10KB zip file that decompresses into 100GB, exhausting disk space and memory (DoS).
   - *Mitigation*: Validate file sizes before decompression. Limit the maximum memory/disk size during extraction, and extract files sequentially while checking total size constraints.

5. **Malicious Image Payloads (Polyglot Files)**
   - *Vector*: An attacker embeds executable code (e.g. Javascript or PHP) inside the metadata headers of a valid GIF/JPEG file to exploit server vulnerabilities.
   - *Mitigation*: Pass the image through a processing library (such as Pillow) to decode and re-encode the file. Saving the image to a new file strips out any hidden metadata payloads.
