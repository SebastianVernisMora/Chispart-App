"""
Tests para el módulo ai_client
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from blackbox_hybrid_tool.core.ai_client import (
    AIOrchestrator,
    BlackboxClient,
    AIModelFactory,
)


class TestBlackboxClient:
    """Tests para la clase BlackboxClient"""

    def setup_method(self):
        """Configuración inicial para cada test"""
        self.api_key = "test_api_key"
        self.model_config = {"model": "blackboxai/openai/o1"}
        self.client = BlackboxClient(self.api_key, self.model_config)

    def test_initialization(self):
        """Test de inicialización del cliente"""
        assert self.client is not None
        assert self.client.api_key == "test_api_key"
        assert self.client.model_config == {"model": "blackboxai/openai/o1"}

    @patch('requests.post')
    def test_generate_response_success(self, mock_post):
        """Test generación exitosa de respuesta"""
        # Configurar mock
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test response'}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # Ejecutar consulta
        result = self.client.generate_response("Test query")

        # Verificar resultado
        assert result == "Test response"
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_generate_response_failure(self, mock_post):
        """Test consulta fallida"""
        # Configurar mock para error de requests
        import requests
        mock_post.side_effect = requests.RequestException("Connection error")

        # Ejecutar consulta
        result = self.client.generate_response("Test query")

        # Verificar que retorna mensaje de error
        assert "Error en la API de Blackbox" in result


## Se elimina TestGeminiClient ya que la lógica de Gemini fue retirada


class TestAIModelFactory:
    """Tests para la clase AIModelFactory"""

    def test_create_blackbox_client(self):
        """Test creación de cliente Blackbox"""
        client = AIModelFactory.create_client(
            "blackbox", 
            "test_key", 
            {"model": "blackbox"}
        )
        assert isinstance(client, BlackboxClient)

    def test_create_client_ignores_type_and_returns_blackbox(self):
        """Factory siempre retorna BlackboxClient, incluso si se pide 'gemini'"""
        client = AIModelFactory.create_client(
            "gemini",
            "test_key",
            {"model": "gemini-pro"},
        )
        assert isinstance(client, BlackboxClient)

    def test_invalid_model_type_returns_blackbox(self):
        """Incluso tipo inválido devuelve BlackboxClient (compatibilidad)"""
        client = AIModelFactory.create_client(
            "invalid_model",
            "test_key",
            {"model": "test"},
        )
        assert isinstance(client, BlackboxClient)


class TestAIOrchestrator:
    """Tests para la clase AIOrchestrator"""

    def setup_method(self):
        """Configuración inicial para cada test"""
        # Mock del archivo de configuración
        self.mock_config = {
            "default_model": "auto",
            "models": {
                "blackbox": {
                    "api_key": "test_blackbox_key",
                    "model": "blackboxai/openai/o1",
                    "enabled": True,
                }
            },
        }

    @patch('builtins.open', mock_open(read_data='{"default_model": "auto", "models": {"blackbox": {"api_key": "test_key", "model": "blackboxai/openai/o1", "enabled": true}}}'))
    @patch('json.load')
    def test_load_config_success(self, mock_json_load):
        """Test carga exitosa de configuración"""
        mock_json_load.return_value = self.mock_config
        
        orchestrator = AIOrchestrator()
        # orquestador puede ajustar el modelo al mejor disponible; verificamos claves principales
        assert orchestrator.models_config.get("models", {}).get("blackbox") is not None

    def test_load_config_file_not_found(self):
        """Test configuración por defecto cuando no existe archivo"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            orchestrator = AIOrchestrator()
            assert "default_model" in orchestrator.models_config
            assert "models" in orchestrator.models_config

    @patch('builtins.open', mock_open())
    @patch('json.load')
    def test_get_client_success(self, mock_json_load):
        """Test obtención exitosa de cliente"""
        mock_json_load.return_value = self.mock_config
        
        orchestrator = AIOrchestrator()
        client = orchestrator.get_client("blackbox")
        assert isinstance(client, BlackboxClient)

    @patch('builtins.open', mock_open())
    @patch('json.load')
    def test_get_client_disabled_model(self, mock_json_load):
        """Si blackbox está deshabilitado, debe fallar"""
        disabled_cfg = {
            "default_model": "auto",
            "models": {
                "blackbox": {
                    "api_key": "test_blackbox_key",
                    "model": "blackboxai/openai/o1",
                    "enabled": False,
                }
            },
        }
        mock_json_load.return_value = disabled_cfg

        orchestrator = AIOrchestrator()
        with pytest.raises(ValueError, match="no está habilitado"):
            orchestrator.get_client("blackbox")

    @patch('builtins.open', mock_open())
    @patch('json.load')
    def test_switch_model(self, mock_json_load):
        """Test cambio de modelo por defecto"""
        mock_json_load.return_value = self.mock_config
        
        with patch('builtins.open', mock_open()) as mock_file:
            with patch('json.dump') as mock_json_dump:
                orchestrator = AIOrchestrator()
                # Solo 'blackbox' existe; cambiar a 'blackbox' es válido
                orchestrator.switch_model("blackbox")
                assert orchestrator.models_config["default_model"] == "blackbox"
                mock_json_dump.assert_called_once()
