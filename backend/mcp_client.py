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
    
    def translate_to_marathi(self, text: str) -> str:
        """
        Translate any text to Marathi using local LLaMA3 model via Ollama
        """
        prompt = f"Translate the following text into Marathi. Only return the Marathi translation without any additional commentary:\n\n{text}"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": self.temperature,
            "stream": False
        }
        
        try:
            response = requests.post(self.api_url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', 'Translation failed')
                
        except Exception as e:
            print(f"Translation error: {str(e)}")
            return f"Error: {str(e)}"
