#!/usr/bin/env python3
"""
Chispart AI - Plataforma de IA multiagente
Servidor FastAPI para la plataforma de creación con múltiples agentes IA
"""

import os
import json
import logging
import shutil
from typing import Optional, Dict, Any, List
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from blackbox_hybrid_tool.core.ai_client import AIOrchestrator
from blackbox_hybrid_tool.utils.patcher import apply_unified_diff
from blackbox_hybrid_tool.utils.self_repo import ensure_embedded_snapshot

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MODEL_CATALOG = {
    "Video": [
        "blackboxai/google/veo-3",
        "blackboxai/google/veo-3-fast",
    ],
    "Image": [
        "blackboxai/black-forest-labs/flux-1.1-pro-ultra",
        "blackboxai/black-forest-labs/flux-schnell",
        "blackboxai/bytedance/hyper-flux-8step",
        "blackboxai/stability-ai/stable-diffusion",
        "blackboxai/prompthero/openjourney",
    ],
    "Text": [
        "blackboxai/google/gemma-2-9b-it:free",
        "blackboxai/mistralai/mistral-7b-instruct:free",
        "blackboxai/meta-llama/llama-3.1-8b-instruct",
    ]
}

# Configuración de límites por modelo para imágenes
IMAGE_MODEL_LIMITS = {
    # Modelos que permiten 1 imagen por solicitud
    "blackboxai/salesforce/blip": 1,
    "blackboxai/andreasjansson/blip-2": 1,
    "blackboxai/philz1337x/clarity-upscaler": 1,
    "blackboxai/krthr/clip-embeddings": 1,
    "blackboxai/sczhou/codeformer": 1,
    "blackboxai/jagilley/controlnet-scribble": 1,
    "blackboxai/fofr/face-to-many": 1,
    "blackboxai/black-forest-labs/flux-1.1-pro": 1,
    "blackboxai/black-forest-labs/flux-1.1-pro-ultra": 1,
    "blackboxai/black-forest-labs/flux-kontext-pro": 1,
    "blackboxai/black-forest-labs/flux-pro": 1,
    "blackboxai/prunaai/flux.1-dev": 1,
    "blackboxai/tencentarc/gfpgan": 1,
    "blackboxai/xinntao/gfpgan": 1,
    "blackboxai/adirik/grounding-dino": 1,
    "blackboxai/pengdaqian2020/image-tagger": 1,
    "blackboxai/allenhooo/lama": 1,
    "blackboxai/yorickvp/llava-13b": 1,
    "blackboxai/google/nano-banana": 1,
    "blackboxai/falcons-ai/nsfw_image_detection": 1,
    "blackboxai/nightmareai/real-esrgan": 1,
    "blackboxai/daanelson/real-esrgan-a100": 1,
    "blackboxai/abiruyt/text-extract-ocr": 1,
    
    # Modelos que permiten 4 imágenes por solicitud
    "blackboxai/black-forest-labs/flux-dev": 4,
    "blackboxai/black-forest-labs/flux-schnell": 4,
    "blackboxai/bytedance/hyper-flux-8step": 4,
    "blackboxai/ai-forever/kandinsky-2.2": 4,
    "blackboxai/datacte/proteus-v0.2": 4,
    "blackboxai/stability-ai/sdxl": 4,
    "blackboxai/fofr/sdxl-emoji": 4,
    "blackboxai/bytedance/sdxl-lightning-4step": 4,
    "blackboxai/stability-ai/stable-diffusion": 4,
    "blackboxai/stability-ai/stable-diffusion-inpainting": 4,
    
    # Modelos con más capacidad
    "blackboxai/prompthero/openjourney": 10,
}

# Valor por defecto para modelos no listados
DEFAULT_IMAGE_LIMIT = 1

# Branding configurable por variables de entorno
APP_NAME = os.getenv("APP_NAME", "Blackbox Hybrid Tool")
APP_TAGLINE = os.getenv("APP_TAGLINE", "API para herramienta híbrida de modelos AI")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Crear aplicación FastAPI con branding configurable
app = FastAPI(
    title=f"{APP_NAME} API",
    description=APP_TAGLINE,
    version=APP_VERSION,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("Middleware CORS configurado con allow_origins=['*']")

# Servir archivos estáticos (playground y frontend principal)
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info(f"Directorio static montado desde: {os.path.abspath('static')}")
    
    app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")
    logger.info(f"Directorio frontend montado desde: {os.path.abspath('frontend')}")
except Exception as e:
    # Si no existe el directorio, omitir sin fallar
    logger.error(f"Error al montar directorios estáticos: {e}")
    pass

# Modelo de datos para las solicitudes
class ChatRequest(BaseModel):
    prompt: str
    model_type: Optional[str] = None
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7
    analyze_directory: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ChatResponse(BaseModel):
    response: str
    model_used: str
    status: str = "success"

class SwitchModelRequest(BaseModel):
    model: str  # Identificador de modelo de Blackbox, ej: "blackboxai/openai/o1"

class WriteFileRequest(BaseModel):
    path: str
    content: str
    overwrite: bool = False

class ApplyPatchRequest(BaseModel):
    patch: str  # unified diff text
    root: Optional[str] = None

class ListDirectoryRequest(BaseModel):
    path: str = "."
    show_hidden: bool = False

class ReadFileRequest(BaseModel):
    path: str

class CreateDirectoryRequest(BaseModel):
    path: str

class DeleteFileRequest(BaseModel):
    path: str

class AnalyzeDirectoryRequest(BaseModel):
    path: str = "."
    max_files: int = 50
    include_content: bool = True

class ChangeRootRequest(BaseModel):
    new_root: str

# Instancia global del orquestador
orchestrator = None

@app.on_event("startup")
async def startup_event():
    """Inicializar el orquestador al iniciar la aplicación"""
    global orchestrator
    try:
        config_file = os.getenv("CONFIG_FILE", "blackbox_hybrid_tool/config/models.json")
        orchestrator = AIOrchestrator(config_file)
        # Asegurar snapshot embebido si está habilitado
        if os.getenv("AUTO_SNAPSHOT", "true").lower() in ("1", "true", "yes"):
            try:
                changed, meta = ensure_embedded_snapshot(Path(".").resolve())
                if changed:
                    logger.info(f"Snapshot embebido actualizado (files={meta.get('file_count')}, hash={meta.get('sha256')[:8]}...)")
                else:
                    logger.info("Snapshot embebido al día")
            except Exception:
                # No bloquear arranque
                logger.warning("No se pudo generar/verificar snapshot embebido")
        # Importar modelos disponibles desde CSV si existe
        csv_path = os.getenv(
            "BLACKBOX_MODELS_CSV",
            "/home/sebastianvernis/Música/blackboxai-1756783978577-main/modelos_blackbox.csv",
        )
        try:
            if os.path.exists(csv_path):
                count = orchestrator.import_available_models_from_csv(csv_path)
                if count:
                    logger.info(f"Modelos disponibles importados desde CSV: {count}")
        except Exception as _:
            # No bloquear arranque si falla la importación
            pass

        logger.info("Orquestador AI inicializado correctamente")
    except Exception as e:
        logger.error(f"Error al inicializar el orquestador: {str(e)}")
        raise

@app.get("/")
async def read_root():
    """Sirve la interfaz de chat principal."""
    # Servir la interfaz de chat completa desde frontend/index.html
    frontend_path = os.path.join("frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path, media_type="text/html", headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache", 
            "Expires": "0"
        })
    # Fallback a playground si no existe frontend/index.html
    playground_path = os.path.join("static", "playground.html")
    if os.path.exists(playground_path):
        return FileResponse(playground_path, media_type="text/html", headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache", 
            "Expires": "0"
        })
    # Último fallback: HTML minimalista
    return HTMLResponse("<html><body><h1>Error: No se encontró la interfaz</h1></body></html>")

@app.get("/fileexplorer")
async def file_explorer():
    """Interfaz para explorar archivos"""
    fileexplorer_path = os.path.join("static", "fileexplorer.html")
    if os.path.exists(fileexplorer_path):
        return FileResponse(fileexplorer_path, media_type="text/html", headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache", 
            "Expires": "0"
        })
    # Fallback si no existe el archivo
    return HTMLResponse("<html><body><h1>Error: No se encontró el explorador de archivos</h1></body></html>")

@app.get("/playground")
async def playground():
    """UI mínima para probar el chat desde el navegador"""
    index_path = os.path.join("static", "playground.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html", headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        })
    # HTML moderno con diseño visual e interactivo
    html = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>🤖 Blackbox AI Chat</title>
    <style>
      :root {
        --primary: #007acc;
        --primary-dark: #0056b3;
        --success: #28a745;
        --warning: #ffc107;
        --danger: #dc3545;
        --bg: #f8f9fa;
        --surface: #ffffff;
        --text: #212529;
        --text-muted: #6c757d;
        --border: #dee2e6;
        --shadow: 0 2px 8px rgba(0,0,0,0.1);
      }
      
      * { box-sizing: border-box; }
      
      body { 
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        margin: 0; padding: 0; background: var(--bg); color: var(--text);
        line-height: 1.6;
      }
      
      .container {
        max-width: 1200px; margin: 0 auto; padding: 20px;
        display: grid; grid-template-columns: 300px 1fr; gap: 20px;
      }
      
      .sidebar {
        background: var(--surface); border-radius: 12px; padding: 20px;
        box-shadow: var(--shadow); height: fit-content;
      }
      
      .main-chat {
        background: var(--surface); border-radius: 12px; padding: 20px;
        box-shadow: var(--shadow); min-height: 600px; display: flex; flex-direction: column;
      }
      
      h1 { margin: 0 0 20px 0; color: var(--primary); display: flex; align-items: center; gap: 10px; }
      h2 { margin: 0 0 15px 0; font-size: 1.1rem; color: var(--text); }
      
      .tools-grid {
        display: grid; gap: 8px;
      }
      
      .tool-btn {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark));
        color: white; border: none; padding: 12px 16px; border-radius: 8px;
        cursor: pointer; transition: all 0.2s; font-size: 0.9rem;
        text-align: left; display: flex; align-items: center; gap: 8px;
      }
      
      .tool-btn:hover {
        transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,122,204,0.3);
      }
      
      .tool-btn:active { transform: translateY(0); }
      
      .input-group {
        margin-bottom: 15px;
      }
      
      .input-group label {
        display: block; margin-bottom: 5px; font-weight: 600; color: var(--text);
      }
      
      .form-control {
        width: 100%; padding: 12px; border: 2px solid var(--border);
        border-radius: 8px; font-size: 1rem; transition: border-color 0.2s;
        background: var(--surface);
      }
      
      .form-control:focus {
        outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(0,122,204,0.1);
      }
      
      textarea.form-control {
        resize: vertical; min-height: 120px; font-family: inherit;
      }
      
      .btn-group {
        display: flex; gap: 10px; align-items: center;
      }
      
      .btn {
        padding: 12px 24px; border: none; border-radius: 8px; cursor: pointer;
        font-weight: 600; font-size: 1rem; transition: all 0.2s;
        display: inline-flex; align-items: center; gap: 8px;
      }
      
      .btn-primary {
        background: linear-gradient(135deg, var(--primary), var(--primary-dark));
        color: white;
      }
      
      .btn-primary:hover {
        transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,122,204,0.3);
      }
      
      .btn-secondary {
        background: var(--text-muted); color: white;
      }
      
      .btn-secondary:hover {
        background: #5a6268; transform: translateY(-1px);
      }
      
      .status {
        display: inline-flex; align-items: center; gap: 8px;
        font-weight: 600; padding: 8px 16px; border-radius: 20px;
        background: var(--warning); color: #000;
        opacity: 0; transition: opacity 0.3s;
      }
      
      .status.show { opacity: 1; }
      
      .response-area {
        flex: 1; margin-top: 20px;
      }
      
      .response-content {
        background: #1a1a1a; color: #e0e0e0; padding: 20px; border-radius: 12px;
        font-family: 'Monaco', 'Menlo', monospace; font-size: 0.9rem;
        line-height: 1.5; white-space: pre-wrap; overflow: auto;
        min-height: 200px; max-height: 400px;
        border: 1px solid var(--border);
      }
      
      .loading {
        display: inline-block; width: 20px; height: 20px;
        border: 3px solid rgba(255,255,255,0.3);
        border-radius: 50%; border-top-color: white;
        animation: spin 1s ease-in-out infinite;
      }
      
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      
      .empty-state {
        color: var(--text-muted); font-style: italic; text-align: center;
        padding: 40px 20px;
      }
      
      @media (max-width: 768px) {
        .container {
          grid-template-columns: 1fr; gap: 15px; padding: 15px;
        }
        .sidebar { order: 2; }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="sidebar">
        <h2>🛠️ Herramientas Rápidas</h2>
        <div class="tools-grid">
          <button class="tool-btn" onclick="insertTool('generate-tests')">
            🧪 Generar Tests
          </button>
          <button class="tool-btn" onclick="insertTool('analyze-coverage')">
            📊 Cobertura
          </button>
          <button class="tool-btn" onclick="insertTool('media image-batch')">
            🖼️ Crear Imágenes
          </button>
          <button class="tool-btn" onclick="insertTool('profile create')">
            👤 Nuevo Perfil
          </button>
          <button class="tool-btn" onclick="insertTool('profile list')">
            📋 Listar Perfiles
          </button>
          <button class="tool-btn" onclick="insertTool('switch-model')">
            🔄 Cambiar Modelo
          </button>
          <button class="tool-btn" onclick="insertTool('repl')">
            💬 Chat Interactivo
          </button>
        </div>
        
        <h2 style="margin-top: 30px;">📋 Ejemplos</h2>
        <div class="tools-grid">
          <button class="tool-btn" onclick="insertExample('Explica este código: [pegar código]')">
            💡 Explicar Código
          </button>
          <button class="tool-btn" onclick="insertExample('Optimiza esta función para mejor rendimiento')">
            ⚡ Optimizar
          </button>
          <button class="tool-btn" onclick="insertExample('Encuentra bugs en este código')">
            🐛 Debug
          </button>
          <button class="tool-btn" onclick="insertExample('Documenta esta función')">
            📚 Documentar
          </button>
        </div>
      </div>
      
      <div class="main-chat">
        <h1>
          🤖 Blackbox AI Chat
        </h1>
        
        <div class="input-group">
          <label for="model">Modelo (opcional)</label>
          <input id="model" class="form-control" type="text" 
                 placeholder="blackboxai/openai/o1, blackboxai/anthropic/claude-3.5-sonnet" />
        </div>
        
        <div class="input-group">
          <label for="prompt">Prompt</label>
          <textarea id="prompt" class="form-control" 
                    placeholder="Describe tu tarea o pregunta...&#10;&#10;Ejemplos:&#10;• Explica este código: [pegar código]&#10;• Genera tests para la función X&#10;• Optimiza esta consulta SQL&#10;• Crea un perfil de marca para mi startup"></textarea>
        </div>
        
        <div class="btn-group">
          <button class="btn btn-primary" onclick="send()">
            <span id="send-text">🚀 Enviar</span>
            <div id="loading" class="loading" style="display: none;"></div>
          </button>
          <button class="btn btn-secondary" onclick="clearChat()">🗑️ Limpiar</button>
          <div id="status" class="status"></div>
        </div>
        
        <div class="response-area">
          <h2>Respuesta</h2>
          <div id="out" class="response-content">
            <div class="empty-state">💭 Listo para recibir tu consulta...</div>
          </div>
        </div>
      </div>
    </div>
    <script>
      // Función para enviar el prompt al chat
      async function send() {
        const model = document.getElementById('model').value.trim() || null;
        const prompt = document.getElementById('prompt').value.trim();
        const out = document.getElementById('out');
        const status = document.getElementById('status');
        const sendText = document.getElementById('send-text');
        const loading = document.getElementById('loading');
        
        if (!prompt) {
          out.innerHTML = '<div style="color: #dc3545; text-align: center; padding: 20px;">⚠️ Escribe un prompt primero</div>';
          return;
        }
        
        // UI de carga
        status.textContent = 'Enviando...';
        status.classList.add('show');
        sendText.style.display = 'none';
        loading.style.display = 'inline-block';
        
        try {
          const res = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, model_type: model })
          });
          
          const data = await res.json();
          
          if (!res.ok) {
            out.innerHTML = `<div style="color: #dc3545; padding: 20px;">❌ Error ${res.status}:<br><br>${data.detail || JSON.stringify(data, null, 2)}</div>`;
          } else {
            // Formatear la respuesta con mejor estilo
            const response = data.response || 'Sin respuesta';
            out.innerHTML = `<div style="color: #28a745; margin-bottom: 10px;">✅ Respuesta generada:</div>${escapeHtml(response)}`;
          }
        } catch (err) {
          out.innerHTML = `<div style="color: #dc3545; padding: 20px;">🚫 Error de conexión:<br><br>${err.message}</div>`;
        } finally {
          status.classList.remove('show');
          sendText.style.display = 'inline';
          loading.style.display = 'none';
        }
      }
      
      // Función para insertar herramientas en el prompt
      function insertTool(tool) {
        const prompt = document.getElementById('prompt');
        const currentText = prompt.value;
        const newText = currentText ? `${currentText}\n\n${tool} ` : `${tool} `;
        prompt.value = newText;
        prompt.focus();
        // Posicionar cursor al final
        prompt.setSelectionRange(newText.length, newText.length);
      }
      
      // Función para insertar ejemplos
      function insertExample(example) {
        const prompt = document.getElementById('prompt');
        prompt.value = example;
        prompt.focus();
      }
      
      // Función para limpiar el chat
      function clearChat() {
        document.getElementById('prompt').value = '';
        document.getElementById('out').innerHTML = '<div class="empty-state">💭 Listo para recibir tu consulta...</div>';
        document.getElementById('model').value = '';
      }
      
      // Función para escapar HTML
      function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
      }
      
      // Permitir Ctrl+Enter para enviar
      document.getElementById('prompt').addEventListener('keydown', function(e) {
        if (e.ctrlKey && e.key === 'Enter') {
          send();
        }
      });
      
      // Auto-resize del textarea
      document.getElementById('prompt').addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.max(120, this.scrollHeight) + 'px';
      });
    </script>
  </body>
</html>
    """
    return HTMLResponse(content=html)

@app.get("/health")
async def health_check():
    """Endpoint de verificación de salud"""
    return {"status": "healthy"}

async def handle_special_command(command: str) -> ChatResponse:
    """Maneja comandos especiales de herramientas"""
    try:
        parts = command.split()
        base_command = parts[0]
        
        if base_command == "generate-tests":
            if len(parts) < 2:
                return ChatResponse(response="❌ Error: Necesitas especificar el archivo para generar tests.\n\nEjemplo: generate-tests mi_archivo.py", model_used="command-handler")
            filename = parts[1]
            return ChatResponse(response=f"🧪 Generando tests para {filename}...\n\n⚠️ Esta funcionalidad requiere acceso al CLI completo.\n\nPara generar tests reales, usa:\n```bash\nbb generate-tests {filename}\n```", model_used="command-handler")
        
        elif base_command == "analyze-coverage":
            return ChatResponse(response="📊 Analizando cobertura de código...\n\n⚠️ Esta funcionalidad requiere acceso al CLI completo.\n\nPara analizar cobertura real, usa:\n```bash\nbb analyze-coverage [ruta]\n```", model_used="command-handler")
        
        elif base_command == "media":
            if len(parts) < 2:
                return ChatResponse(response="🖼️ Comandos de media disponibles:\n\n• media image-batch - Crear múltiples imágenes\n• media profile create - Crear perfil de marca\n• media profile list - Listar perfiles\n\n⚠️ Funcionalidad completa disponible en CLI:\n```bash\nbb media --help\n```", model_used="command-handler")
            subcommand = parts[1]
            if subcommand == "image-batch":
                return ChatResponse(response="🖼️ Creando lote de imágenes...\n\n⚠️ Esta funcionalidad requiere configuración adicional.\n\nPara crear imágenes reales, usa el CLI:\n```bash\nbb media image-batch\n```", model_used="command-handler")
            elif subcommand == "profile":
                return ChatResponse(response="👤 Gestión de perfiles de marca:\n\n• create - Crear nuevo perfil\n• list - Listar perfiles existentes\n• activate <nombre> - Activar perfil\n• show - Ver detalles\n\n⚠️ Usa el CLI para funcionalidad completa:\n```bash\nbb media profile --help\n```", model_used="command-handler")
        
        elif base_command == "profile":
            return ChatResponse(response="👤 Comandos de perfil:\n\n• profile create - Crear perfil\n• profile list - Listar perfiles\n• profile activate <nombre> - Activar perfil\n\n⚠️ Usa el CLI completo:\n```bash\nbb media profile --help\n```", model_used="command-handler")
        
        elif base_command == "switch-model":
            return ChatResponse(response="🔄 Para cambiar modelo, usa el endpoint dedicado:\n\n```javascript\nfetch('/models/switch', {\n  method: 'POST',\n  headers: {'Content-Type': 'application/json'},\n  body: JSON.stringify({model: 'nuevo-modelo'})\n})\n```\n\nO desde CLI:\n```bash\nbb switch-model <modelo>\n```", model_used="command-handler")
        
        elif base_command == "repl":
            return ChatResponse(response="💬 El modo REPL interactivo está disponible en el CLI:\n\n```bash\nbb repl\n```\n\n💡 Esta interfaz web YA es interactiva - puedes seguir chateando aquí!", model_used="command-handler")
        
        else:
            return ChatResponse(response=f"❓ Comando no reconocido: {base_command}\n\n🛠️ Comandos disponibles:\n• generate-tests <archivo>\n• analyze-coverage\n• media image-batch\n• profile create/list\n• switch-model <modelo>\n• repl", model_used="command-handler")
            
    except Exception as e:
        return ChatResponse(response=f"❌ Error procesando comando: {str(e)}\n\n💡 Tip: Intenta usar un prompt normal en lugar de un comando CLI.", model_used="command-handler")


def create_multiprompt_sequence(prompt: str, media_type: str = "Video") -> list:
    """
    Divide un prompt largo en una secuencia de prompts coherentes.
    
    Args:
        prompt (str): El prompt original en español
        media_type (str): Tipo de media ("Video" o "Image")
        
    Returns:
        list: Lista de prompts secuenciales en inglés
    """
    # Usar Claude para analizar el prompt y dividirlo en secuencias coherentes
    if media_type == "Video":
        analysis_prompt = f"""
        I need to create a longer video (more than 8 seconds) by dividing it into coherent sequential segments.
        
        Please analyze this video request: "{prompt}"
        
        Then:
        1. Determine if this requires multiple segments (assume anything narrative or with multiple scenes does)
        2. Create 2-4 sequential prompts that together tell the complete story/concept
        3. Each prompt should build on the previous one with visual continuity
        4. Each prompt should be fully standalone yet maintain style consistency
        5. Translate everything to English and enhance with cinematic details
        
        Return ONLY a JSON array of prompts, with each element being one sequential prompt.
        Format: ["prompt1", "prompt2", "prompt3"]
        Do not include any explanation or other text.
        """
    else:  # Image
        analysis_prompt = f"""
        I need to create a series of related images by dividing a complex request into coherent separate image prompts.
        
        Please analyze this image request: "{prompt}"
        
        Then:
        1. Determine if this request contains multiple distinct elements that should be separate images
        2. Create 2-4 distinct image prompts that together cover all aspects of the request
        3. Each prompt should focus on a different element but maintain visual style consistency
        4. Each prompt should be fully standalone yet fit into the overall theme
        5. Translate everything to English and enhance with visual details for better image generation
        
        Return ONLY a JSON array of prompts, with each element being one image prompt.
        Format: ["prompt1", "prompt2", "prompt3"]
        Do not include any explanation or other text.
        """
    
    try:
        # Usar un modelo específico para el análisis y segmentación
        analysis_model = "blackboxai/anthropic/claude-3-haiku"
        response = orchestrator.generate_response(
            analysis_prompt,
            model_type=analysis_model,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Extraer respuesta
        if isinstance(response, dict):
            response_text = response.get("content", "").strip()
        else:
            response_text = response.strip() if isinstance(response, str) else ""
        
        # Si la respuesta está vacía o hay un error, procesar como un solo prompt
        if not response_text:
            logger.warning("No se pudo segmentar el prompt. Tratando como prompt único.")
            return [enhance_video_prompt(prompt)]
        
        # Intentar interpretar la respuesta como JSON
        import json
        try:
            prompts = json.loads(response_text)
            if isinstance(prompts, list) and len(prompts) > 0:
                logger.info(f"Prompt dividido en {len(prompts)} segmentos secuenciales")
                return prompts
            else:
                raise ValueError("Formato de respuesta incorrecto")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Error al procesar la segmentación: {e}")
            # Si no podemos procesar el JSON, intentamos mejorar el prompt original
            return [enhance_video_prompt(prompt)]
            
    except Exception as e:
        logger.error(f"Error al crear secuencia multiprompt: {e}")
        return [enhance_video_prompt(prompt)]  # Fallback a un solo prompt mejorado


def enhance_video_prompt(prompt: str) -> str:
    """
    Mejora y traduce los prompts de video para maximizar la efectividad.
    
    Args:
        prompt (str): El prompt original en español
        
    Returns:
        str: Prompt mejorado y traducido al inglés
    """
    # Usar Claude para mejorar y traducir el prompt
    enhanced_prompt = f"""
    I need to create a high-quality video with an AI generator. Please help me by:
    
    1. Translating this Spanish prompt to English
    2. Enhancing it with additional details for better video generation
    3. Adding relevant cinematic terms (camera angles, lighting, movement)
    4. Keeping the core idea intact while making it more descriptive
    
    Original prompt: "{prompt}"
    
    Respond ONLY with the enhanced English prompt, nothing else.
    """
    
    try:
        # Usar un modelo específico para traducción y mejora
        translation_model = "blackboxai/anthropic/claude-3-haiku"
        response = orchestrator.generate_response(
            enhanced_prompt,
            model_type=translation_model,
            temperature=0.7,
            max_tokens=500
        )
        
        # Extraer respuesta
        if isinstance(response, dict):
            enhanced_text = response.get("content", "").strip()
        else:
            enhanced_text = response.strip() if isinstance(response, str) else ""
        
        # Si la respuesta está vacía o hay un error, volver al prompt original
        if not enhanced_text:
            logger.warning("No se pudo mejorar el prompt de video. Usando el original.")
            return prompt
            
        logger.info(f"Prompt de video mejorado: {enhanced_text}")
        return enhanced_text
    except Exception as e:
        logger.error(f"Error al mejorar prompt de video: {e}")
        return prompt  # Fallback al prompt original


def update_media_response_multi(media_urls, media_type):
    """
    Formatea la respuesta para incluir múltiples URLs de medios para reproducción embebida.
    
    Args:
        media_urls (list): Lista de URLs de medios generados
        media_type (str): Tipo de medio ('Image' o 'Video')
        
    Returns:
        str: Respuesta formateada
    """
    # Verificar que tenemos al menos una URL
    if not media_urls or not isinstance(media_urls, list) or len(media_urls) == 0:
        return f"No se pudo generar el {media_type.lower()}. Intenta con una descripción diferente."
    
    # Contar cuántos segmentos se generaron correctamente
    valid_urls = [url for url in media_urls if url and url.startswith("http")]
    
    if not valid_urls:
        return f"No se pudo generar el {media_type.lower()}. Intenta con una descripción diferente."
    
    # Formatear respuesta con todas las URLs
    response = f"He generado tu {media_type.lower()} en {len(valid_urls)} segmentos secuenciales:\n\n"
    
    # Añadir cada URL en una línea separada para que sea embebida
    for i, url in enumerate(valid_urls):
        # Verificar si es un formato embebible
        media_extension = url.split('.')[-1].lower().split('?')[0] if '.' in url else ''
        is_embeddable = media_extension in ['mp4', 'webm', 'ogg', 'jpg', 'jpeg', 'png', 'gif', 'webp']
        
        if is_embeddable:
            # Añadir URL en línea separada para embebido
            response += f"Segmento {i+1}:\n{url}\n\n"
        else:
            # Fallback para formatos no reconocibles
            response += f"Segmento {i+1}: [Enlace]({url})\n\n"
    
    return response


def update_media_response(media_url, media_type):
    """
    Formatea la respuesta para incluir la URL del medio para reproducción embebida.
    
    Args:
        media_url (str): URL del medio generado
        media_type (str): Tipo de medio ('Image' o 'Video')
        
    Returns:
        str: Respuesta formateada
    """
    # Verificar si hay una URL válida
    if not media_url or not media_url.startswith("http"):
        return f"No se pudo generar el {media_type.lower()}. Intenta con una descripción diferente."
    
    # Verificar si es un formato de archivo reconocible para embebido
    media_extension = media_url.split('.')[-1].lower().split('?')[0] if '.' in media_url else ''
    is_image = media_extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']
    is_video = media_extension in ['mp4', 'webm', 'ogg']
    
    if is_image or is_video:
        # Para asegurar que la URL sea reconocida y embebida, la ponemos sola en una línea
        return f"He generado tu {media_type.lower()}:\n{media_url}"
    else:
        # Fallback si la URL no termina con una extensión reconocible
        return f"He generado tu {media_type.lower()}. Aquí está el enlace: {media_url}"


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Endpoint para generar respuestas de IA con detección de intención y comandos especiales."""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="Orquestador no inicializado")
        
        # Verificar si se solicitó análisis de directorio
        if request.analyze_directory is not None:
            directory_analysis = await analyze_directory_background(request.analyze_directory)
            if "error" not in directory_analysis:
                response_text = f"He analizado el directorio '{request.analyze_directory}'. Contiene {directory_analysis['total_files']} archivos y {directory_analysis['total_directories']} directorios."
                return ChatResponse(response=response_text, model_used="directory-analyzer", status="success")
            else:
                return ChatResponse(response=directory_analysis["error"], model_used="directory-analyzer", status="error")
        
        # Detectar si es un comando especial
        prompt = request.prompt.strip()
        
        # Comandos especiales que se manejan de forma diferente
        if prompt.startswith(('generate-tests', 'analyze-coverage', 'media', 'profile', 'switch-model', 'repl')):
            return await handle_special_command(prompt)
        
        # Si no es un comando especial, proceder con el flujo normal

        # --- Detección de Intención Mejorada ---
        intent_prompt = f"""Clasifica la siguiente solicitud del usuario. Responde únicamente con una de estas opciones:
- IMAGEN: si pide crear, generar, diseñar imágenes, fotos, gráficos, logos, ilustraciones
- VIDEO: si pide crear, generar videos, animaciones, clips
- CODIGO: si pide explicar código, generar tests, documentar funciones, optimizar, debuggear
- TEXTO: para cualquier otra consulta general, preguntas, explicaciones

Solicitud: '{request.prompt}'

Respuesta:"""
        
        # Usar un modelo rápido para clasificación
        classification_model = "blackboxai/mistralai/mistral-7b-instruct:free"
        
        intent_response = orchestrator.generate_response(
            intent_prompt,
            model_type=classification_model,
            max_tokens=10,
            temperature=0.0
        )
        
        # Manejar caso cuando la respuesta es un diccionario
        if isinstance(intent_response, dict):
            intent = intent_response.get("content", "TEXTO").strip().upper()
        else:
            intent = intent_response.strip().upper() if isinstance(intent_response, str) else "TEXTO"

        logger.info(f"Intención detectada: {intent} para el prompt: '{request.prompt}'")

        # Manejar diferentes tipos de intención
        if "CODIGO" in intent:
            # Para consultas de código, usar un modelo especializado en programación
            code_model = request.model_type or "blackboxai/anthropic/claude-3.5-sonnet"
            
            # Mejorar el prompt para consultas de código
            enhanced_prompt = f"""Como experto en programación, ayuda con esta consulta relacionada con código:

{request.prompt}

Por favor proporciona una respuesta detallada, clara y con ejemplos cuando sea apropiado."""
            
            response_data = orchestrator.generate_response(
                enhanced_prompt,
                model_type=code_model,
                temperature=0.3
            )
            
            # Manejar caso cuando la respuesta es un diccionario
            if isinstance(response_data, dict):
                response_text = response_data.get("content", "")
            else:
                response_text = response_data if isinstance(response_data, str) else ""
            
            return ChatResponse(
                response=response_text,
                model_used=code_model
            )

        elif "IMAGEN" in intent or "VIDEO" in intent:
            media_type = "Image" if "IMAGEN" in intent else "Video"
            
            # Flujo simplificado: seleccionar el primer modelo del catálogo para ese tipo
            media_model = MODEL_CATALOG[media_type][0]
            
            logger.info(f"Generando {media_type} con el modelo: {media_model}")
            
            # Para videos, mejorar y traducir el prompt
            if media_type == "Video":
                # Guardar el prompt original para contexto
                original_prompt = request.prompt
                
                # Analizar si necesitamos múltiples prompts para un video largo
                prompts_sequence = create_multiprompt_sequence(request.prompt, media_type="Video")
                
                logger.info(f"Prompt original: '{original_prompt}'")
                logger.info(f"Secuencia de prompts: {len(prompts_sequence)} segmentos")
                
                if len(prompts_sequence) > 1:
                    # Generar múltiples segmentos de video y combinarlos
                    video_urls = []
                    
                    for i, segment_prompt in enumerate(prompts_sequence):
                        logger.info(f"Generando segmento de video {i+1}/{len(prompts_sequence)}")
                        logger.info(f"Prompt del segmento: '{segment_prompt}'")
                        
                        # Generar cada segmento
                        segment_response = orchestrator.generate_response(
                            segment_prompt,
                            model_type=media_model
                        )
                        
                        # Extraer URL
                        if isinstance(segment_response, dict):
                            segment_url = segment_response.get("content", "")
                        else:
                            segment_url = segment_response if isinstance(segment_response, str) else ""
                        
                        if segment_url and segment_url.startswith("http"):
                            video_urls.append(segment_url)
                            logger.info(f"URL del segmento {i+1}: {segment_url}")
                        else:
                            logger.warning(f"No se pudo generar el segmento {i+1}")
                    
                    # Combinar respuesta con todas las URLs
                    if video_urls:
                        # Devolver la primera URL como respuesta principal, pero incluir todas en el mensaje
                        media_response = video_urls[0]
                        # Guardar todas las URLs para incluirlas en la respuesta final
                        request.metadata = {"all_video_segments": video_urls}
                    else:
                        # Si falló la generación múltiple, intentar con un solo prompt mejorado
                        logger.warning("Fallando a generación con prompt único")
                        enhanced_prompt = enhance_video_prompt(request.prompt)
                        media_response = orchestrator.generate_response(
                            enhanced_prompt,
                            model_type=media_model
                        )
                else:
                    # Usar el único prompt mejorado para la generación
                    enhanced_prompt = prompts_sequence[0]
                    logger.info(f"Prompt mejorado: '{enhanced_prompt}'")
                    
                    media_response = orchestrator.generate_response(
                        enhanced_prompt,
                        model_type=media_model
                    )
            else:  # Imágenes
                # Guardar el prompt original para contexto
                original_prompt = request.prompt
                
                # Analizar si necesitamos múltiples prompts para imágenes complejas
                prompts_sequence = create_multiprompt_sequence(request.prompt, media_type="Image")
                
                logger.info(f"Prompt original para imagen: '{original_prompt}'")
                logger.info(f"Secuencia de prompts para imagen: {len(prompts_sequence)} segmentos")
                
                if len(prompts_sequence) > 1:
                    # Generar múltiples imágenes relacionadas
                    image_urls = []
                    
                    # Obtener el límite de imágenes por solicitud para este modelo
                    model_limit = IMAGE_MODEL_LIMITS.get(media_model, DEFAULT_IMAGE_LIMIT)
                    logger.info(f"Modelo {media_model} permite {model_limit} imágenes por solicitud")
                    
                    # Si el modelo permite más de una imagen por solicitud y tenemos múltiples prompts
                    if model_limit > 1 and len(prompts_sequence) > 1:
                        # Procesar en lotes según el límite del modelo
                        for i in range(0, len(prompts_sequence), model_limit):
                            batch_prompts = prompts_sequence[i:i+model_limit]
                            logger.info(f"Procesando lote {i//model_limit + 1}, con {len(batch_prompts)} prompts")
                            
                            # Para cada prompt en el lote actual
                            for j, segment_prompt in enumerate(batch_prompts):
                                prompt_index = i + j
                                logger.info(f"Generando imagen {prompt_index+1}/{len(prompts_sequence)}")
                                logger.info(f"Prompt del segmento: '{segment_prompt}'")
                                
                                # Generar cada imagen
                                segment_response = orchestrator.generate_response(
                                    segment_prompt,
                                    model_type=media_model
                                )
                                
                                # Extraer URL
                                if isinstance(segment_response, dict):
                                    segment_url = segment_response.get("content", "")
                                else:
                                    segment_url = segment_response if isinstance(segment_response, str) else ""
                                
                                if segment_url and segment_url.startswith("http"):
                                    image_urls.append(segment_url)
                                    logger.info(f"URL de la imagen {prompt_index+1}: {segment_url}")
                                else:
                                    logger.warning(f"No se pudo generar la imagen {prompt_index+1}")
                    else:
                        # Modelo solo permite una imagen por solicitud o tenemos un solo prompt
                        for i, segment_prompt in enumerate(prompts_sequence):
                            logger.info(f"Generando imagen {i+1}/{len(prompts_sequence)}")
                            logger.info(f"Prompt del segmento: '{segment_prompt}'")
                            
                            # Generar cada imagen individualmente
                            segment_response = orchestrator.generate_response(
                                segment_prompt,
                                model_type=media_model
                            )
                            
                            # Extraer URL
                            if isinstance(segment_response, dict):
                                segment_url = segment_response.get("content", "")
                            else:
                                segment_url = segment_response if isinstance(segment_response, str) else ""
                            
                            if segment_url and segment_url.startswith("http"):
                                image_urls.append(segment_url)
                                logger.info(f"URL de la imagen {i+1}: {segment_url}")
                            else:
                                logger.warning(f"No se pudo generar la imagen {i+1}")
                    
                    # Combinar respuesta con todas las URLs
                    if image_urls:
                        # Devolver la primera URL como respuesta principal, pero incluir todas en el mensaje
                        media_response = image_urls[0]
                        # Guardar todas las URLs para incluirlas en la respuesta final
                        request.metadata = {"all_image_segments": image_urls}
                    else:
                        # Si falló la generación múltiple, intentar con un solo prompt mejorado
                        logger.warning("Fallando a generación con prompt único")
                        media_response = orchestrator.generate_response(
                            enhance_video_prompt(request.prompt),  # Reutilizamos la función de mejora
                            model_type=media_model
                        )
                else:
                    # Usar el único prompt mejorado para la generación
                    enhanced_prompt = prompts_sequence[0]
                    logger.info(f"Prompt mejorado para imagen: '{enhanced_prompt}'")
                    
                    media_response = orchestrator.generate_response(
                        enhanced_prompt,
                        model_type=media_model
                    )
            
            # Manejar caso cuando la respuesta es un diccionario
            if isinstance(media_response, dict):
                media_url = media_response.get("content", "")
            else:
                media_url = media_response if isinstance(media_response, str) else ""
            
            # Comprobar si tenemos múltiples segmentos de media
            all_video_segments = getattr(request, 'metadata', {}).get('all_video_segments', [])
            all_image_segments = getattr(request, 'metadata', {}).get('all_image_segments', [])
            
            if media_type == "Video" and all_video_segments and len(all_video_segments) > 1:
                # Formatear respuesta para múltiples segmentos de video
                response_text = update_media_response_multi(all_video_segments, media_type)
            elif media_type == "Image" and all_image_segments and len(all_image_segments) > 1:
                # Formatear respuesta para múltiples segmentos de imagen
                response_text = update_media_response_multi(all_image_segments, media_type)
            else:
                # Formatear respuesta con una sola URL para reproducción embebida
                response_text = update_media_response(media_url, media_type)
            
            return ChatResponse(
                response=response_text,
                model_used=media_model,
                status="success"
            )
        else: # TEXTO o fallback
            # Para consultas generales, usar el modelo especificado o el predeterminado
            text_model = request.model_type or "blackboxai/anthropic/claude-3.5-sonnet"
            
            response_data = orchestrator.generate_response(
                prompt=request.prompt,
                model_type=text_model,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )
            
            # Manejar caso cuando la respuesta es un diccionario
            if isinstance(response_data, dict):
                response_text = response_data.get("content", "")
            else:
                response_text = response_data if isinstance(response_data, str) else ""
            
            logger.info(f"Respuesta de texto generada usando modelo: {text_model}")
            return ChatResponse(
                response=response_text,
                model_used=text_model,
                status="success"
            )

    except Exception as e:
        logger.error(f"Error al procesar solicitud de chat: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/tools")
async def get_tools():
    """Devuelve una lista de herramientas y comandos disponibles."""
    tools = {
        "media": {
            "description": "Creación de contenido multimedia.",
            "subcommands": {
                "image-batch": "Crear múltiples imágenes con un perfil de marca.",
                "profile create": "Crear un nuevo perfil de marca.",
                "profile list": "Listar perfiles existentes.",
                "profile activate <nombre>": "Activar un perfil.",
                "profile show [--name <nombre>]": "Mostrar detalles de un perfil."
            }
        },
        "repl": {
            "description": "Iniciar una sesión de chat interactiva con contexto y herramientas."
        },
        "ai-query <prompt>": {
            "description": "Realizar una consulta directa a la IA."
        },
        "generate-tests <archivo>": {
            "description": "Genera tests automáticamente para un archivo."
        },
        "analyze-coverage <ruta>": {
            "description": "Analiza la cobertura de código."
        },
        "switch-model <modelo>": {
            "description": "Cambia el modelo de IA por defecto."
        }
    }
    return tools


class SetRootRequest(BaseModel):
    """Modelo para solicitar cambio de directorio raíz."""
    new_root: str


@app.get("/files")
async def list_files(path: str = "."):
    """Lista archivos y directorios en la ruta especificada."""
    try:
        logger.info(f"Solicitud de listado para ruta: {path}")
        
        # Normalizar y validar la ruta
        base_dir = os.environ.get("WRITE_ROOT", os.getcwd())
        target_path = os.path.normpath(os.path.join(base_dir, path))
        
        logger.info(f"Base dir: {base_dir}")
        logger.info(f"Target path normalizada: {target_path}")
        
        # Verificar que no se está intentando acceder a directorios por encima del base_dir
        if not os.path.abspath(target_path).startswith(os.path.abspath(base_dir)):
            logger.warning(f"Intento de acceso fuera del directorio base: {target_path}")
            return {"error": "No se permite acceder a rutas fuera del directorio base"}
        
        # Verificar que la ruta existe
        if not os.path.exists(target_path):
            logger.warning(f"Ruta no existe: {target_path}")
            return {"error": f"La ruta {path} no existe"}
        
        # Verificar que es un directorio
        if not os.path.isdir(target_path):
            logger.warning(f"Ruta no es un directorio: {target_path}")
            return {"error": f"{path} no es un directorio"}
        
        # Listar archivos y directorios
        files = []
        items = os.listdir(target_path)
        logger.info(f"Encontrados {len(items)} items en {target_path}")
        
        for item in items:
            # Ignorar archivos ocultos
            if item.startswith('.'):
                continue
                
            item_path = os.path.join(target_path, item)
            item_type = "directory" if os.path.isdir(item_path) else "file"
            
            files.append({
                "name": item,
                "type": item_type
            })
        
        logger.info(f"Retornando {len(files)} archivos/directorios")
        return {"files": files}
    except Exception as e:
        logger.error(f"Error al listar archivos: {str(e)}")
        return {"error": f"Error al listar archivos: {str(e)}"}


@app.post("/set-root")
async def set_root_dir(request: SetRootRequest):
    """Establece un nuevo directorio raíz."""
    try:
        logger.info(f"Solicitud para cambiar directorio raíz a: {request.new_root}")
        
        # Verificar que el directorio existe
        if not os.path.exists(request.new_root):
            logger.warning(f"Directorio solicitado no existe: {request.new_root}")
            return {"error": f"El directorio {request.new_root} no existe"}
        
        # Verificar que es un directorio
        if not os.path.isdir(request.new_root):
            logger.warning(f"Ruta no es un directorio: {request.new_root}")
            return {"error": f"{request.new_root} no es un directorio"}
        
        # Actualizar la variable de entorno
        prev_root = os.environ.get("WRITE_ROOT", os.getcwd())
        os.environ["WRITE_ROOT"] = request.new_root
        
        logger.info(f"Directorio raíz cambiado de '{prev_root}' a '{request.new_root}'")
        return {"success": True, "message": f"Directorio raíz cambiado a: {request.new_root}"}
    except Exception as e:
        logger.error(f"Error al cambiar directorio raíz: {str(e)}")
        return {"error": f"Error al cambiar directorio raíz: {str(e)}"}

@app.get("/models")
async def list_models():
    """Endpoint para listar modelos disponibles"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="Orquestador no inicializado")

        models = []
        # Únicamente devolvemos la configuración activa de Blackbox
        config = orchestrator.models_config.get("models", {}).get("blackbox", {})
        if config.get("enabled", False):
            models.append({
                "name": "blackbox",
                "model": config.get("model", "blackbox"),
                "enabled": True
            })

        return {
            "models": models,
            "default_model": orchestrator.models_config.get("models", {}).get("blackbox", {}).get("model", "blackbox"),
            "available_models": orchestrator.models_config.get("available_models", [])
        }

    except Exception as e:
        logger.error(f"Error al listar modelos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/models/switch")
async def switch_model(request: SwitchModelRequest):
    """Cambiar el modelo activo de Blackbox manteniendo la misma API key"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="Orquestador no inicializado")

        # Validación básica: debe parecer un identificador de Blackbox
        if "/" not in request.model:
            raise HTTPException(status_code=400, detail="Identificador de modelo inválido")

        # Actualizar en memoria y persistir en archivo
        orchestrator.models_config.setdefault("models", {}).setdefault("blackbox", {})["model"] = request.model
        # Asegurar base_url por si falta
        orchestrator.models_config["models"]["blackbox"].setdefault(
            "base_url", "https://api.blackbox.ai/chat/completions"
        )
        # Mantener enabled/api_key existentes
        orchestrator._save_config()

        logger.info(f"Modelo por defecto actualizado a: {request.model}")
        return {"status": "success", "default_model": request.model}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al cambiar de modelo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.post("/files/write")
async def write_file(req: WriteFileRequest):
    """Crea o sobrescribe un archivo de texto dentro del directorio permitido.

    Por seguridad, se restringe la escritura a `WRITE_ROOT` (por defecto `/app`).
    """
    try:
        base_dir = Path(os.getenv("WRITE_ROOT", ".")).resolve()
        dest = (base_dir / req.path).expanduser().resolve()
        # Evitar path traversal: el destino debe estar dentro de base_dir
        # if base_dir not in target_path.parents and target_path != base_dir:
            # Navegación libre permitida

        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not req.overwrite:
            raise HTTPException(status_code=409, detail="El archivo ya existe. Use overwrite=true para sobrescribir")

        with open(dest, 'w', encoding='utf-8') as f:
            f.write(req.content)

        return {"status": "success", "path": str(dest), "written": len(req.content)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al escribir archivo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo escribir el archivo: {str(e)}")

@app.post("/patch/apply")
async def apply_patch(req: ApplyPatchRequest):
    """Aplica un parche unified diff sobre un directorio raiz permitido.

    Seguridad: restringido a WRITE_ROOT (por defecto /app).
    """
    try:
        base_dir = Path(os.getenv("WRITE_ROOT", ".")).resolve()
        root = (base_dir / (req.root or ".")).resolve()
        # if base_dir not in target_path.parents and target_path != base_dir:
            # Navegación libre permitida
        result = apply_unified_diff(req.patch, root)
        return {"status": "success", **result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error aplicando parche: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo aplicar el parche: {str(e)}")

@app.post("/files/list")
async def list_directory(req: ListDirectoryRequest):
    """Lista archivos y directorios en una ruta específica"""
    try:
        base_dir = Path(os.getenv("WRITE_ROOT", ".")).resolve()
        target_path = (base_dir / req.path).resolve()
        
        # Permitir navegación libre, solo verificar que la ruta existe
        # (Removido el check de directorio permitido para navegación libre)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directorio no encontrado")
        
        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="La ruta no es un directorio")
        
        items = []
        for item in target_path.iterdir():
            if not req.show_hidden and item.name.startswith('.'):
                continue
                
            relative_path = item.relative_to(base_dir)
            items.append({
                "name": item.name,
                "path": str(relative_path),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime
            })
        
        # Ordenar: directorios primero, luego archivos
        items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        
        return {
            "status": "success",
            "path": str(target_path.relative_to(base_dir)),
            "items": items
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listando directorio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo listar el directorio: {str(e)}")

@app.post("/files/read")
async def read_file(req: ReadFileRequest):
    """Lee el contenido de un archivo"""
    try:
        base_dir = Path(os.getenv("WRITE_ROOT", ".")).resolve()
        file_path = (base_dir / req.path).resolve()
        
        # if base_dir not in target_path.parents and target_path != base_dir:
            # Navegación libre permitida
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Archivo no encontrado")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="La ruta no es un archivo")
        
        # Verificar que sea un archivo de texto
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Intentar con otras codificaciones
            try:
                with open(file_path, 'r', encoding='latin1') as f:
                    content = f.read()
            except:
                raise HTTPException(status_code=400, detail="El archivo no es un archivo de texto válido")
        
        return {
            "status": "success",
            "path": str(file_path.relative_to(base_dir)),
            "content": content,
            "size": len(content)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error leyendo archivo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo leer el archivo: {str(e)}")

@app.post("/files/mkdir")
async def create_directory(req: CreateDirectoryRequest):
    """Crea un directorio"""
    try:
        base_dir = Path(os.getenv("WRITE_ROOT", ".")).resolve()
        dir_path = (base_dir / req.path).resolve()
        
        # if base_dir not in target_path.parents and target_path != base_dir:
            # Navegación libre permitida
        
        dir_path.mkdir(parents=True, exist_ok=True)
        
        return {
            "status": "success",
            "path": str(dir_path.relative_to(base_dir)),
            "message": "Directorio creado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando directorio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo crear el directorio: {str(e)}")

@app.post("/files/delete")
async def delete_file(req: DeleteFileRequest):
    """Elimina un archivo o directorio"""
    try:
        base_dir = Path(os.getenv("WRITE_ROOT", ".")).resolve()
        target_path = (base_dir / req.path).resolve()
        
        # Permitir navegación libre (removido check de directorio permitido)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Archivo o directorio no encontrado")
        
        if target_path.is_dir():
            shutil.rmtree(target_path)
            message = "Directorio eliminado exitosamente"
        else:
            target_path.unlink()
            message = "Archivo eliminado exitosamente"
        
        return {
            "status": "success",
            "path": str(target_path.relative_to(base_dir)),
            "message": message
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando archivo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo eliminar: {str(e)}")

@app.post("/files/analyze-directory")
async def analyze_directory(req: AnalyzeDirectoryRequest):
    """Analiza un directorio completo y genera contexto para IA"""
    try:
        base_dir = Path(os.getenv("WRITE_ROOT", ".")).resolve()
        target_path = (base_dir / req.path).resolve()
        
        # Permitir navegación libre (removido check de directorio permitido)
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directorio no encontrado")
        
        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="La ruta no es un directorio")
        
        analysis = {
            "directory": str(target_path.relative_to(base_dir)),
            "structure": {},
            "files": [],
            "summary": {
                "total_files": 0,
                "total_dirs": 0,
                "file_types": {},
                "total_size": 0
            }
        }
        
        # Función recursiva para construir estructura
        def build_structure(path, max_depth=3, current_depth=0):
            if current_depth >= max_depth:
                return "..."
            
            structure = {}
            try:
                for item in path.iterdir():
                    if item.name.startswith('.'):
                        continue
                    
                    if item.is_dir():
                        analysis["summary"]["total_dirs"] += 1
                        structure[item.name + "/"] = build_structure(item, max_depth, current_depth + 1)
                    else:
                        analysis["summary"]["total_files"] += 1
                        size = item.stat().st_size
                        analysis["summary"]["total_size"] += size
                        
                        # Contar tipos de archivo
                        ext = item.suffix.lower()
                        analysis["summary"]["file_types"][ext] = analysis["summary"]["file_types"].get(ext, 0) + 1
                        
                        structure[item.name] = f"{size} bytes"
                        
                        # Agregar a lista de archivos si hay espacio
                        if len(analysis["files"]) < req.max_files:
                            file_info = {
                                "name": item.name,
                                "path": str(item.relative_to(base_dir)),
                                "size": size,
                                "extension": ext,
                                "content": None
                            }
                            
                            # Incluir contenido si se solicita y es archivo de texto pequeño
                            if (req.include_content and size < 50000 and 
                                ext in ['.py', '.js', '.html', '.css', '.md', '.txt', '.json', '.yaml', '.yml']):
                                try:
                                    with open(item, 'r', encoding='utf-8') as f:
                                        file_info["content"] = f.read()
                                except:
                                    file_info["content"] = "[No se pudo leer el contenido]"
                            
                            analysis["files"].append(file_info)
                        
            except PermissionError:
                return "[Sin permisos]"
            
            return structure
        
        analysis["structure"] = build_structure(target_path)
        
        # Formatear tamaño total
        def format_size(bytes):
            for unit in ['B', 'KB', 'MB', 'GB']:
                if bytes < 1024:
                    return f"{bytes:.1f} {unit}"
                bytes /= 1024
            return f"{bytes:.1f} TB"
        
        analysis["summary"]["total_size_formatted"] = format_size(analysis["summary"]["total_size"])
        
        return {
            "status": "success",
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analizando directorio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo analizar el directorio: {str(e)}")

@app.post("/files/change-root")
async def change_root(req: ChangeRootRequest):
    """Cambia el directorio raíz de trabajo"""
    try:
        new_root = Path(req.new_root).resolve()
        
        if not new_root.exists():
            raise HTTPException(status_code=404, detail="El directorio no existe")
        
        if not new_root.is_dir():
            raise HTTPException(status_code=400, detail="La ruta no es un directorio")
        
        # Verificar permisos básicos
        try:
            list(new_root.iterdir())
        except PermissionError:
            raise HTTPException(status_code=403, detail="Sin permisos para acceder al directorio")
        
        # Actualizar variable de entorno para esta sesión
        os.environ["WRITE_ROOT"] = str(new_root)
        
        return {
            "status": "success",
            "message": f"Directorio raíz cambiado a: {new_root}",
            "new_root": str(new_root)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando directorio raíz: {str(e)}")
        raise HTTPException(status_code=500, detail=f"No se pudo cambiar el directorio raíz: {str(e)}")

# ===============================
# FUNCTION CALLING / TOOLS DEMO
# ===============================

# Simulador de base de datos de productos
PRODUCTS_DB = [
    {
        "id": "p001",
        "name": "Smartphone Galaxy S24",
        "category": "Electronics",
        "price": 899.99,
        "description": "Latest flagship smartphone with advanced camera",
        "inventory": 25
    },
    {
        "id": "p002", 
        "name": "Wireless Headphones Pro",
        "category": "Audio",
        "price": 299.99,
        "description": "Noise-canceling wireless headphones",
        "inventory": 12
    },
    {
        "id": "p003",
        "name": "Gaming Laptop X1",
        "category": "Computers",
        "price": 1599.99,
        "description": "High-performance gaming laptop",
        "inventory": 8
    }
]

def search_products(query: str = "", category: str = "") -> list:
    """Buscar productos en el catálogo"""
    results = []
    for product in PRODUCTS_DB:
        match = False
        if not query and not category:
            match = True
        elif query and query.lower() in product["name"].lower():
            match = True
        elif category and category.lower() == product["category"].lower():
            match = True
            
        if match:
            results.append({
                "id": product["id"],
                "name": product["name"],
                "category": product["category"],
                "price": product["price"]
            })
    return results

def get_product_details(product_id: str) -> dict:
    """Obtener detalles completos de un producto específico"""
    for product in PRODUCTS_DB:
        if product["id"] == product_id:
            return product
    return {"error": "Product not found"}

def check_inventory(product_id: str) -> dict:
    """Verificar niveles de inventario para un producto"""
    for product in PRODUCTS_DB:
        if product["id"] == product_id:
            return {
                "product_id": product_id,
                "product_name": product["name"],
                "inventory_count": product["inventory"],
                "status": "in_stock" if product["inventory"] > 0 else "out_of_stock"
            }
    return {"error": "Product not found"}

# Definición de tools para function calling
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search for products in the catalog by name or category",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term to match product names"
                    },
                    "category": {
                        "type": "string", 
                        "description": "Product category to filter by"
                    }
                }
            }
        }
    },
    {
        "type": "function", 
        "function": {
            "name": "get_product_details",
            "description": "Get detailed information about a specific product",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The unique product ID"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_inventory", 
            "description": "Check current inventory levels for a product",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "The unique product ID"
                    }
                },
                "required": ["product_id"]
            }
        }
    }
]

def execute_function_call(function_name: str, arguments: dict) -> dict:
    """Ejecutar llamadas de función basadas en el nombre y argumentos"""
    try:
        if function_name == "search_products":
            return search_products(
                query=arguments.get("query", ""),
                category=arguments.get("category", "")
            )
        elif function_name == "get_product_details":
            return get_product_details(arguments["product_id"])
        elif function_name == "check_inventory":
            return check_inventory(arguments["product_id"])
        else:
            return {"error": f"Unknown function: {function_name}"}
    except Exception as e:
        return {"error": f"Function execution failed: {str(e)}"}

class ToolChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

@app.post("/chat-with-tools")
async def chat_with_tools(request: ToolChatRequest):
    """Chat endpoint con soporte para function calling"""
    try:
        if not orchestrator:
            raise HTTPException(status_code=500, detail="Orquestador no inicializado")
        
        # Generar respuesta con tools disponibles
        response = orchestrator.generate_response(
            request.message,
            tools=AVAILABLE_TOOLS,
            max_tokens=1500
        )
        
        # Si la respuesta es un diccionario, contiene tool calls
        if isinstance(response, dict) and "tool_calls" in response:
            tool_responses = []
            
            # Ejecutar cada tool call
            for tool_call in response["tool_calls"]:
                if tool_call.get("type") == "function":
                    func = tool_call.get("function", {})
                    func_name = func.get("name")
                    func_args = json.loads(func.get("arguments", "{}"))
                    
                    # Ejecutar la función
                    result = execute_function_call(func_name, func_args)
                    tool_responses.append({
                        "tool_call_id": tool_call.get("id"),
                        "function_name": func_name,
                        "arguments": func_args,
                        "result": result
                    })
            
            # Generar respuesta final con los resultados de las herramientas
            follow_up_messages = [
                {"role": "user", "content": request.message},
                {"role": "assistant", "content": response.get("content", ""), "tool_calls": response["tool_calls"]}
            ]
            
            # Agregar resultados de tools como mensajes del sistema
            for tool_resp in tool_responses:
                follow_up_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_resp["tool_call_id"],
                    "content": json.dumps(tool_resp["result"])
                })
            
            # Solicitar respuesta final
            final_response = orchestrator.generate_response(
                "",  # Sin prompt adicional
                messages=follow_up_messages,
                max_tokens=1500
            )
            
            return {
                "response": final_response if isinstance(final_response, str) else final_response.get("content", ""),
                "tool_calls_executed": tool_responses,
                "model_used": "blackbox_with_tools",
                "status": "success"
            }
        
        # Respuesta normal sin tool calls
        return {
            "response": response,
            "model_used": "blackbox",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error en chat con tools: {str(e)}")
        return {
            "response": f"Error: {str(e)}",
            "status": "error"
        }

async def analyze_directory_background(path: str = ".") -> dict:
    """Analiza un directorio en segundo plano y devuelve información estructurada."""
    try:
        base_dir = os.environ.get("WRITE_ROOT", os.getcwd())
        target_path = os.path.normpath(os.path.join(base_dir, path))
        
        # Verificar que la ruta existe y está dentro del directorio permitido
        if not os.path.exists(target_path):
            return {"error": f"La ruta {path} no existe"}
            
        if not os.path.abspath(target_path).startswith(os.path.abspath(base_dir)):
            return {"error": "No se permite acceder a rutas fuera del directorio base"}
        
        if not os.path.isdir(target_path):
            return {"error": f"{path} no es un directorio"}
        
        # Recopilar información del directorio
        analysis = {
            "path": path,
            "absolute_path": target_path,
            "files": [],
            "directories": [],
            "total_files": 0,
            "total_directories": 0,
            "total_size": 0
        }
        
        # Analizar contenido
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                analysis["files"].append({
                    "name": item,
                    "size": size,
                    "type": "file"
                })
                analysis["total_files"] += 1
                analysis["total_size"] += size
            elif os.path.isdir(item_path):
                analysis["directories"].append({
                    "name": item,
                    "type": "directory"
                })
                analysis["total_directories"] += 1
        
        return analysis
    except Exception as e:
        return {"error": f"Error al analizar directorio: {str(e)}"}

@app.get("/tools")
async def list_available_tools():
    """Endpoint para listar herramientas disponibles"""
    return {
        "tools": AVAILABLE_TOOLS,
        "description": "Available function calling tools for the AI assistant"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8006))
    uvicorn.run(app, host="0.0.0.0", port=port)
