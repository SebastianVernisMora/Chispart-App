"""
Cliente AI para Blackbox Hybrid Tool
Provee integración únicamente con Blackbox usando una API key única
con selección dinámica del modelo (por ejemplo, cambiar entre
"blackboxai/anthropic/claude-3.7-sonnet" y "blackboxai/openai/o1").
"""

import json
import csv
import os
import requests
from typing import Dict, Any, Optional, Union
from abc import ABC, abstractmethod


class AIClient(ABC):
    """Clase base abstracta para clientes AI"""

    def __init__(self, api_key: str, model_config: Dict[str, Any]):
        self.api_key = api_key
        self.model_config = model_config

    @abstractmethod
    def generate_response(self, prompt: str, **kwargs) -> Union[str, Dict[str, Any]]:
        """Genera respuesta del modelo AI"""
        pass


class BlackboxClient(AIClient):
    """Cliente específico para Blackbox API"""

    def __init__(self, api_key: str, model_config: Dict[str, Any]):
        super().__init__(api_key, model_config)
        # Permitir sobreescribir el endpoint vía configuración
        self.base_url = model_config.get(
            "base_url", "https://api.blackbox.ai/chat/completions"
        )

    def generate_response(self, prompt: str, **kwargs) -> Union[str, Dict[str, Any]]:
        """Genera respuesta usando Blackbox API"""
        debug = bool(kwargs.get("debug", False))
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        # Permitir override del modelo vía kwargs['model']
        model_name = kwargs.get("model") or self.model_config.get("model", "blackboxai/openai/o1")

        # Mensajes (pueden incluir rol system)
        messages = kwargs.get("messages")
        if isinstance(messages, list) and messages:
            msgs = messages
        else:
            msgs = [{"role": "user", "content": prompt}]

        data = {
            "messages": msgs,
            "model": model_name,
            "max_tokens": kwargs.get("max_tokens", 2048),
            "temperature": kwargs.get("temperature", 0.7),
        }

        # Agregar soporte para tools/function calling si se especifican
        tools = kwargs.get("tools")
        if tools:
            data["tools"] = tools
            
        # Permitir forzar tool choice
        tool_choice = kwargs.get("tool_choice")
        if tool_choice:
            data["tool_choice"] = tool_choice

        try:
            if debug:
                def _mask(val: Optional[str]) -> str:
                    if not val:
                        return ""
                    s = str(val)
                    return ("*" * max(0, len(s) - 4)) + s[-4:]

                dbg_headers = dict(headers)
                if "Authorization" in dbg_headers:
                    dbg_headers["Authorization"] = "Bearer " + _mask(self.api_key)
                if "x-api-key" in dbg_headers:
                    dbg_headers["x-api-key"] = _mask(self.api_key)

                print("[DEBUG] Blackbox POST:", self.base_url)
                print("[DEBUG] Headers:", json.dumps(dbg_headers, ensure_ascii=False))
                print("[DEBUG] Payload:", json.dumps(data, ensure_ascii=False))

            response = requests.post(self.base_url, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            if debug:
                try:
                    print("[DEBUG] Status:", response.status_code)
                    print("[DEBUG] Response:", json.dumps(result, ensure_ascii=False))
                except Exception:
                    print("[DEBUG] Raw Response:", response.text)
            # Extraer la respuesta completa del mensaje
            message = result.get("choices", [{}])[0].get("message", {})
            
            # Si hay tool calls, devolverlos junto con el contenido
            if "tool_calls" in message:
                return {
                    "content": message.get("content", ""),
                    "tool_calls": message["tool_calls"]
                }
            
            # Respuesta normal sin tool calls
            return message.get("content", "")

        except requests.RequestException as e:
            # Incluir detalles de respuesta si están disponibles para facilitar el diagnóstico
            try:
                detail = response.text  # type: ignore[name-defined]
            except Exception:
                detail = ""
            if debug and detail:
                print("[DEBUG] Error Detail:", detail)
            return f"Error en la API de Blackbox: {str(e)}{(' | Detalle: ' + detail) if detail else ''}"


class AIModelFactory:
    """Factory para crear instancias de clientes AI"""

    @staticmethod
    def create_client(
        model_type: str, api_key: str, model_config: Dict[str, Any]
    ) -> AIClient:
        """Crea instancia del cliente AI apropiado"""
        # Únicamente Blackbox: devolvemos siempre el cliente de Blackbox
        return BlackboxClient(api_key, model_config)


class AIOrchestrator:
    """Orquestador principal para manejar múltiples modelos AI"""

    def __init__(self, config_file: Optional[str] = None):
        # Determinar ruta de configuración: ENV -> default del paquete
        self.config_file = config_file or os.getenv(
            "CONFIG_FILE", "blackbox_hybrid_tool/config/models.json"
        )
        self.models_config = self._load_config()
        # Configurar el mejor modelo disponible al iniciar
        try:
            self._ensure_best_model()
        except Exception:
            # No bloquear si algo falla al seleccionar mejor modelo
            pass
        self.clients = {}

    def _load_config(self) -> Dict[str, Any]:
        """Carga configuración de modelos desde archivo JSON"""
        try:
            path = self.config_file
            if not os.path.exists(path):
                # Fallback al path del paquete si la ruta configurada no existe
                candidate = "blackbox_hybrid_tool/config/models.json"
                if os.path.exists(candidate):
                    path = candidate
            with open(path, "r") as f:
                cfg = json.load(f)
                # Permitir override por variables de entorno
                bk = cfg.get("models", {}).setdefault("blackbox", {})
                env_key = os.getenv("BLACKBOX_API_KEY")
                if env_key:
                    bk["api_key"] = env_key
                # Si falta api_key, intentar también variable heredada genérica
                if not bk.get("api_key"):
                    generic = os.getenv("API_KEY")
                    if generic:
                        bk["api_key"] = generic
                return cfg
        except FileNotFoundError:
            # Configuración por defecto
            return {
                "default_model": "auto",
                "models": {
                    "blackbox": {
                        "model": "blackboxai/openai/o1",
                        "enabled": True,
                    }
                },
            }

    def _ensure_best_model(self) -> None:
        """Selecciona y fija el mejor modelo disponible en la config de Blackbox.

        - Filtra modelos relacionados con Gemini.
        - Elige por heurística el identificador con mayor preferencia.
        - Actualiza models.blackbox.model si encuentra uno adecuado.
        """
        cfg = self.models_config or {}
        models = cfg.get("models", {})
        bb = models.get("blackbox", {})

        # Lista de candidatos desde available_models y, si existe, el actual
        avail = []
        try:
            avail = [
                m.get("model", "")
                for m in cfg.get("available_models", [])
                if isinstance(m, dict) and m.get("model")
            ]
        except Exception:
            avail = []

        # Agregar el actual si no está
        current = bb.get("model")
        if current and current not in avail:
            avail.append(current)

        # Filtrar gemini por completo
        def _is_gemini(mid: str) -> bool:
            s = str(mid).lower()
            return "gemini" in s or "/google/gemini" in s

        avail = [m for m in avail if m and not _is_gemini(m)]

        if not avail:
            return  # no hay candidatos

        # Preferencias por calidad/caso de uso (sin gemini)
        prefs = [
            # razonamiento de alta calidad
            "o3", "o1", "claude-3.7", "claude-3.5", "deepseek-r1",
            # código/generalistas potentes
            "gpt-4o", "gpt-4.1", "mixtral", "llama-3.1", "llama-3",
            "qwen3", "qwen-3", "qwen2.5",
            # rápidos/compactos
            "flash", "mini", "sonar",
        ]

        def score(model_id: str) -> tuple:
            mid = model_id.lower()
            for i, key in enumerate(prefs):
                if key.lower() in mid:
                    return (0, i)
            generic = ["latest", "pro"]
            for j, k in enumerate(generic):
                if k in mid:
                    return (1, j)
            return (2, len(mid))

        best = sorted(avail, key=score)[0]
        # Fijar modelo en config en memoria
        bb["model"] = best
        models["blackbox"] = bb
        cfg["models"] = models
        self.models_config = cfg

    def get_client(self, model_type: Optional[str] = None) -> AIClient:
        """Obtiene cliente AI para el modelo especificado"""
        # Si no se especifica, usamos la configuración principal "blackbox"
        if model_type is None or model_type == "blackbox" or "/" in str(model_type):
            key = "blackbox"
        else:
            key = model_type

        if key not in self.clients:
            model_config = self.models_config["models"].get("blackbox", {})
            if not model_config.get("enabled", False):
                raise ValueError("Modelo blackbox no está habilitado")

            api_key = model_config.get("api_key", "")
            if not api_key:
                raise ValueError(
                    "API key de Blackbox no configurada. "
                    "Por favor, configura la variable de entorno BLACKBOX_API_KEY"
                )

            self.clients[key] = AIModelFactory.create_client(
                "blackbox", api_key, model_config
            )

        return self.clients[key]

    def generate_response(
        self, prompt: str, model_type: Optional[str] = None, **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """Genera respuesta usando el modelo especificado"""
        # Permite override de modelo pasando un identificador de Blackbox en model_type
        override_model: Optional[str] = None
        if model_type and "/" in model_type:
            override_model = model_type
            client = self.get_client("blackbox")
        else:
            client = self.get_client(model_type)

        if override_model:
            return client.generate_response(prompt, model=override_model, **kwargs)
        return client.generate_response(prompt, **kwargs)

    def switch_model(self, model_type: str):
        """Cambia el modelo por defecto"""
        if model_type not in self.models_config["models"]:
            raise ValueError(f"Modelo {model_type} no existe en configuración")

        self.models_config["default_model"] = model_type
        self._save_config()

    def _save_config(self):
        """Guarda configuración actualizada"""
        with open(self.config_file, "w") as f:
            json.dump(self.models_config, f, indent=2)

    def import_available_models_from_csv(self, csv_path: str) -> int:
        """Importa modelos disponibles desde un CSV y los agrega a available_models en el JSON.

        Espera columnas: Modelo, Contexto, Costo de Entrada ($/M tokens), Costo de Salida ($/M tokens)
        Retorna la cantidad de modelos importados.
        """
        if not os.path.exists(csv_path):
            return 0
        try:
            rows = []
            with open(csv_path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(
                        {
                            "model": r.get("Modelo", "").strip(),
                            "context": r.get("Contexto", "").strip(),
                            "input_cost": str(r.get("Costo de Entrada ($/M tokens)", "")).strip(),
                            "output_cost": str(r.get("Costo de Salida ($/M tokens)", "")).strip(),
                        }
                    )
            if rows:
                self.models_config["available_models"] = rows
                self._save_config()
            return len(rows)
        except Exception:
            return 0
