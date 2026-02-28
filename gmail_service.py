import os
import time
import base64
from email.message import EmailMessage
from typing import List, Dict
from playwright.sync_api import sync_playwright
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

AUTH_JSON = "gmail_auth.json"

def get_gmail_service():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    token_path = os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")
    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "gmail_credentials.json")
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                logger.warning(f"Warning: {creds_path} not found. Cannot send emails via API.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as error:
        logger.error(f"An error occurred: {error}")
        return None

def send_email_api(to_email: str, subject: str, content: str, attachment_path: str = None) -> bool:
    """Send an email using Gmail API"""
    service = get_gmail_service()
    if not service:
        return False
        
    try:
        message = EmailMessage()
        message.set_content(content)
        message['To'] = to_email
        message['Subject'] = subject

        if attachment_path and os.path.exists(attachment_path):
            import magic
            mime_type = magic.from_file(attachment_path, mime=True)
            main_type, sub_type = mime_type.split('/', 1)
            with open(attachment_path, 'rb') as f:
                message.add_attachment(f.read(), maintype=main_type, subtype=sub_type, filename=os.path.basename(attachment_path))

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        logger.info(f"Message Id: {send_message['id']}")
        return True
    except Exception as e:
        logger.error(f"An error occurred sending email: {e}")
        return False

def check_unread_emails_playwright() -> List[Dict]:
    """
    Uses Playwright to scan Gmail inbox for unread emails and extract their details.
    Assumes session state is stored in AUTH_JSON.
    """
    unread_emails = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Check if auth state exists
        if os.path.exists(AUTH_JSON):
            context = browser.new_context(storage_state=AUTH_JSON)
        else:
            logger.warning("No auth state found for Playwright. Please login manually first by running script in headful mode.")
            # For automation, if it's the first time, it might need to be run in headful mode
            context = browser.new_context()
            
        page = context.new_page()
        try:
            page.goto("https://mail.google.com/mail/u/0/#inbox")
            
            # Simple check if login is required
            if "ServiceLogin" in page.url or "AccountChooser" in page.url:
                logger.error("Gmail requires login. Run playwright in headful mode to authenticate and save state.")
                browser.close()
                return unread_emails

            # Wait for inbox to load
            page.wait_for_selector('tr.zA', timeout=15000)
            
            # Find all unread rows 
            unread_rows = page.locator('tr.zA.zE').all()
            
            for row in unread_rows:
                try:
                    # Sender
                    sender_el = row.locator('.yX.xY .yW span').first
                    sender_name = sender_el.inner_text() if sender_el.count() > 0 else "Unknown"
                    sender_email = sender_el.get_attribute('email') if sender_el.count() > 0 else "Unknown"
                    
                    # Subject & Preview
                    subject_el = row.locator('.xY.a4W .xS .bog span').first
                    subject = subject_el.inner_text() if subject_el.count() > 0 else "No Subject"
                    
                    preview_el = row.locator('.xY.a4W .xS .y2').first
                    preview = preview_el.inner_text().replace('\u2014', '').strip() if preview_el.count() > 0 else ""
                    
                    email_id = row.get_attribute('id')
                    
                    unread_emails.append({
                        "id": email_id,
                        "sender_name": sender_name,
                        "sender_email": sender_email,
                        "subject": subject,
                        "preview": preview
                    })
                except Exception as row_error:
                    logger.warning(f"Error parsing row: {row_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error checking Gmail via Playwright: {e}")
            
        browser.close()
        
    return unread_emails

def manual_login():
    """Utility function to login manually and save auth state for Playwright"""
    print("Opening browser for manual login. Please sign into Gmail.")
    print("Once logged in and inbox is visible, close the browser.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto("https://mail.google.com")
        page.wait_for_url("https://mail.google.com/mail/u/0/#inbox", timeout=300000) # 5 min to login
        context.storage_state(path=AUTH_JSON)
        browser.close()
    print("Auth state saved successfully.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        manual_login()
