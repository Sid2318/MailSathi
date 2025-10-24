# mcp_client.py
import requests
import json

class MCPClient:
    def __init__(self, temperature=0):
        """
        Initialize the client with local Ollama API
        """
        self.api_url = "http://localhost:11434/api/generate"
        self.model = "llama3"
        self.temperature = temperature
    
    def translate(self, text: str, target_language: str = "Marathi") -> str:
        """
        Translate any text to the specified target_language using local LLaMA3 model via Ollama.
        Returns the translated text (best-effort) or an error string.
        """
        if not text:
            return ""

        # Build a concise prompt that asks for plain translated text only
        prompt = (
            f"Translate the following text into {target_language}. "
            "Only return the translated text without any additional commentary:\n\n"
            f"{text}"
        )

        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False
        }

        # Retry with exponential backoff in case Ollama is busy or slow
        retries = 3
        timeout = 120  # seconds
        backoff = 1.5
        for attempt in range(1, retries + 1):
            try:
                response = requests.post(self.api_url, json=payload, timeout=timeout)
                response.raise_for_status()

                result = response.json()
                # Ollama's response field may be 'response' or similar; handle gracefully
                return result.get('response') or result.get('text') or str(result)

            except requests.exceptions.ReadTimeout:
                msg = f"Translation timeout (attempt {attempt}/{retries})."
                print(msg)
                if attempt == retries:
                    return f"Error: Ollama timed out after {timeout}s. Is the server running and the model available?"
            except requests.exceptions.ConnectionError as e:
                msg = f"Connection error contacting Ollama (attempt {attempt}/{retries}): {e}"
                print(msg)
                if attempt == retries:
                    return f"Error: Could not connect to Ollama at {self.api_url}. Is 'ollama serve' running?"
            except Exception as e:
                # Other errors (bad response, JSON decode, HTTP error)
                print(f"Translation error (attempt {attempt}/{retries}): {str(e)}")
                if attempt == retries:
                    return f"Error: {str(e)}"

            # Wait before next attempt
            try:
                import time
                time.sleep(backoff ** attempt)
            except Exception:
                pass

    def translate_to_marathi(self, text: str) -> str:
        """Backward-compatible helper for Marathi translation."""
        return self.translate(text, target_language="Marathi")
