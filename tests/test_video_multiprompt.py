"""
Tests para verificar la funcionalidad de multiprompt para videos secuenciados.
"""
import unittest
from unittest.mock import patch, MagicMock
import pytest

# Importaciones para pruebas directas de las funciones
from main import create_multiprompt_sequence, update_media_response_multi


class TestVideoMultiprompt(unittest.TestCase):
    """Pruebas para la funcionalidad de secuenciado de prompts para videos."""

    @patch('main.orchestrator')
    def test_create_multiprompt_sequence_success(self, mock_orchestrator):
        """Verifica que se cree correctamente una secuencia de prompts."""
        # Configurar el mock para que devuelva un JSON válido
        mock_orchestrator.generate_response.return_value = """
        ["A car driving through a desert road, wide shot, golden hour", 
         "The car stops at a viewpoint, medium shot, sunset lighting",
         "Driver exits the car and looks at horizon, close-up shot"]
        """
        
        original_prompt = "Un coche atravesando el desierto, se detiene y el conductor contempla el horizonte"
        prompt_sequence = create_multiprompt_sequence(original_prompt)
        
        # Verificar que se devuelva una secuencia de prompts
        self.assertIsInstance(prompt_sequence, list)
        self.assertEqual(len(prompt_sequence), 3)
        self.assertIn("desert", prompt_sequence[0])
        self.assertIn("sunset", prompt_sequence[1])
        self.assertIn("horizon", prompt_sequence[2])

    @patch('main.orchestrator')
    def test_create_multiprompt_sequence_json_error(self, mock_orchestrator):
        """Verifica que se maneje correctamente un error en el formato JSON."""
        # Configurar el mock para que devuelva un JSON inválido
        mock_orchestrator.generate_response.return_value = "Invalid JSON"
        
        original_prompt = "Un gato jugando con un perro"
        prompt_sequence = create_multiprompt_sequence(original_prompt)
        
        # Verificar que se caiga a un solo prompt mejorado
        self.assertIsInstance(prompt_sequence, list)
        self.assertEqual(len(prompt_sequence), 1)
        
        # Verificar que se llamó a enhance_video_prompt como fallback
        mock_orchestrator.generate_response.assert_called()

    @patch('main.orchestrator')
    def test_create_multiprompt_sequence_empty_response(self, mock_orchestrator):
        """Verifica que se maneje correctamente una respuesta vacía."""
        # Configurar el mock para que devuelva una respuesta vacía
        mock_orchestrator.generate_response.return_value = ""
        
        original_prompt = "Un rayo en una tormenta"
        prompt_sequence = create_multiprompt_sequence(original_prompt)
        
        # Verificar que se caiga a un solo prompt mejorado
        self.assertIsInstance(prompt_sequence, list)
        self.assertEqual(len(prompt_sequence), 1)

    def test_update_media_response_multi_valid(self):
        """Verifica que se formateen correctamente múltiples URLs."""
        media_urls = [
            "https://example.com/video1.mp4",
            "https://example.com/video2.mp4",
            "https://example.com/video3.mp4"
        ]
        
        response = update_media_response_multi(media_urls, "Video")
        
        # Verificar que la respuesta incluya todas las URLs
        self.assertIn("3 segmentos secuenciales", response)
        self.assertIn("Segmento 1", response)
        self.assertIn("Segmento 2", response)
        self.assertIn("Segmento 3", response)
        self.assertIn("https://example.com/video1.mp4", response)
        self.assertIn("https://example.com/video2.mp4", response)
        self.assertIn("https://example.com/video3.mp4", response)

    def test_update_media_response_multi_empty(self):
        """Verifica que se maneje correctamente una lista vacía de URLs."""
        media_urls = []
        
        response = update_media_response_multi(media_urls, "Video")
        
        # Verificar que la respuesta indique error
        self.assertIn("No se pudo generar el video", response)

    def test_update_media_response_multi_invalid_urls(self):
        """Verifica que se manejen correctamente URLs inválidas."""
        media_urls = ["", None, "invalid"]
        
        response = update_media_response_multi(media_urls, "Video")
        
        # Verificar que la respuesta indique error
        self.assertIn("No se pudo generar el video", response)

    def test_update_media_response_multi_mixed_formats(self):
        """Verifica que se manejen correctamente formatos mixtos de archivo."""
        media_urls = [
            "https://example.com/video1.mp4",
            "https://example.com/file.xyz",  # Formato no reconocido
            "https://example.com/video3.mp4"
        ]
        
        response = update_media_response_multi(media_urls, "Video")
        
        # Verificar que se embeben los formatos reconocidos y se dan como enlaces los demás
        self.assertIn("3 segmentos secuenciales", response)
        self.assertIn("https://example.com/video1.mp4", response)
        self.assertIn("[Enlace](https://example.com/file.xyz)", response)


if __name__ == "__main__":
    unittest.main()