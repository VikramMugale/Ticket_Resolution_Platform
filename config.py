"""
Configuration settings for the ticket management system
"""
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI/CrewAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

# Email Configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "")

# Database Configuration - PostgreSQL (Neon)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_gDh86RpYwObM@ep-empty-queen-ahxgu44w-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

# Organization Context for EuronSupport
ORG_CONTEXT = {
    "product": "EuronSupport - AI-Powered Ticket Resolution System",
    "stack": {
        "backend": "FastAPI + PostgreSQL + Redis",
        "streaming": "HLS via CDN + DRM",
        "auth": "OTP provider + fallback provider",
        "payments": "Payment gateway + webhook processor",
        "observability": "Sentry + Datadog + CloudWatch",
    },
    "recent_changes": [
        {
            "date": "2026-01-15",
            "release": "v2.7.0",
            "notes": [
                "New dashboard query optimization attempt",
                "Payment unlock logic refactor to async worker",
                "Live test engine updated for new question formats",
                "OTP provider primary route updated for cost savings",
            ],
        }
    ],
    "known_incidents": [
        {
            "date": "2025-12-28",
            "summary": "OTP delays during 7–10pm IST due to provider throttling",
            "mitigation": "Added fallback provider but not fully rolled out to all regions",
        },
        {
            "date": "2026-01-10",
            "summary": "Payment deducted but unlock delay due to webhook retries backlog",
            "mitigation": "Scaled worker, but queue alerts were not tuned",
        }
    ],
    "sla_targets": {
        "dashboard_p95_ms": 1200,
        "video_rebuffer_rate": "<1%",
        "otp_delivery_s": "<15s",
        "payment_unlock_s": "<30s",
        "crash_free_sessions": ">=99.5%",
    }
}

# Streamlit Configuration
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")  # Change in production!
