import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from notifications.tasks import send_transactional_email

def main():
    print("🚀 Queuing 250 successful email jobs to trigger rate limiting (200/min limit)...")
    for i in range(250):
        send_transactional_email.delay({"id": i, "to": f"user{i}@example.com"})

    print("❌ Queuing 1 failing job to demonstrate exponential backoff retries...")
    send_transactional_email.delay({
        "id": 999, 
        "to": "fail@example.com", 
        "simulate_failure": True
    })

    print("✅ All jobs submitted to Redis!")

if __name__ == "__main__":
    main()
