
import os
import httpx
import json
from typing import List, Dict, Any

class BlackboxClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.blackbox.ai"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def chat_completions(self, model: str, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status() # Lanza una excepción para códigos de estado 4xx/5xx
            return response.json()

# --- Definiciones de Herramientas para la API de Blackbox AI ---

def search_web_tool_definition():
    return {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Busca información en la web utilizando un motor de búsqueda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La consulta de búsqueda para la web."
                    }
                },
                "required": ["query"]
            }
        }
    }

def generate_image_tool_definition():
    return {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Genera una imagen a partir de un prompt de texto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "La descripción textual de la imagen a generar."
                    }
                },
                "required": ["prompt"]
            }
        }
    }

# Puedes añadir más definiciones de herramientas aquí (ej. generate_video, text_to_speech)
