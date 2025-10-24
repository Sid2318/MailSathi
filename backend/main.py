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
from tts_service import tts_service

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables early
from dotenv import load_dotenv
load_dotenv(verbose=True)

# Create audio output directory if it doesn't exist
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio_cache")
os.makedirs(AUDIO_DIR, exist_ok=True)
os.chdir(os.path.dirname(__file__))  # Change to backend directory for relative paths

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

class AudioCleanupRequest(BaseModel):
    message_id: str
    language: str

@app.post("/tts/cleanup")
async def cleanup_audio(req: AudioCleanupRequest):
    """
    Cleanup audio file after playback is complete
    """
    try:
        success = tts_service.cleanup_audio_file(req.message_id, req.language)
        return {"success": success}
    except Exception as e:
        logger.error(f"Error cleaning up audio: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup audio file")

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


def _require_auth_or_return_auth_url():
    """
    Helper to check for stored credentials and, if missing, return an
    HTTP 401 with an optional Gmail auth URL so the frontend can redirect
    the user to authenticate.
    """
    user_id = "current_user"
    if user_id in user_credentials:
        return user_credentials[user_id]

    # If Gmail integration is available, try to provide an auth URL
    auth_url = None
    if GMAIL_AVAILABLE:
        try:
            auth_url = gmail_client.get_auth_url()
        except Exception:
            auth_url = None

    raise HTTPException(status_code=401, detail={
        "message": "Not authenticated",
        "auth_url": auth_url
    })

class InputText(BaseModel):
    text: str
    language: Optional[str] = "Marathi"

class EmailRequest(BaseModel):
    message_id: str
    language: Optional[str] = "Marathi"

# Models for Gmail API
class AuthResponse(BaseModel):
    auth_url: str

class TokenData(BaseModel):
    code: str

class TTSRequest(BaseModel):
    email: Dict[str, Any]
    translated_body: str
    language: str
    message_id: str

class TTSResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class CredentialResponse(BaseModel):
    token: str
    success: bool

@app.post("/translate-to-marathi")
async def translate_to_marathi(req: InputText):
    if not req.text:
        raise HTTPException(status_code=400, detail="No text provided")
    
    logger.info(f"Translating text: {req.text[:50]}...")
    # Use requested language if provided
    lang = req.language or "Marathi"
    translated_text = mcp_client.translate(req.text, target_language=lang)
    logger.info("Translation completed")
    
    # Return both legacy key and a generic key
    return {"marathi_translation": translated_text, "translation": translated_text, "language": lang}

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
async def get_recent_emails(max_results: int = 16):
    """
    Get recent emails from the user's Gmail inbox
    """
    if not GMAIL_AVAILABLE:
        raise HTTPException(
            status_code=501, 
            detail="Gmail integration is not available. Please install required packages: 'pip install google-auth google-auth-oauthlib google-api-python-client'"
        )
        
    # try:
        # Ensure user is authenticated or provide auth URL in the 401 detail
    creds = _require_auth_or_return_auth_url()
        
    #     # Update client credentials and fetch messages
    #     gmail_client.credentials = creds
    #     messages = gmail_client.get_recent_messages(max_results=max_results)
    #     return {"messages": messages}
    # except Exception as e:
    #     logger.error(f"Error fetching recent emails: {e}")
    #     raise HTTPException(status_code=500, detail=str(e))

    try:
        # Set credentials from stored data
        client = GmailClient()
        client.set_credentials(json.dumps(creds))

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
        
    # Ensure user is authenticated or provide auth URL in the 401 detail
    creds = _require_auth_or_return_auth_url()

    try:
        # Set credentials from stored data
        client = GmailClient()
        client.set_credentials(json.dumps(creds))

        # Get email content
        email = client.get_email_content(req.message_id)
        return {"email": email}
    except Exception as e:
        logger.error(f"Error getting email content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting email content: {str(e)}")

@app.post("/gmail/translate-email")
async def translate_email(req: EmailRequest):
    """
    Get and translate the content of a specific email, generating audio in parallel
    """
    if not GMAIL_AVAILABLE:
        raise HTTPException(
            status_code=501, 
            detail="Gmail integration is not available. Please install required packages: 'pip install google-auth google-auth-oauthlib google-api-python-client'"
        )
        
    # Ensure user is authenticated or provide auth URL in the 401 detail
    creds = _require_auth_or_return_auth_url()

    try:
        # Set credentials from stored data
        client = GmailClient()
        client.set_credentials(json.dumps(creds))
        # Get email content
        email = client.get_email_content(req.message_id)

        # Translate the email body using requested language
        lang = req.language or "Marathi"
        translated_body = mcp_client.translate(email["body"], target_language=lang)

        # Generate audio file in parallel with response
        speech_text = tts_service.format_email_for_speech(email, translated_body, lang)
        
        # Generate the audio file (will be cached) - don't play it yet
        audio_generated = tts_service.generate_audio(
            email_data=email,
            translated_body=translated_body,
            lang=lang,
            email_id=req.message_id
        )

        try:
            # Generate audio file in background
            speech_text = tts_service.format_email_for_speech(email, translated_body, lang)
            audio_generated = tts_service.generate_audio(
                email_data=email,
                translated_body=translated_body,
                lang=lang,
                email_id=req.message_id
            )
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            audio_generated = False

        # Return both original and translated content
        return {
            "original_email": email,
            "translated_body": translated_body,
            "audio_ready": audio_generated
        }
    except Exception as e:
        logger.error(f"Error translating email: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error translating email: {str(e)}")

@app.post("/tts/speak-email")
async def speak_email(req: TTSRequest) -> TTSResponse:
    """
    Convert email content to speech in the target language
    """
    try:
        # Format the email content for speech
        speech_text = tts_service.format_email_for_speech(
            req.email,
            req.translated_body,
            req.language
        )
        
        # Generate and play the audio
        success = tts_service.speak_text(
            text=speech_text,
            lang=req.language,
            email_id=req.message_id
        )
        
        if success:
            return {"success": True, "message": "Audio playback started"}
        else:
            return {"success": False, "message": "Failed to generate audio"}
            
    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}")
        return {"success": False, "message": str(e)}


