import os
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import date
import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Multi-Source Job Search Pipeline Ingestion Engine")

# Reliable Database Connection
def get_warehouse_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

# --- DATA QUALITY & INTEGRITY LAYER ---
class GoogleSheetsApplicationSchema(BaseModel):
    application_id: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    job_title: str = Field(..., min_length=1)
    applied_date: date  # Enforces YYYY-MM-DD compliance
    platform_source: str
    salary_estimate: str = "Not Specified"

# --- WEBHOOK ENDPOINT FOR SOURCE A (MANUAL INPUTS) ---
@app.post("/webhook/sheets-app", status_code=status.HTTP_201_CREATED)
async def ingest_sheets_application(payload: GoogleSheetsApplicationSchema):
    try:
        conn = get_warehouse_connection()
        cursor = conn.cursor()
        
        # Inserts straight into the real, physical table
        insert_query = """
            INSERT INTO raw_sheets_applications (
                application_id, company_name, job_title, applied_date, platform_source, salary_estimate
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (application_id) DO UPDATE SET
                company_name = EXCLUDED.company_name,
                job_title = EXCLUDED.job_title,
                platform_source = EXCLUDED.platform_source,
                salary_estimate = EXCLUDED.salary_estimate;
        """
        
        cursor.execute(insert_query, (
            payload.application_id.strip(),
            payload.company_name.strip(),
            payload.job_title.strip(),
            payload.applied_date,
            payload.platform_source.strip(),
            payload.salary_estimate.strip()
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success", "message": f"Application for {payload.company_name} successfully stored."}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline ingestion failure: {str(e)}"
        )

# --- API EXPORT ENDPOINT FOR GOOGLE SHEETS ---
@app.get("/api/export-dashboard")
async def export_automated_dashboard():
    try:
        conn = get_warehouse_connection()
        cursor = conn.cursor()
        
        # Explicitly fetch the exact 6 columns your Google Apps Script relies on
        query = """
            SELECT 
                application_id, 
                company_name, 
                job_title, 
                applied_date, 
                platform_source, 
                current_status
            FROM analytical_job_funnel;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        sheet_data = []
        for r in rows:
            # Clean trailing newline spaces dynamically before array packaging
            clean_company = str(r[1]).replace("\n", " ").replace("\r", " ").strip()
            clean_title = str(r[2]).replace("\n", " ").replace("\r", " ").strip()
            clean_status = str(r[5]).replace("\n", " ").replace("\r", " ").strip()
            
            sheet_data.append([
                str(r[0]).strip(),   # application_id (Index 0)
                clean_company,       # company_name   (Index 1)
                clean_title,         # job_title      (Index 2)
                str(r[3]),           # applied_date   (Index 3)
                str(r[4]),           # platform_source(Index 4)
                clean_status         # current_status (Index 5)
            ])
            
        cursor.close()
        conn.close()
        
        return JSONResponse(content=sheet_data)
        
    except Exception as e:
        return JSONResponse(
            status_code=500, 
            content={"status": "error", "detail": str(e)}
        )

from pydantic import BaseModel
from typing import List

# Clear structure schema for data arrays
class AirflowSyncPayload(BaseModel):
    data: List[list]

# --- PUSH ENGINE: AIRFLOW AUTOMATION INGESTION ---
@app.post("/webhook/airflow-sync", status_code=status.HTTP_200_OK)
async def receive_automated_airflow_sync(payload: AirflowSyncPayload):
    try:
        conn = get_warehouse_connection()
        cursor = conn.cursor()
        
        cursor.execute("TRUNCATE TABLE raw_sheets_applications CASCADE;")
        
        insert_query = """
            INSERT INTO raw_sheets_applications (
                application_id, company_name, job_title, applied_date, platform_source, salary_estimate
            ) VALUES (%s, %s, %s, %s, %s, %s);
        """
        
        # Access the wrapper list array cleanly
        for row in payload.data:
            cursor.execute(insert_query, (
                row[0], row[1], row[2], row[3], row[4], row[5] if len(row) > 5 else "Not Specified"
            ))
            
        conn.commit()
        cursor.close()
        conn.close()
        return {"status": "success", "message": f"Successfully cached {len(payload.data)} rows from Airflow engine."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Push synchronization drop: {str(e)}")