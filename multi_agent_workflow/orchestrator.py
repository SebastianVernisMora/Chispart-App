
import os
from .agents import ResearcherAgent, ContentGeneratorAgent
from .tools import BlackboxClient # Asumiendo que crearás un cliente API

class OrchestratorAgent:
    def __init__(self, api_key: str):
        self.blackbox_client = BlackboxClient(api_key)
        self.researcher_agent = ResearcherAgent(api_key)
        self.content_generator_agent = ContentGeneratorAgent(api_key)
        # Puedes añadir más agentes aquí

    async def process_request(self, user_query: str):
        print(f"Orquestador: Recibida la solicitud del usuario: '{user_query}'")

        # Paso 1: Delegar investigación
        print("Orquestador: Delegando tarea de investigación...")
        research_results = await self.researcher_agent.research(user_query)
        print(f"Orquestador: Investigación completada. Resultados: {research_results[:100]}...") # Mostrar solo un fragmento

        # Paso 2: Delegar generación de contenido
        print("Orquestador: Delegando tarea de generación de contenido...")
        generated_content = await self.content_generator_agent.generate_report(research_results)
        print(f"Orquestador: Contenido generado. Fragmento: {generated_content[:100]}...")

        # Aquí podrías añadir lógica para generar imágenes/videos si la solicitud lo requiere
        # Por ejemplo, si user_query contiene "con una imagen"

        print("Orquestador: Tarea completada. Consolidando respuesta.")
        final_response = f"Aquí está el resultado de tu solicitud:

Reporte: {generated_content}"
        return final_response

# Ejemplo de uso (esto iría en main.py)
async def main():
    api_key = os.getenv("BLACKBOX_API_KEY")
    if not api_key:
        print("Error: La variable de entorno BLACKBOX_API_KEY no está configurada.")
        return

    orchestrator = OrchestratorAgent(api_key)
    response = await orchestrator.process_request("Genera un resumen sobre la historia de la inteligencia artificial y una imagen representativa.")
    print("\n--- Respuesta Final del Orquestador ---")
    print(response)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
