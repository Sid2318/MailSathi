# main.py
from fastapi import FastAPI, HTTPException, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import logging
import os
import json
from typing import Dict, Any, List, Optional
import sys

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables early
from dotenv import load_dotenv
load_dotenv(verbose=True)

# Log environment variable status (without exposing values)
logger.info(f"GMAIL_CLIENT_ID set: {'Yes' if os.getenv('GMAIL_CLIENT_ID') else 'No'}")
logger.info(f"GMAIL_CLIENT_SECRET set: {'Yes' if os.getenv('GMAIL_CLIENT_SECRET') else 'No'}")

from mcp_client import MCPClient

# Import GmailClient conditionally to avoid import error if packages are not installed
try:
    from gmail_client import GmailClient
    GMAIL_AVAILABLE = True
    logger.info("Gmail integration available")
except ImportError as e:
    GMAIL_AVAILABLE = False
    logger.warning(f"Gmail integration not available: {str(e)}")
    class DummyGmailClient:
        def __init__(self, *args, **kwargs):
            pass
    GmailClient = DummyGmailClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

try:
    mcp_client = MCPClient()
    logger.info("MCPClient initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize MCPClient: {str(e)}")
    raise

# Initialize Gmail client
gmail_client = GmailClient() if GMAIL_AVAILABLE else None

# Global variable to store user credentials
user_credentials = {}

class InputText(BaseModel):
    text: str

class EmailRequest(BaseModel):
    message_id: str

# Models for Gmail API
class AuthResponse(BaseModel):
    auth_url: str

class TokenData(BaseModel):
    code: str

class CredentialResponse(BaseModel):
    token: str
    success: bool

@app.post("/translate-to-marathi")
async def translate_to_marathi(req: InputText):
    if not req.text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    logger.info(f"Translating text: {req.text[:50]}...")
    translated_text = mcp_client.translate_to_marathi(req.text)
    logger.info("Translation completed")
    
    return {"marathi_translation": translated_text}

@app.get("/gmail/auth-url")
async def get_gmail_auth_url() -> AuthResponse:
    """
    Get the Gmail authorization URL
    """
    if not GMAIL_AVAILABLE:
        raise HTTPException(
            status_code=501, 
            detail="Gmail integration is not available. Please install required packages: 'pip install google-auth google-auth-oauthlib google-api-python-client'"
        )
    
    # Check environment variables
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    
    if not client_id:
        logger.error("GMAIL_CLIENT_ID not found in environment variables")
        raise HTTPException(
            status_code=500, 
            detail="Gmail client ID not configured. Please check your .env file."
        )
        
    if not client_secret:
        logger.error("GMAIL_CLIENT_SECRET not found in environment variables")
        raise HTTPException(
            status_code=500, 
            detail="Gmail client secret not configured. Please check your .env file."
        )
        
    try:
        auth_url = gmail_client.get_auth_url()
        logger.info("Auth URL generated successfully")
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Error getting auth URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting auth URL: {str(e)}")

@app.get("/auth/callback")
async def auth_callback(code: str, state: Optional[str] = None):
    """
    Handle the OAuth callback from Google
    """
    if not GMAIL_AVAILABLE:
        return RedirectResponse(url=f"http://localhost:5174?auth=error&message=Gmail integration not available")
        
    try:
        # Exchange code for credentials
        credentials = gmail_client.get_credentials_from_code(code)
        
        # Store credentials for this session
        # In a real app, you would store this in a database associated with a user
        user_id = "current_user"  # In a real app, get this from the session
        user_credentials[user_id] = {
            "token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes
        }
        
        # Redirect to frontend with success indicator
        return RedirectResponse(url=f"http://localhost:5174?auth=success")
    except Exception as e:
        logger.error(f"Error in auth callback: {str(e)}")
        return RedirectResponse(url=f"http://localhost:5174?auth=error&message={str(e)}")

@app.get("/gmail/check-auth")
async def check_auth() -> CredentialResponse:
    """
    Check if user is authenticated
    """
    if not GMAIL_AVAILABLE:
        return {"token": "", "success": False}
        
    user_id = "current_user"
    if user_id in user_credentials:
        return {"token": "valid", "success": True}
    else:
        return {"token": "", "success": False}

@app.get("/gmail/recent-emails")
async def get_recent_emails(max_results: int = 10):
    """
    Get recent emails from the user's Gmail inbox
    """
    if not GMAIL_AVAILABLE:
        raise HTTPException(
            status_code=501, 
            detail="Gmail integration is not available. Please install required packages: 'pip install google-auth google-auth-oauthlib google-api-python-client'"
        )
        
    user_id = "current_user"
    if user_id not in user_credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Set credentials from stored data
        client = GmailClient()
        client.set_credentials(json.dumps(user_credentials[user_id]))
        
        # Get recent emails
        emails = client.get_recent_emails(max_results=max_results)
        return {"emails": emails}
    except Exception as e:
        logger.error(f"Error getting recent emails: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting recent emails: {str(e)}")

@app.post("/gmail/email-content")
async def get_email_content(req: EmailRequest):
    """
    Get the content of a specific email
    """
    if not GMAIL_AVAILABLE:
        raise HTTPException(
            status_code=501, 
            detail="Gmail integration is not available. Please install required packages: 'pip install google-auth google-auth-oauthlib google-api-python-client'"
        )
        
    user_id = "current_user"
    if user_id not in user_credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Set credentials from stored data
        client = GmailClient()
        client.set_credentials(json.dumps(user_credentials[user_id]))
        
        # Get email content
        email = client.get_email_content(req.message_id)
        return {"email": email}
    except Exception as e:
        logger.error(f"Error getting email content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting email content: {str(e)}")

@app.post("/gmail/translate-email")
async def translate_email(req: EmailRequest):
    """
    Get and translate the content of a specific email
    """
    if not GMAIL_AVAILABLE:
        raise HTTPException(
            status_code=501, 
            detail="Gmail integration is not available. Please install required packages: 'pip install google-auth google-auth-oauthlib google-api-python-client'"
        )
        
    user_id = "current_user"
    if user_id not in user_credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Set credentials from stored data
        client = GmailClient()
        client.set_credentials(json.dumps(user_credentials[user_id]))
        
        # Get email content
        email = client.get_email_content(req.message_id)
        
        # Translate the email body
        translated_body = mcp_client.translate_to_marathi(email["body"])
        
        # Return both original and translated content
        return {
            "original_email": email,
            "translated_body": translated_body
        }
    except Exception as e:
        logger.error(f"Error translating email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error translating email: {str(e)}")
