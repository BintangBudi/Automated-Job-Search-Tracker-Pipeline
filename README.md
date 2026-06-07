# 📊 Automated Job Search Tracker Pipeline

An automated, data-driven pipeline that systematically monitors your job hunt. The system automatically harvests messy job email alerts (LinkedIn, Jobstreet, Direct Senders) directly from your inbox via IMAP, structures the data through a 20-condition PostgreSQL parsing matrix, and bridges it to an interactive Google Sheets analytics dashboard.

---

## 📌 Features & Core Flow

1. **Daily Email Ingestion:** Apache Airflow 3.0 orchestrates a specialized Python script (`fetch_emails.py`) every morning at 08:00 AM WIB to extract incoming applications, interviews, and status alerts.
2. **On-the-Fly Data Refining:** Raw text streams are instantly parsed using a highly optimized, case-insensitive regular expression PostgreSQL View (`analytical_job_funnel`) to automatically track your funnel status, company names, and technical roles.
3. **Secure API Sync Gate:** A lightweight FastAPI server exposes local sync endpoints that query your database warehouse views.
4. **Cloud-to-Local Bridge:** An Ngrok tunnel safely bypasses local firewalls, allowing cloud-hosted Google Apps Script webhooks to fetch local analytics metrics directly.
5. **Real-Time Visualizations:** Google Sheets renders live KPI scorecards, application velocity trends, and a visual horizontal pipeline funnel chart.

---

## 🏗️ System Architecture

```mermaid
graph TD
    Gmail["📧 Gmail (Raw Inbox)"]
    GSheets["📊 Google Sheets Dashboard"]

    subgraph Laptop ["💻 Local Laptop (Airflow & Database)"]
        Airflow["⚙️ Airflow Scheduler"]
        Scraper["🐍 fetch_emails.py"]
        Postgres["🗄️ PostgreSQL DB"]
        SQLView["🎛️ SQL view: analytical_job_funnel"]
        FastAPI["⚡ FastAPI (Backend App)"]
    end

    Ngrok["🔒 Ngrok Tunnel"]

    Airflow -->|1. Triggers Daily| Scraper
    Gmail ==>|2. Extracts Emails| Scraper
    Scraper ==>|3. Saves Rows| Postgres
    Postgres -->|4. Cleans Text Via| SQLView

    GSheets ==>|5. Sync Button / Trigger| Ngrok
    Ngrok ==>|6. Tunnels Inbound| FastAPI
    FastAPI ==>|7. Queries| SQLView
    SQLView ==>|8. Returns JSON| FastAPI
    FastAPI ==>|9. Updates Charts| GSheets
