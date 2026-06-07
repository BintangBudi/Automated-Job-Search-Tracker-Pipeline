import os
import imaplib
import email
from email.header import decode_header
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_warehouse_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT")
    )

def extract_and_load_emails():
    print("⏳ Connecting to live inbox via IMAP...")
    
    try:
        mail = imaplib.IMAP4_SSL(os.getenv("EMAIL_HOST"))
        mail.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_APP_PASSWORD"))
    except Exception as e:
        print(f"❌ Mail Authentication Failed: {str(e)}")
        return

    # Escaped internal quotes prevent IMAP "Could not parse command" syntax drops
    mail.select('"[Gmail]/All Mail"')
    
    # --- PRODUCTION SEARCH CRITERIA ---
    search_keywords = [
        'SUBJECT "application"', 
        'SUBJECT "lamaranmu"', 
        'SUBJECT "melihat"', 
        'SUBJECT "ditutup"', 
        'SUBJECT "interview"', 
        'SUBJECT "wawancara"', 
        'SUBJECT "test"', 
        'SUBJECT "assessment"', 
        'SUBJECT "challenge"'
    ]
    
    # Build the IMAP standard nested OR format: (OR term1 (OR term2 term3))
    query = search_keywords[0]
    for keyword in search_keywords[1:]:
        query = f"OR {keyword} ({query})"
    search_criterion = f"({query})"
    
    status, messages = mail.search(None, search_criterion)
    
    if status != "OK":
        print("❌ Error searching mail server with advanced criteria.")
        return
        
    email_ids = messages[0].split()
    print(f"📥 Found {len(email_ids)} targeted application milestone emails in your inbox.")
    
    if not email_ids:
        print("💡 No matching emails found. Waiting for new updates.")
        return

    conn = get_warehouse_connection()
    cursor = conn.cursor()
    
    insert_query = """
        INSERT INTO raw_email_alerts (
            email_id, sender_address, email_subject, received_timestamp, email_snippet
        ) VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (email_id) DO UPDATE SET
            email_subject = EXCLUDED.email_subject,
            email_snippet = EXCLUDED.email_snippet;
    """
    
    loaded_count = 0
    
    # Sliced to [-200:] to retrieve and scan the 200 newest matched entries
    newest_emails = email_ids[-200:]
    print(f"🔄 Processing the {len(newest_emails)} newest records...")
    
    for e_id in newest_emails:
        res, msg_data = mail.fetch(e_id, "(RFC822)")
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Decode Subject cleanly
                subject_header = msg.get("Subject", "")
                subject, encoding = decode_header(subject_header)[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="ignore")
                    
                sender = msg.get("From")
                if not sender:
                    sender = "Unknown Sender"
                
                # Parse Timestamp
                date_str = msg.get("Date")
                try:
                    parsed_date = email.utils.parsedate_to_datetime(date_str)
                except Exception:
                    parsed_date = datetime.now()
                
                unique_email_id = msg.get("Message-ID", str(e_id)).strip("<>")
                
                # Parse Body Snippet
                snippet = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                snippet = payload.decode(errors="ignore")[:500]
                            break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        snippet = payload.decode(errors="ignore")[:500]

                # --- ✅ FIX: SYSTEM-WIDE DEFENSIVE SAFETY GUARD ---
                # Strip domain hostnames to get a short, robust alphanumeric unique key
                clean_id_prefix = unique_email_id.split("@")[0].strip()
                safe_email_id = clean_id_prefix[:95]
                
                # Broaden constraints to allow long sender display headers to pass cleanly
                safe_sender = sender[:140]
                safe_subject = subject

                cursor.execute(insert_query, (
                    safe_email_id,
                    safe_sender,
                    safe_subject,
                    parsed_date,
                    snippet.strip()
                ))
                loaded_count += 1

    conn.commit()
    cursor.close()
    conn.close()
    mail.logout()
    
    print(f"✅ Enhanced email pipeline sync complete. Processed {loaded_count} milestone entries.")

if __name__ == "__main__":
    extract_and_load_emails()