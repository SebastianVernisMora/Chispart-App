# ✨ Chispart AI


Plataforma de IA multiagente para creación de contenido, con interfaz glassmorphism y flujos de trabajo colaborativos, potenciada por Blackbox AI.

## 🚀 Características

- **API REST con FastAPI**: Interfaz moderna y rápida para integración
- **Soporte Blackbox AI**: Selección dinámica del modelo vía identificador de Blackbox (p. ej. `blackboxai/openai/o1`)
- **Contenedor Docker**: Despliegue simplificado con Docker y Docker Compose
- **Configuración flexible**: Archivo JSON para configuración y lista de modelos disponibles
- **Importación desde CSV**: Carga opcional de catálogo de modelos disponibles
- **Logging y health checks**: Monitoreo básico del servicio
- **CORS habilitado**: Soporte para aplicaciones web
- **Documentación automática**: API docs con Swagger UI en `/docs`

## 📋 Requisitos

- Docker y Docker Compose (recomendado)
- Python 3.9+ (para desarrollo local)

## 🛠️ Instalación y Despliegue

### Usando Docker Compose (Recomendado)

1. **Navega al directorio del proyecto**:
   ```bash
   cd blackbox-hybrid-tool
   ```

2. **Configura las variables de entorno**:
   Crea un archivo `.env` con al menos la clave de Blackbox y, opcionalmente, rutas de configuración:
   ```env
   BLACKBOX_API_KEY=tu_clave_blackbox
   # Opcional: ruta al archivo de configuración JSON
   CONFIG_FILE=blackbox_hybrid_tool/config/models.json
   # Opcional: CSV con catálogo de modelos (ver sección Importación CSV)
   BLACKBOX_MODELS_CSV=/ruta/a/modelos_blackbox.csv
   ```

3. **Construye y ejecuta el contenedor**:
   ```bash
docker-compose up --build
   ```

4. **Verifica que la aplicación esté ejecutándose**:
   ```bash
   curl http://localhost:8000/health
   ```

### Desarrollo Local

1. **Instala las dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configura las variables de entorno** (igual que arriba)

3. **Ejecuta la aplicación**:
   ```bash
   python main.py
   ```

## 📖 Manual de Uso

### 🚀 Inicio Rápido

Después de la instalación, la API estará disponible en `http://localhost:8000`.

#### Verificar estado del servicio:
```bash
curl http://localhost:8000/health
```

#### Obtener información básica:
```bash
curl http://localhost:8000/
```

### 📋 Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/` | Información básica de la API |
| `GET` | `/health` | Verificación de salud del servicio |
| `GET` | `/models` | Lista de modelos disponibles |
| `POST` | `/models/switch` | Actualiza el modelo por defecto de Blackbox |
| `POST` | `/chat` | Generar respuesta de IA |
| `POST` | `/files/write` | Crear/escribir un archivo de texto |
| `POST` | `/patch/apply` | Aplicar un parche unified diff |
| `GET` | `/docs` | Documentación interactiva (Swagger UI) |
| `GET` | `/redoc` | Documentación alternativa (ReDoc) |
| `GET` | `/playground` | Interfaz web mínima para chatear |

### 💬 Uso del Endpoint de Chat

#### Parámetros de solicitud:

```json
{
  "prompt": "Tu mensaje aquí",
  "model_type": "blackboxai/openai/o1",  // opcional: identificador completo de Blackbox
  "max_tokens": 2048,                    // opcional: máximo de tokens en respuesta
  "temperature": 0.7                     // opcional: creatividad (0.0-1.0)
}
```

#### Ejemplos de uso:

```bash
# 1. Chat simple con modelo por defecto (auto)
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "¿Cuál es la capital de Francia?"
     }'

# 2. Chat forzando un modelo específico de Blackbox por identificador
curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "Explica la teoría de la relatividad",
       "model_type": "blackboxai/openai/o1",
       "max_tokens": 500,
       "temperature": 0.3
     }'
```

#### Respuesta de ejemplo:

```json
{
  "response": "La capital de Francia es París, una ciudad conocida por su historia, cultura y monumentos icónicos como la Torre Eiffel.",
  "model_used": "blackboxai/openai/o1",
  "status": "success"
}
```

### 🤖 Gestión de Modelos

#### Listar modelos disponibles:
```bash
curl http://localhost:8000/models
```

#### Respuesta de ejemplo:
```json
{
  "models": [
    {
      "name": "blackbox",
      "model": "blackboxai/openai/o1",  
      "enabled": true
    }
  ],
  "default_model": "auto",
  "available_models": [
    {"model": "blackboxai/openai/o1", "context": "128k", "input_cost": "5.00", "output_cost": "15.00"}
  ]
}

#### Cambiar el modelo por defecto
```bash
curl -X POST "http://localhost:8000/models/switch" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "blackboxai/anthropic/claude-3.7-sonnet"
     }'
```
### 🔧 Casos de Uso Avanzados

#### Integración con aplicaciones web:
```javascript
// Ejemplo con JavaScript/Fetch
async function chatWithAI(prompt, model) {
  const response = await fetch('http://localhost:8000/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      prompt: prompt,
      model_type: model,
      max_tokens: 1000,
      temperature: 0.7
    })
  });

  const data = await response.json();
  return data.response;
}
```

#### Uso con Python:
```python
import requests

def chat_with_ai(prompt, model=None):
    url = 'http://localhost:8000/chat'
    data = {
        'prompt': prompt,
        'model_type': model,
        'max_tokens': 1000,
        'temperature': 0.7
    }

    response = requests.post(url, json=data)
    return response.json()['response']

# Ejemplo de uso
respuesta = chat_with_ai("¿Qué es machine learning?")
print(respuesta)
```

#### Uso con cURL en scripts:
```bash
#!/bin/bash
# Script para consultar la API

PROMPT="Explica qué es Docker"
MODEL="blackboxai/openai/o1"

curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d "{\"prompt\": \"$PROMPT\", \"model_type\": \"$MODEL\"}" \
     | jq -r '.response'
```

### 📊 Monitoreo y Health Checks

#### Health check básico:
```bash
curl http://localhost:8000/health
# Respuesta: {"status": "healthy"}
```

#### Monitoreo continuo con script:
```bash
#!/bin/bash
# health_monitor.sh

while true; do
    if curl -s http://localhost:8000/health > /dev/null; then
        echo "$(date): Servicio OK"
    else
        echo "$(date): ERROR - Servicio no disponible"
        # Aquí puedes agregar notificaciones o acciones de recuperación
    fi
    sleep 60  # Verificar cada minuto
done
```

#### Ver logs en tiempo real:
```bash
# Logs del contenedor
docker-compose logs -f blackbox-hybrid-tool

# Logs de la aplicación
docker-compose logs -f | grep "blackbox"
```

## ⚙️ Configuración

### Archivo de configuración de modelos

El archivo `blackbox_hybrid_tool/config/models.json` contiene la configuración del modelo Blackbox y, opcionalmente, un catálogo de modelos disponibles. **La API key se debe configurar en la variable de entorno `BLACKBOX_API_KEY`**:

```json
{
  "default_model": "auto",
  "models": {
    "blackbox": {
      "enabled": true,
      "model": "blackboxai/openai/o1",

      "base_url": "https://api.blackbox.ai/chat/completions"
    }
  },
  "available_models": [
    {"model": "blackboxai/openai/o1", "context": "128k", "input_cost": "5.00", "output_cost": "15.00"}
  ]
}
```

### Importación de modelos desde CSV (opcional)

Si defines la variable de entorno `BLACKBOX_MODELS_CSV` apuntando a un archivo CSV, la app intentará importar un catálogo de modelos al iniciar. El CSV debe contener las columnas:

- "Modelo"
- "Contexto"
- "Costo de Entrada ($/M tokens)"
- "Costo de Salida ($/M tokens)"

Ejemplo de uso:
```env
BLACKBOX_MODELS_CSV=/ruta/a/modelos_blackbox.csv
```
Tras el arranque, los modelos importados se verán en `GET /models` bajo `available_models`.

## 🖥️ CLI (opcional)

La herramienta incluye una CLI simple para generar tests, consultar la IA y revisar configuración.

Instalación local (opcional) para habilitar el comando global:

```bash
pip install -e .

# Comandos disponibles (alias):
blackbox-tool --help
blackbox-hybrid-tool --help
blackbox_hybrid_tool --help
```

Modo depuración:

```bash
# Ver payloads y respuesta cruda de la API (con claves enmascaradas)
blackbox-tool ai-query "Quiubo" --debug
```

Variables de entorno útiles para la CLI/API:

```bash
export BLACKBOX_API_KEY='tu_api_key'
export CONFIG_FILE=blackbox_hybrid_tool/config/models.json
# Opcionales para búsqueda web
export SERPAPI_KEY=tu_serpapi_key   # o
export TAVILY_API_KEY=tu_tavily_key
```

Ejemplos rápidos:

```bash
# Mostrar ayuda general
blackbox-tool -h

# Consultar IA con el modelo por defecto
blackbox-tool ai-query "Explica TDD brevemente"

# Consultar forzando un identificador de Blackbox
blackbox-tool ai-query "Resume SOLID" -m blackboxai/openai/o1

# Listar modelos y ver el actual
blackbox-tool list-models

# Ver configuración cargada
blackbox-tool config

### Despliegue Remoto (SSH)

La CLI incluye utilidades SSH para sincronizar y desplegar en un servidor remoto, con o sin Docker. Consulta `docs/deployment.md` para detalles.

Ejemplo rápido (Docker Compose):

```bash
# Sincroniza el proyecto al servidor
python -m blackbox_hybrid_tool.cli.main ssh-sync --host your.host --user ubuntu --key ~/.ssh/id_rsa --recursive . /opt/bbtool

# Levanta el servicio con Docker Compose
python -m blackbox_hybrid_tool.cli.main ssh-exec --host your.host --user ubuntu --key ~/.ssh/id_rsa "cd /opt/bbtool && docker compose up -d --build"

# O usa el helper de un paso
python -m blackbox_hybrid_tool.cli.main deploy-remote --host your.host --user ubuntu --key ~/.ssh/id_rsa --dir /opt/bbtool --compose
```

Comandos disponibles:
- `ssh-exec`: ejecuta comando remoto
- `ssh-sync`: copia archivos (scp)
- `deploy-remote`: despliega con compose/docker o venv (`--no-docker`)

# Cambiar el modelo por defecto de la CLI
# Opción 1: establecer el nombre lógico (compatibilidad: 'blackbox')
blackbox-tool switch-model blackbox

# Opción 2: establecer un identificador de Blackbox por defecto (recomendado)
blackbox-tool switch-model blackboxai/anthropic/claude-3.7-sonnet

### CLI interactiva (REPL)

```bash
# Inicia una sesión interactiva con contexto
blackbox-tool repl

# Con modelo específico desde el inicio
blackbox-tool repl -m blackboxai/openai/o1

# Comandos dentro del REPL:
# /model <id>        → cambia el modelo de la sesión
# /reset             → limpia el contexto
# /save              → guarda el estado actual (si hay sesión)
# /session <nombre>  → cambia/carga otra sesión persistente
# /transcript <ruta> → activa/actualiza el archivo de log
# /exit              → termina la sesión
# /help              → ayuda rápida

# Persistencia automática por nombre de sesión
blackbox-tool repl -s mi-sesion

# Con transcript de texto (se va anexando)
blackbox-tool repl -s demo -t ~/transcripts/demo.txt
```

## 🌐 Playground Web

Visita `http://localhost:8000/playground` para una interfaz mínima que consume el endpoint `/chat`. Permite fijar el identificador del modelo, ajustar `max_tokens` y `temperature`.

## ✍️ Crear/Escribir Archivos

### Vía API

Endpoint: `POST /files/write`

Body JSON:

```json
{
  "path": "docs/nota.txt",
  "content": "Hola mundo",
  "overwrite": false
}
```

Notas:
- Limita la escritura a `WRITE_ROOT` (por defecto `/app`). Puedes cambiarlo con `WRITE_ROOT=/app` en variables de entorno del contenedor.
- Devuelve `409` si el archivo existe y `overwrite=false`.

### Vía CLI

```bash
# Contenido inline
blackbox-tool write-file docs/nota.txt -c "Hola mundo"

# Leer desde stdin
echo "línea 1" | blackbox-tool write-file docs/nota.txt --stdin --overwrite

# Usar editor ($EDITOR, nano o vi)
blackbox-tool write-file docs/nota.txt --editor

### Aplicar parches (Unified Diff)

```bash
# Desde archivo .patch/.diff
blackbox-tool apply-patch -f cambios.patch --root .

# Leer parche desde STDIN (pipe)
git diff > cambios.patch
cat cambios.patch | blackbox-tool apply-patch --stdin --root .

# Simular sin aplicar
blackbox-tool apply-patch -f cambios.patch --dry-run
```

Vía API:

```bash
curl -X POST http://localhost:8000/patch/apply \
  -H 'Content-Type: application/json' \
  -d '{"patch": "<contenido unified diff>", "root": "."}'
```
```

La CLI crea directorios intermedios si no existen y no sobrescribe a menos que uses `--overwrite`.

## 🤖 Auto‑análisis y Auto‑evolución (local)

Herramientas para que la CLI se analice, se empaquete y se actualice de forma segura:

```bash
# Generar y embeber un snapshot comprimido del repo en el código
blackbox-tool self-snapshot

# Extraer el snapshot embebido a un directorio
blackbox-tool self-extract -o .self_extract

# Analizar dependencias y estructura (árbol actual o snapshot)
blackbox-tool self-analyze --from current
blackbox-tool self-analyze --from embedded

# Ejecutar pruebas del proyecto actual
blackbox-tool self-test

# Aplicar un parche en una copia, correr tests y, si pasan, sustituir el árbol actual (con backup)
git diff > cambios.patch
blackbox-tool self-apply-patch -f cambios.patch
```

Notas:
- Los snapshots embebidos se guardan en `blackbox_hybrid_tool/_embedded_payload.py` (ignorado por git) y se actualizan en el arranque si `AUTO_SNAPSHOT=true`.
- Los backups se guardan en `.self_backup/backup-<timestamp>.tar.gz`.
- El reemplazo sólo ocurre si las pruebas pasan en la copia modificada.

## 🧠 Desarrollo asistido por IA (ai-dev)

Genera parches unified diff a partir de instrucciones en lenguaje natural. Opcionalmente usa web y aplica los cambios tras pasar pruebas.

```bash
# Generar parche (estrategia automática) y revisar
blackbox-tool ai-dev "Agregar comando 'hello' a la CLI" --out-dir patches

# Permitir búsqueda web (requiere SERPAPI_KEY o TAVILY_API_KEY)
blackbox-tool ai-dev "Soporte para quickstart con ejemplos" --allow-web -e serpapi

# Elegir estrategia/modelo: fast | reasoning | code
blackbox-tool ai-dev "Refactor de ai_client para retrys" -s reasoning

# Forzar un modelo específico
blackbox-tool ai-dev "Crear endpoint /metrics" -m blackboxai/openai/o1

# Generar y aplicar si pruebas pasan
blackbox-tool ai-dev "Actualizar README con sección de seguridad" --apply
```

Notas:
- Estrategia "auto" intenta elegir un modelo de `available_models` acorde (por nombre).
- El parche se guarda en `patches/ai-dev-<timestamp>.patch`.
- Con `--apply` se ejecuta `self-apply-patch` automáticamente.
 - Puedes fijar modelos por estrategia vía variables de entorno:
   - `MODEL_FOR_AUTO`, `MODEL_FOR_FAST`, `MODEL_FOR_REASONING`, `MODEL_FOR_CODE`
   - Ejemplo: `export MODEL_FOR_REASONING=blackboxai/anthropic/claude-3.7-sonnet`

## 🌐 Búsqueda web (opcional)

```bash
# Buscar resultados (requiere SERPAPI_KEY o TAVILY_API_KEY)
blackbox-tool web-search -q "pytest best practices" -e serpapi -n 3

# Descargar una URL y ver el texto procesado
blackbox-tool web-fetch https://docs.pytest.org/
```

## 🔗 Integración con GitHub (Token Personal)

Configura `GH_TOKEN` (o `GITHUB_TOKEN`) en tu entorno para habilitar comandos básicos.

```bash
export GH_TOKEN=ghp_...

# Verificar token/usuario
blackbox-tool gh-status

# Crear un Gist (público o secreto)
blackbox-tool gh-create-gist -f README.md -n README.md -d "Copia del README" --public

# O desde STDIN
echo "hola" | blackbox-tool gh-create-gist --stdin -n hola.txt -d "Ejemplo"
```

Nota: Para crear PRs automáticamente requiere operaciones adicionales (ramas, commits). La estructura del cliente (`utils/github_client.py`) ya está lista para extenderse con el Git Data API en una siguiente iteración.
```
La CLI ahora también permite actualizar el identificador por defecto de Blackbox. Alternativamente, puedes usar el endpoint `POST /models/switch` documentado arriba.

## 📁 Estructura del proyecto

```
blackbox-hybrid-tool/
├── main.py                    # Servidor FastAPI principal
├── blackbox_hybrid_tool/
│   ├── core/
│   │   └── ai_client.py       # Cliente para integración con IA
│   └── config/
│       └── models.json        # Configuración de modelos IA
├── Dockerfile                 # Configuración Docker
├── docker-compose.yml         # Configuración Docker Compose
├── requirements.txt           # Dependencias Python
├── .dockerignore             # Archivos a ignorar en Docker
└── README.md                 # Esta documentación
```

## 🔧 Desarrollo

### Ejecutar en modo desarrollo con hot reload

```bash
docker-compose --profile dev up --build
```

Esto ejecutará la aplicación en el puerto 8001 con recarga automática al cambiar archivos.

### Ejecutar pruebas

```bash
python -m pytest
```

## 📊 Monitoreo y Logs

### Health Check

La aplicación incluye un endpoint de health check que verifica:
- Estado del orquestador de IA
- Conectividad con los modelos configurados
- Estado general del servicio

```bash
curl http://localhost:8000/health
```

### Logs

Los logs se almacenan en el directorio `logs/` dentro del contenedor. Para ver los logs en tiempo real:

```bash
docker-compose logs -f blackbox-hybrid-tool
```

## 🐛 Solución de problemas

### Error de conexión con modelos de IA
- Verifica que las claves API estén configuradas correctamente en el archivo `.env`
- Asegúrate de que el contenedor tenga acceso a internet
- Revisa los logs para mensajes de error específicos

### Error 500 en la API
- Revisa los logs del contenedor para más detalles
- Verifica la configuración de modelos en `models.json`
- Asegúrate de que todos los modelos requeridos estén habilitados

### Problemas con Docker
- Asegúrate de que Docker esté ejecutándose
- Limpia las imágenes y contenedores antiguos: `docker system prune -a`
- Verifica que los puertos 8000/8001 estén disponibles

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Agrega nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🙏 Agradecimientos

- [Blackbox AI](https://blackbox.ai) por la API de IA
- [FastAPI](https://fastapi.tiangolo.com/) por el framework web

---

**Desarrollado con ✨ por Chispart AI Team**
