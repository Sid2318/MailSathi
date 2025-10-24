import os
import time
from gtts import gTTS
import pygame
from typing import Optional
import logging
import threading

logger = logging.getLogger(__name__)

# Map language names to gTTS codes
LANG_MAP = {
    "Marathi": "mr",
    "Hindi": "hi",
    "Tamil": "ta",
    "English": "en",
    "Kannada": "kn",
    "Telugu": "te",
    "Bengali": "bn"
}

class TTSService:
    def __init__(self):
        self._cached_files = {}  # Store files by email_id + lang
        pygame.mixer.init(frequency=44100)

    def get_cache_key(self, email_id: str, lang: str) -> str:
        """Generate a unique key for caching audio files"""
        return f"{email_id}_{lang}"

    def speak_text(self, text: str, lang: str, email_id: str) -> bool:
        """
        Convert text to speech and play it. Deletes the audio file after playback.
        Returns True if successful.
        """
        if not text.strip():
            logger.warning("No text to speak")
            return False

        filename = None
        try:
            # Get language code, fallback to English
            lang_code = LANG_MAP.get(lang, "en")
            
            # Generate new file
            filename = f"speech_{email_id}_{lang}_{int(time.time())}.mp3"
            tts = gTTS(text=text, lang=lang_code)
            tts.save(filename)

            # Clean up old files
            for old_file in self._cached_files.values():
                try:
                    if os.path.exists(old_file):
                        os.remove(old_file)
                except Exception:
                    pass
            self._cached_files = {}

            # Play the audio
            try:
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                # Cleanup after playback
                pygame.mixer.music.unload()
                if os.path.exists(filename):
                    os.remove(filename)
                    logger.info(f"Deleted audio file: {filename}")
                return True
                
            except Exception as e:
                logger.error(f"Error playing audio: {e}")
                return False

        except Exception as e:
            logger.error(f"Error in text-to-speech: {e}")
            return False
        
        finally:
            # Ensure file is deleted even if an error occurs
            if filename and os.path.exists(filename):
                try:
                    os.remove(filename)
                    logger.info(f"Cleaned up audio file: {filename}")
                except Exception as e:
                    logger.error(f"Error cleaning up audio file: {e}")

    def format_email_for_speech(self, email_data: dict, translated_body: str, lang: str) -> str:
        """
        Format email data into a speech-friendly format in the target language.
        Includes email summary and replaces URLs with the word 'link'.
        """
        from mcp_client import MCPClient
        mcp = MCPClient()
        
        # First translate the metadata prompts
        prompts = {
            "from": "This email is from",
            "subject": "The subject is",
            "date": "Sent on",
            "summary_intro": "Let me summarize this email for you.",
            "key_points": "The main points are:",
            "full_content": "Here is the complete message:",
            "link": "link"
        }
        
        translated_prompts = {
            key: mcp.translate(text, target_language=lang).strip()
            for key, text in prompts.items()
        }

        # Clean up the body text first
        import re

        # Patterns to remove
        web_version_patterns = [
            # Match "View web version:" and the following URL line and any surrounding whitespace
            r"(?i)View\s+web\s+version:[\s\n]*http[s]?://[^\n]*\n?",
            # Match the entire HTML display message block
            r"Unfortunately,[^*]*?display HTML[^*]*?browser\.[^*]*\*+",
            # Match lines with just asterisks (any length)
            r"^\s*\*+\s*$\n?",
            # Match any standalone URL lines
            r"^\s*http[s]?://\S+\s*$\n?",
            # Match email client capability messages
            r"(?i)If you(?: are unable to|cannot| can't) (?:see|view|read)[^*\n]+\n",
            # Clean up extra newlines and spaces after removals
            r"\n{3,}",
        ]

        # Clean the body
        cleaned_body = translated_body
        for pattern in web_version_patterns:
            cleaned_body = re.sub(pattern, "", cleaned_body, flags=re.MULTILINE | re.IGNORECASE)
        
        # Replace URLs with translated "link" word
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        cleaned_body = re.sub(url_pattern, translated_prompts['link'], cleaned_body)
        
        # Remove extra newlines and whitespace
        cleaned_body = re.sub(r'\n{3,}', '\n\n', cleaned_body.strip())

        # Get original English text from email_data
        original_body = email_data.get('original_body', email_data.get('body', ''))
        original_subject = email_data.get('original_subject', email_data.get('subject', ''))

        # First clean the original English text
        cleaned_original_body = original_body
        for pattern in web_version_patterns:
            cleaned_original_body = re.sub(pattern, "", cleaned_original_body, flags=re.MULTILINE | re.IGNORECASE)
        
        # Replace URLs with "link" in original text
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        cleaned_original_body = re.sub(url_pattern, "link", cleaned_original_body)
        
        cleaned_original_body = re.sub(r'\n{3,}', '\n\n', cleaned_original_body.strip())

        try:
            # Generate summary from original English content first
            # Start with subject
            summary_parts = []
            if original_subject:
                summary_parts.append(original_subject)

            # Split original text into sentences (handling abbreviations and numbers carefully)
            text_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', cleaned_original_body)
            
            # Filter out short or unimportant sentences from original text
            important_sentences = []
            for sentence in text_sentences:
                # Clean the sentence
                clean_sent = sentence.strip()
                # Skip if too short or contains unwanted patterns
                if (len(clean_sent) < 10 or 
                    clean_sent.startswith('http') or 
                    '*' in clean_sent or
                    clean_sent.startswith('View') or
                    clean_sent.lower().startswith('this message')):
                    continue
                important_sentences.append(clean_sent)
            
            # Add first 2 important sentences to the summary
            if important_sentences:
                # Get the most relevant sentences (first 2)
                key_sentences = important_sentences[:2]
                summary_parts.extend(key_sentences)
            
            # Create complete English summary
            english_summary = ". ".join(summary_parts).strip()
            
            # Get translated versions of the summary and subject
            if lang != "English":
                # Translate the complete summary
                summary = mcp.translate(english_summary, target_language=lang).strip()
                # Translate the subject for display
                translated_subject = mcp.translate(original_subject, target_language=lang).strip()
            else:
                summary = english_summary
                translated_subject = original_subject

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            # Fallback to simple summary from original text
            try:
                # Simple fallback using first two sentences
                first_sentences = ". ".join(cleaned_original_body.split(".")[:2]) + "."
                summary = mcp.translate(first_sentences, target_language=lang).strip() if lang != "English" else first_sentences
                translated_subject = email_data['subject']  # Use original subject as fallback
            except Exception as e2:
                logger.error(f"Error in fallback summary generation: {e2}")
                summary = ""
                translated_subject = email_data['subject']

        # Replace URLs with translated 'link' word in the body
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        processed_body = re.sub(url_pattern, translated_prompts['link'], cleaned_body)

        # Build the speech text focusing on summary
        speech_text = (
            f"{translated_prompts['from']} {email_data['from']}. "
            f"{translated_prompts['subject']} {translated_subject}. "
            f"{translated_prompts['summary_intro']} "
        )

        # Add summary if successfully generated
        if summary:
            speech_text += f"{summary}"
        else:
            # Fallback to a brief introduction if no summary
            speech_text += f"{translated_prompts['summary_intro']}"
        
        return speech_text

    def generate_audio(self, email_data: dict, translated_body: str, lang: str, email_id: str) -> bool:
        """
        Generate audio file without playing it. Returns True if successful.
        """
        try:
            # Format the text
            speech_text = self.format_email_for_speech(email_data, translated_body, lang)
            
            # Get language code
            lang_code = LANG_MAP.get(lang, "en")
            
            # Generate new file
            cache_key = self.get_cache_key(email_id, lang)
            filename = f"speech_{email_id}_{lang}_{int(time.time())}.mp3"
            
            # Generate audio file
            tts = gTTS(text=speech_text, lang=lang_code)
            tts.save(filename)
            
            # Clean up old files and cache new one
            self.cleanup_old_files(except_key=cache_key)
            self._cached_files[cache_key] = filename
            
            return True
            
        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            return False

    def cleanup_audio_file(self, email_id: str, lang: str) -> bool:
        """
        Clean up specific audio file for an email and language
        """
        try:
            cache_key = self.get_cache_key(email_id, lang)
            if cache_key in self._cached_files:
                filename = self._cached_files[cache_key]
                if os.path.exists(filename):
                    os.remove(filename)
                    logger.info(f"Successfully deleted audio file: {filename}")
                del self._cached_files[cache_key]
                return True
            return False
        except Exception as e:
            logger.error(f"Error cleaning up audio file: {e}")
            return False

# Global instance
tts_service = TTSService()