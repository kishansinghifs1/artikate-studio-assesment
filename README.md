# Artikate Studio — Backend Assessment

This repository contains the backend assessment implementation for Artikate Studio. It covers Multi-Tenant isolation, N+1 Query profiling/optimization, a Rate-Limited Background Job Queue (Celery + Redis), and technical Q&A.

---

## Repository Structure

```
artikate-assessment/
├── README.md                  # Setup and execution instructions (this file)
├── DESIGN.md                  # System architecture design decisions
├── ANSWERS.md                 # Technical Q&A answers (Sections 1, 2, 3, 4)
├── requirements.txt           # Django, DRF, Celery, Redis, and Pytest dependencies
├── docker-compose.yml         # Spin up PostgreSQL and Redis
├── manage.py                  # Django operations script
├── pytest.ini                 # Pytest Django configuration
├── config/                    # Django project configuration
│   ├── settings.py
│   ├── celery.py
│   ├── urls.py
│   └── wsgi.py
├── orders/                    # Orders app (Tenant Isolation & N+1 profiling)
│   ├── models.py
│   ├── views.py
│   ├── managers.py            # TenantManager & bind_tenant helper
│   ├── middleware.py          # TenantMiddleware
│   ├── urls.py
│   ├── management/            # Seeding and query benchmarking tool
│   │   └── commands/
│   │       └── run_benchmark.py
│   └── tests/                 # Tenant isolation and view tests
├── notifications/             # Notifications app (Rate-limited Task queue)
│   ├── models.py              # FailedJob model (DLQ)
│   ├── tasks.py               # Rate-limited Celery task
│   ├── rate_limiter.py        # Python wrapper for Redis rate limiter
│   └── tests/                 # Rate limiter and Celery task tests
└── docs/
    └── silk_before_after.md   # Diagnostic performance output
```

---

## Setup & Quickstart

To run the project, make sure you have **Docker** and **Python 3.10+** installed. The setup takes less than 2 minutes.

### 1. Spin up Database & Broker (Docker)
Start the PostgreSQL and Redis containers in the background:
```bash
docker compose up -d
```

### 2. Set Up Virtual Environment & Dependencies
Create and activate a Python virtual environment, then install requirements:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Database Migrations
Run Django migrations to prepare the database schema:
```bash
python manage.py makemigrations orders
python manage.py makemigrations notifications
python manage.py migrate
```

### 4. Run the Performance Benchmark (Diagnostic Tool)
We built a custom command to seed 250 orders (each with 3 items) and run both unoptimized and optimized code paths. It outputs a clear timing and query count comparison:
```bash
python manage.py run_benchmark
```

### 5. Run the Test Suite
Verify that the complete implementation passes all 14 tests:
```bash
pytest
```

---

## Running the Servers

### Run Web Server
Start the Django development server:
```bash
python manage.py runserver
```
The Django app will run at `http://127.0.0.1:8000/`.
- Django-Silk profiler UI: `http://127.0.0.1:8000/silk/`
- Optimized API path: `/api/orders/optimized/` (requires basic auth & `X-Tenant` header)
- Unoptimized API path: `/api/orders/unoptimized/` (requires basic auth & `X-Tenant` header)

### Run Celery Worker
Start the Celery worker to consume rate-limited background tasks:
```bash
celery -A config worker -l info
```
The tasks will process rate-limited requests at 200 requests/minute, retry with exponential backoff on failure, and DLQ to `FailedJob` on exhaustion.
