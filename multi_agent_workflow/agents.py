
import os
import json
from typing import List, Dict, Any

# Asumiendo que BlackboxClient se define en tools.py
from .tools import BlackboxClient, search_web_tool_definition, generate_image_tool_definition

class BaseAgent:
    def __init__(self, api_key: str):
        self.client = BlackboxClient(api_key)

    async def _call_blackbox_chat(self, messages: List[Dict[str, str]], model: str, tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Método auxiliar para llamar al endpoint de chat de Blackbox
        # Aquí se implementaría la lógica de reintento, manejo de errores, etc.
        try:
            response = await self.client.chat_completions(
                model=model,
                messages=messages,
                tools=tools
            )
            return response
        except Exception as e:
            print(f"Error al llamar a Blackbox API: {e}")
            return {"error": str(e)}

class ResearcherAgent(BaseAgent):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.tools = [search_web_tool_definition()] # Definición de la herramienta de búsqueda web
        self.model = "blackboxai/openai/gpt-4o-mini" # Modelo para razonamiento del investigador

    async def research(self, query: str) -> str:
        print(f"Investigador: Recibida consulta de investigación: '{query}'")
        messages = [
            {"role": "system", "content": "Eres un agente investigador experto. Tu tarea es usar las herramientas disponibles para encontrar información relevante."},
            {"role": "user", "content": f"Necesito información sobre: {query}"}
        ]

        # Primer intento: dejar que el LLM decida si usar la herramienta
        response = await self._call_blackbox_chat(messages, self.model, tools=self.tools)

        if "choices" in response and response["choices"][0]["finish_reason"] == "tool_calls":
            tool_calls = response["choices"][0]["message"]["tool_calls"]
            tool_results = []
            for tool_call in tool_calls:
                if tool_call["function"]["name"] == "search_web":
                    args = json.loads(tool_call["function"]["arguments"])
                    search_terms = args.get("query")
                    print(f"Investigador: Ejecutando herramienta search_web con query: {search_terms}")
                    # Aquí se llamaría a la función real de búsqueda web
                    # Por ahora, simulamos un resultado
                    simulated_result = f"Resultados simulados para '{search_terms}': La IA es un campo en rápido crecimiento con aplicaciones en muchos sectores."
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "output": simulated_result
                    })

            # Segundo intento: enviar los resultados de la herramienta de vuelta al LLM
            messages.append(response["choices"][0]["message"])
            for result in tool_results:
                messages.append({"role": "tool", "tool_call_id": result["tool_call_id"], "content": result["output"]})

            final_response = await self._call_blackbox_chat(messages, self.model, tools=self.tools)
            if "choices" in final_response:
                return final_response["choices"][0]["message"]["content"]
            else:
                return "No se pudo obtener una respuesta final de la investigación."
        elif "choices" in response:
            return response["choices"][0]["message"]["content"]
        else:
            return "No se pudo realizar la investigación."

class ContentGeneratorAgent(BaseAgent):
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.model = "blackboxai/openai/gpt-4o-mini" # Modelo para generación de contenido

    async def generate_report(self, research_data: str) -> str:
        print("Generador de Contenido: Generando reporte...")
        messages = [
            {"role": "system", "content": "Eres un agente generador de contenido experto. Tu tarea es redactar un reporte conciso y bien estructurado basado en los datos proporcionados."},
            {"role": "user", "content": f"Redacta un reporte basado en los siguientes datos: {research_data}"}
        ]
        response = await self._call_blackbox_chat(messages, self.model)
        if "choices" in response:
            return response["choices"][0]["message"]["content"]
        else:
            return "No se pudo generar el reporte."

    async def generate_image(self, prompt: str) -> str:
        print(f"Generador de Contenido: Generando imagen para el prompt: '{prompt}'")
        # Usamos el endpoint de chat con un modelo de imagen
        messages = [
            {"role": "user", "content": prompt}
        ]
        # Asegúrate de usar un modelo de imagen válido aquí
        image_model = "blackboxai/black-forest-labs/flux-pro" # Ejemplo de modelo de imagen
        response = await self._call_blackbox_chat(messages, image_model)
        if "choices" in response and "content" in response["choices"][0]["message"]:
            return response["choices"][0]["message"]["content"] # Debería ser la URL de la imagen
        else:
            return "No se pudo generar la imagen."

# Puedes añadir más agentes aquí (ej. ReviewerAgent, VideoGeneratorAgent)
