from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys

# Append local project folder reference paths to execute modules smoothly
sys.path.append("/home/bintang/job-application-pipeline")
from fetch_emails import fetch_and_store_emails

default_args = {
    "owner": "bintang",
    "depends_on_past": False,
    "start_date": datetime(2026, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    "automated_job_hunting_pipeline",
    default_args=default_args,
    description="Automated IMAP ingestion pipeline parsing job alerts smoothly into PostgreSQL local view schemas.",
    schedule_interval="0 8 * * *",  # Fires cleanly every single morning at 08:00 AM WIB
    catchup=False,
) as dag:

    ingest_emails_task = PythonOperator(
        task_id="harvest_raw_email_alerts",
        python_callable=fetch_and_store_emails,
    )

    ingest_emails_task
