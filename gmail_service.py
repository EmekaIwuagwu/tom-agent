import os
import time
import base64
import json
import logging
from email.message import EmailMessage
from typing import List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify'
]

def get_gmail_service():
    """Initializes and returns the Gmail API service."""
    token_path = os.getenv("GMAIL_TOKEN_PATH", "gmail_token.json")
    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "gmail_credentials.json")
    creds = None
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            if not os.path.exists(creds_path):
                logger.error(f"Error: {creds_path} not found. Cannot connect to Gmail API.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as error:
        logger.error(f"Failed to build Gmail service: {error}")
        return None

def send_email_api(to_email: str, subject: str, content: str, attachment_path: str = None) -> bool:
    """Send an email using the Gmail API."""
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
        logger.info(f"Email sent successfully. Message Id: {send_message['id']}")
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

def parse_parts(parts):
    """Recursively parses email parts to find the best text body."""
    body = ""
    for part in parts:
        mime_type = part.get('mimeType')
        data = part.get('body', {}).get('data')
        
        if mime_type == 'text/plain' and data:
            return base64.urlsafe_b64decode(data).decode()
        elif mime_type == 'text/html' and data:
            # Save HTML as fallback but keep looking for plain text
            body = base64.urlsafe_b64decode(data).decode()
        elif 'parts' in part:
            recursive_body = parse_parts(part['parts'])
            if recursive_body:
                return recursive_body
    return body

def get_full_email_body(message_id: str) -> str:
    """Fetches and decodes the full text body of an email, handling multi-part messages."""
    service = get_gmail_service()
    if not service:
        return "Gmail service unavailable."
    
    try:
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        payload = msg.get('payload', {})
        
        if 'parts' in payload:
            body = parse_parts(payload['parts'])
        else:
            data = payload.get('body', {}).get('data')
            if data:
                body = base64.urlsafe_b64decode(data).decode()
            else:
                body = ""
                
        if not body:
            return f"Snippet: {msg.get('snippet', 'No content found.')}"
            
        return body
    except Exception as e:
        logger.error(f"Error getting email body: {e}")
        return f"Failed to retrieve email content: {e}"

def check_emails_api(status: str = 'unread', max_results: int = 50, search_query: str = '') -> List[Dict]:
    """Scans the Gmail inbox for emails with metadata. Supports search constraints."""
    service = get_gmail_service()
    if not service:
        return []
        
    try:
        query_parts = []
        if status == 'unread':
            query_parts.append('is:unread')
        elif status == 'read':
            query_parts.append('is:read')
            
        if search_query:
            query_parts.append(search_query)
            
        final_query = " ".join(query_parts)
        
        results = service.users().messages().list(userId='me', q=final_query, maxResults=max_results).execute()
        messages = results.get('messages', [])
        
        unread_emails = []
        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
            
            headers = msg_data['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            unread_emails.append({
                "id": msg['id'],
                "sender_name": sender.split('<')[0].strip(),
                "sender_email": sender,
                "subject": subject,
                "preview": msg_data.get('snippet', ''),
                "date": date
            })
        return unread_emails
    except Exception as e:
        logger.error(f"Error checking emails via API: {e}")
        return []

def manual_login():
    """Simple login function that triggers the standard OAuth flow."""
    print("Opening your default web browser for Gmail login...")
    service = get_gmail_service()
    if service:
        print("Login successful! Tom now has access to your Gmail.")
    else:
        print("Login failed. See logs for details.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        manual_login()
