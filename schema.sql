-- 1. Base Raw Table Architectures
CREATE TABLE IF NOT EXISTS raw_email_alerts (
    email_id TEXT PRIMARY KEY,
    sender_address TEXT NOT NULL,
    email_subject TEXT NOT NULL,
    received_timestamp TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_sheets_applications (
    application_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    applied_date DATE NOT NULL,
    platform_source TEXT NOT NULL
);

-- 2. Comprehensive 20-Condition Transformation View Configuration
CREATE OR REPLACE VIEW analytical_job_funnel AS
SELECT 
    raw_sheets_applications.application_id::text AS application_id,
    raw_sheets_applications.company_name::text AS company_name,
    raw_sheets_applications.job_title::text AS job_title,
    raw_sheets_applications.applied_date,
    raw_sheets_applications.platform_source::text AS platform_source,
    'Application sent'::text AS current_status,
    raw_sheets_applications.applied_date AS latest_activity_date
FROM raw_sheets_applications
UNION ALL
SELECT 
    split_part(raw_email_alerts.email_id::text, '@'::text, 1) AS application_id,
    TRIM(BOTH FROM CASE
        WHEN raw_email_alerts.sender_address::text ~~* '%jobstreet%'::text OR raw_email_alerts.sender_address::text ~~* '%seek%'::text THEN
        CASE
            WHEN raw_email_alerts.email_subject ~~ '%|%'::text THEN split_part(raw_email_alerts.email_subject, '|'::text, 2)
            WHEN raw_email_alerts.email_subject ~* 'telah melihat'::text THEN split_part(raw_email_alerts.email_subject, ' telah'::text, 1)
            WHEN raw_email_alerts.email_subject ~~ '%–%'::text THEN split_part(raw_email_alerts.email_subject, '–'::text, 2)
            WHEN raw_email_alerts.email_subject ~~ '%-%'::text THEN split_part(raw_email_alerts.email_subject, '-'::text, 2)
            ELSE 'Company via Jobstreet'::text
        END
        WHEN raw_email_alerts.sender_address::text ~~* '%linkedin%'::text THEN
        CASE
            WHEN raw_email_alerts.email_subject ~* 'was viewed by'::text THEN split_part(raw_email_alerts.email_subject, 'was viewed by'::text, 2)
            WHEN raw_email_alerts.email_subject ~* 'application to'::text AND raw_email_alerts.email_subject ~* ' at '::text THEN split_part(raw_email_alerts.email_subject, ' at '::text, 2)
            ELSE 'Company via LinkedIn'::text
        END
        ELSE
        CASE
            WHEN raw_email_alerts.email_subject ~~ '%|%'::text THEN split_part(raw_email_alerts.email_subject, '|'::text, 2)
            WHEN raw_email_alerts.email_subject ~~ '%–%'::text THEN split_part(raw_email_alerts.email_subject, '–'::text, 2)
            WHEN raw_email_alerts.email_subject ~~ '%-%'::text THEN split_part(raw_email_alerts.email_subject, '-'::text, 2)
            ELSE initcap(split_part(split_part(raw_email_alerts.sender_address::text, '@'::text, 2), '.'::text, 1))
        END
    END) AS company_name,
    CASE
        WHEN raw_email_alerts.email_subject ~* 'DevOps'::text THEN 'DevOps Engineer'::text
        WHEN raw_email_alerts.email_subject ~* 'Data Engineer'::text THEN 'Data Engineer'::text
        WHEN raw_email_alerts.email_subject ~* 'Data Scientist'::text THEN 'Data Scientist'::text
        WHEN raw_email_alerts.email_subject ~* 'AI Engineer|AI ENGINEER'::text THEN 'AI Engineer'::text
        WHEN raw_email_alerts.email_subject ~* 'Back End|Backend|Software'::text THEN 'Backend Developer'::text
        ELSE 'Technical Role'::text
    END AS job_title,
    raw_email_alerts.received_timestamp::date AS applied_date,
    CASE
        WHEN raw_email_alerts.sender_address::text ~~* '%linkedin%'::text THEN 'LinkedIn'::text
        WHEN raw_email_alerts.sender_address::text ~~* '%jobstreet%'::text THEN 'Jobstreet'::text
        ELSE 'Direct Email'::text
    END AS platform_source,
    CASE
        WHEN raw_email_alerts.sender_address::text ~~* '%jobstreet%'::text THEN
        CASE
            WHEN raw_email_alerts.email_subject ~* 'Next Step'::text THEN 'Next Step'
            WHEN raw_email_alerts.email_subject ~* 'telah melihat'::text THEN 'Viewed'
            ELSE 'Application sent'
        END
        WHEN raw_email_alerts.sender_address::text ~~* '%linkedin%'::text THEN
        CASE
            WHEN raw_email_alerts.email_subject ~* 'Your application was viewed by'::text THEN 'Viewed'
            WHEN raw_email_alerts.email_subject ~* 'Your application to'::text THEN 'Rejected'
            ELSE 'Application sent'
        END
        ELSE 'Application sent'
    END AS current_status,
    raw_email_alerts.received_timestamp::date AS latest_activity_date
FROM raw_email_alerts
WHERE raw_email_alerts.sender_address::text !~~* '%glints%'::text 
  AND raw_email_alerts.sender_address::text !~~* '%quora%'::text 
  AND raw_email_alerts.email_subject !~~* '%glints%'::text 
  AND raw_email_alerts.email_subject !~~* '%quora%'::text;
