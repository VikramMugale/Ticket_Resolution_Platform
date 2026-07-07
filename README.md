# EuronSupport - AI-Powered Ticket Resolution System

**EuronSupport** is an industry-grade, AI-powered customer support and ticket resolution system that automatically processes tickets, assigns them to the right managers, and provides comprehensive analytics.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL database (Neon or any PostgreSQL instance)
- OpenAI API key

### Installation

1. **Install Dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure Environment**
```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env with your values:
# - OPENAI_API_KEY=your_key_here
# - DATABASE_URL=your_postgresql_connection_string
```

3. **Start Applications**
```bash
# Option 1: Use launcher (recommended)
python launcher.py

# Option 2: Start manually
streamlit run user_app.py --server.port 8501
streamlit run admin_app.py --server.port 8502
```

4. **Access Applications**
- **User Interface**: http://localhost:8501
- **Admin Dashboard**: http://localhost:8502 (Password: `admin123`)

## 📋 Features

- ✅ AI-Powered Ticket Processing (5 CrewAI agents)
- ✅ Automatic Manager Assignment
- ✅ PostgreSQL Database (Production-ready)
- ✅ Real-time Analytics & Charts
- ✅ Past Incidents Learning
- ✅ Email Notifications
- ✅ User Ticket Tracking
- ✅ Comprehensive Admin Dashboard

## 📁 Project Structure

```
euronsupport/
├── Core Application
│   ├── database.py          # PostgreSQL operations
│   ├── config.py            # Configuration
│   ├── agents.py            # CrewAI agents
│   ├── ticket_processor.py  # Processing logic
│   └── email_service.py     # Email notifications
│
├── User Interface
│   └── user_app.py          # Streamlit user app
│
├── Admin Interface
│   └── admin_app.py        # Streamlit admin dashboard
│
├── Utilities
│   ├── launcher.py         # App launcher
│   └── test_euronsupport.py # System tests
│
└── Documentation
    ├── README.md           # This file
    





For issues or questions, refer to ARCHITECTURE.md or contact support@euronsupport.com

---

**Built with CrewAI, Streamlit, and PostgreSQL**
