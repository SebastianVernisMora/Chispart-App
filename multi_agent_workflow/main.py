
import asyncio
import os
from dotenv import load_dotenv
from .orchestrator import OrchestratorAgent

async def main():
    # Cargar variables de entorno desde el archivo .env en la raíz del proyecto
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

    api_key = os.getenv("BLACKBOX_API_KEY")
    if not api_key:
        print("Error: La variable de entorno BLACKBOX_API_KEY no está configurada en .env.")
        print("Asegúrate de tener un archivo .env en la raíz del proyecto con BLACKBOX_API_KEY=tu_clave_aqui")
        return

    orchestrator = OrchestratorAgent(api_key)
    
    print("\n--- Iniciando Workflow Multiagente ---")
    user_input = input("Ingresa tu solicitud (ej. 'Genera un resumen sobre la historia de la inteligencia artificial y una imagen representativa.'): ")
    
    response = await orchestrator.process_request(user_input)
    
    print("\n--- Respuesta Final del Orquestador ---")
    print(response)

if __name__ == "__main__":
    asyncio.run(main())
