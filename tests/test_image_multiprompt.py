"""
Tests para verificar la funcionalidad de multiprompt para imágenes.
"""
import unittest
from unittest.mock import patch, MagicMock
import pytest

# Importaciones para pruebas directas de las funciones
from main import create_multiprompt_sequence, update_media_response_multi, IMAGE_MODEL_LIMITS


class TestImageMultiprompt(unittest.TestCase):
    """Pruebas para la funcionalidad de secuenciado de prompts para imágenes."""

    @patch('main.orchestrator')
    def test_create_multiprompt_sequence_for_images_success(self, mock_orchestrator):
        """Verifica que se cree correctamente una secuencia de prompts para imágenes."""
        # Configurar el mock para que devuelva un JSON válido
        mock_orchestrator.generate_response.return_value = """
        ["A close-up view of a majestic eagle in flight, detailed feathers, sharp beak, against blue sky", 
         "A wide view of a mountain landscape with an eagle soaring, dramatic sunset lighting",
         "A detailed view of an eagle perched on a tree branch, looking for prey"]
        """
        
        original_prompt = "Un águila volando sobre las montañas y luego posada en un árbol"
        prompt_sequence = create_multiprompt_sequence(original_prompt, media_type="Image")
        
        # Verificar que se devuelva una secuencia de prompts
        self.assertIsInstance(prompt_sequence, list)
        self.assertEqual(len(prompt_sequence), 3)
        self.assertIn("eagle in flight", prompt_sequence[0])
        self.assertIn("mountain landscape", prompt_sequence[1])
        self.assertIn("perched on a tree", prompt_sequence[2])

    @patch('main.orchestrator')
    def test_create_multiprompt_sequence_for_images_json_error(self, mock_orchestrator):
        """Verifica que se maneje correctamente un error en el formato JSON para imágenes."""
        # Configurar el mock para que devuelva un JSON inválido
        mock_orchestrator.generate_response.return_value = "Invalid JSON"
        
        original_prompt = "Un conjunto de frutas tropicales"
        prompt_sequence = create_multiprompt_sequence(original_prompt, media_type="Image")
        
        # Verificar que se caiga a un solo prompt mejorado
        self.assertIsInstance(prompt_sequence, list)
        self.assertEqual(len(prompt_sequence), 1)
        
        # Verificar que se llamó a enhance_video_prompt como fallback
        mock_orchestrator.generate_response.assert_called()

    @patch('main.orchestrator')
    def test_create_multiprompt_sequence_for_images_empty_response(self, mock_orchestrator):
        """Verifica que se maneje correctamente una respuesta vacía para imágenes."""
        # Configurar el mock para que devuelva una respuesta vacía
        mock_orchestrator.generate_response.return_value = ""
        
        original_prompt = "Un paisaje de campo"
        prompt_sequence = create_multiprompt_sequence(original_prompt, media_type="Image")
        
        # Verificar que se caiga a un solo prompt mejorado
        self.assertIsInstance(prompt_sequence, list)
        self.assertEqual(len(prompt_sequence), 1)

    def test_update_media_response_multi_for_images_valid(self):
        """Verifica que se formateen correctamente múltiples URLs de imágenes."""
        media_urls = [
            "https://example.com/image1.jpg",
            "https://example.com/image2.png",
            "https://example.com/image3.webp"
        ]
        
        response = update_media_response_multi(media_urls, "Image")
        
        # Verificar que la respuesta incluya todas las URLs
        self.assertIn("3 segmentos relacionados", response)
        self.assertIn("Segmento 1", response)
        self.assertIn("Segmento 2", response)
        self.assertIn("Segmento 3", response)
        self.assertIn("https://example.com/image1.jpg", response)
        self.assertIn("https://example.com/image2.png", response)
        self.assertIn("https://example.com/image3.webp", response)

    def test_update_media_response_multi_for_images_empty(self):
        """Verifica que se maneje correctamente una lista vacía de URLs para imágenes."""
        media_urls = []
        
        response = update_media_response_multi(media_urls, "Image")
        
        # Verificar que la respuesta indique error
        self.assertIn("No se pudo generar", response)
        self.assertIn("imagen", response)


if __name__ == "__main__":
    unittest.main()