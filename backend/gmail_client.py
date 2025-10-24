import os
import base64
import json
from typing import List, Optional, Dict, Any
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import logging
from dotenv import load_dotenv
from html import unescape
from html.parser import HTMLParser
import re

# Load environment variables at module level
load_dotenv()

logger = logging.getLogger(__name__)

# OAuth 2.0 scopes for Gmail API access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Client configuration
CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GMAIL_CLIENT_ID", ""),
        "client_secret": os.getenv("GMAIL_CLIENT_SECRET", ""),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost:8000/auth/callback"]
    }
}

class GmailClient:
    def __init__(self, credentials=None):
        """
        Initialize Gmail API client with optional credentials
        """
        self.credentials = credentials
        self.service = None
        if credentials:
            self._build_service()

    def _build_service(self):
        """
        Build the Gmail API service
        """
        try:
            self.service = build('gmail', 'v1', credentials=self.credentials)
        except Exception as e:
            logger.error(f"Error building Gmail service: {e}")
            raise

    def get_recent_messages(self, max_results: int = 16) -> List[Dict[str, Any]]:
        """
        Get recent messages from Gmail inbox
        """
        if not self.service:
            raise ValueError("Gmail service not initialized")

        try:
            # Query for messages from inbox
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            email_details = []

            for message in messages:
                msg_id = message['id']
                try:
                    msg = self.service.users().messages().get(
                        userId='me',
                        id=msg_id,
                        format='full'
                    ).execute()

                    # Get headers
                    headers = msg['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
                    from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
                    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')

                    # Get snippet for preview
                    snippet = msg.get('snippet', '')

                    email_details.append({
                        'id': msg_id,
                        'subject': subject,
                        'from': from_email,
                        'date': date,
                        'snippet': snippet
                    })
                except Exception as e:
                    logger.error(f"Error fetching message {msg_id}: {e}")
                    continue

            return email_details

        except Exception as e:
            logger.error(f"Error fetching recent messages: {e}")
            raise
            logger.error(f"Error building Gmail service: {str(e)}")
            raise

    def get_auth_url(self) -> str:
        """
        Generate the authorization URL for Gmail access
        """
        # Basic validation to avoid common errors
        if not CLIENT_CONFIG['web']['client_id'] or CLIENT_CONFIG['web']['client_id'] == "":
            raise ValueError("Missing client_id in configuration. Please check your .env file.")
            
        if not CLIENT_CONFIG['web']['client_secret'] or CLIENT_CONFIG['web']['client_secret'] == "":
            raise ValueError("Missing client_secret in configuration. Please check your .env file.")
        
        try:
            flow = Flow.from_client_config(
                CLIENT_CONFIG,
                scopes=SCOPES,
                redirect_uri=CLIENT_CONFIG['web']['redirect_uris'][0]
            )
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            return auth_url
        except Exception as e:
            logger.error(f"Error generating auth URL: {str(e)}")
            raise

    def get_credentials_from_code(self, code: str) -> Credentials:
        """
        Exchange authorization code for credentials
        """
        try:
            flow = Flow.from_client_config(
                CLIENT_CONFIG,
                scopes=SCOPES,
                redirect_uri=CLIENT_CONFIG['web']['redirect_uris'][0]
            )
            flow.fetch_token(code=code)
            self.credentials = flow.credentials
            self._build_service()
            return self.credentials
        except Exception as e:
            logger.error(f"Error getting credentials from code: {str(e)}")
            raise

    def set_credentials(self, credentials_json: str):
        """
        Set credentials from a JSON string
        """
        try:
            creds_data = json.loads(credentials_json)
            self.credentials = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes')
            )
            self._build_service()
        except Exception as e:
            logger.error(f"Error setting credentials: {str(e)}")
            raise

    def get_recent_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent emails from the user's inbox
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Set credentials first.")

        try:
            results = self.service.users().messages().list(
                userId='me',
                labelIds=['INBOX'],
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', 
                    id=message['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                # Extract headers
                headers = msg.get('payload', {}).get('headers', [])
                email_data = {
                    'id': msg['id'],
                    'snippet': msg.get('snippet', ''),
                    'from': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                    'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                    'date': next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
                }
                emails.append(email_data)
                
            return emails
            
        except Exception as e:
            logger.error(f"Error getting recent emails: {str(e)}")
            raise

    def get_email_content(self, message_id: str) -> Dict[str, Any]:
        """
        Get the full content of a specific email
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Set credentials first.")
            
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = message.get('payload', {}).get('headers', [])
            email_data = {
                'id': message['id'],
                'threadId': message.get('threadId', ''),
                'from': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                'to': next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown'),
                'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                'date': next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown'),
                'body': self._get_email_body(message)
            }
            
            return email_data
            
        except Exception as e:
            logger.error(f"Error getting email content: {str(e)}")
            raise
    def _get_email_body(self, message: Dict[str, Any]) -> str:
        """
        Extract the body from an email message. Prefer text/plain, fall back to
        text/html and convert HTML to cleaned plain text. This strips tags and
        removes common tracking pixels by ignoring <img> content.
        """
        body = ""
        
        if 'parts' in message.get('payload', {}):
            # Try to pick a text/plain part first
            for part in message['payload']['parts']:
                if part.get('mimeType') == 'text/plain':
                    body = self._decode_body(part.get('body', {}).get('data', ''))
                    break

            # If no text/plain part found, try to get HTML and convert to text
            if not body:
                for part in message['payload']['parts']:
                    if part.get('mimeType') == 'text/html':
                        html_content = self._decode_body(part.get('body', {}).get('data', ''))
                        body = self._html_to_text(html_content)
                        break
        else:
            # Handle single-part messages
            if message.get('payload', {}).get('body', {}).get('data'):
                # If this is HTML, convert to text; otherwise decode directly
                # We make a best-effort guess by checking for HTML tags
                raw = self._decode_body(message['payload']['body']['data'])
                if '<' in raw and '>' in raw:
                    body = self._html_to_text(raw)
                else:
                    body = raw
        
        return body
    
    def _decode_body(self, data: str) -> str:
        """
        Decode base64 email body
        """
        if not data:
            return ""
            
        try:
            return base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8')
        except Exception as e:
            logger.error(f"Error decoding email body: {str(e)}")
            return "Error decoding email content"

    def _html_to_text(self, html_content: str) -> str:
        """
        Convert HTML content to plain text. This is a small, dependency-free
        stripper: it removes tags, unescapes HTML entities and collapses
        whitespace. It intentionally ignores images and common tracking pixels.
        """
        if not html_content:
            return ""

        class _MLStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self._fed = []

            def handle_data(self, d):
                self._fed.append(d)

            def handle_entityref(self, name):
                self._fed.append(self.unescape(f'&{name};'))

            def get_data(self):
                return ''.join(self._fed)

        # Remove script/style tags content first
        cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html_content, flags=re.I | re.S)

        # Initialize stripper and feed cleaned HTML
        stripper = _MLStripper()
        try:
            stripper.feed(unescape(cleaned))
            text = stripper.get_data()
        except Exception:
            # Fallback: strip tags crudely
            text = re.sub('<[^<]+?>', ' ', cleaned)
            text = unescape(text)

        # Collapse whitespace and trim
        text = re.sub(r'\s+', ' ', text).strip()

        return text