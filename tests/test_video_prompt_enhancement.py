"""
Tests para verificar la mejora de prompts de video.
"""
import unittest
from unittest.mock import patch, MagicMock
import pytest

# Importaciones para pruebas directas de la función
from main import enhance_video_prompt


class TestVideoPromptEnhancement(unittest.TestCase):
    """Pruebas para la funcionalidad de mejora de prompts de video."""

    @patch('main.orchestrator')
    def test_prompt_enhancement_success(self, mock_orchestrator):
        """Verifica que los prompts de video se mejoren correctamente."""
        # Configurar el mock para que devuelva una respuesta mejorada
        mock_orchestrator.generate_response.return_value = "A beautiful sunset over the ocean with waves crashing against rocks, cinematic wide angle, golden hour lighting, slow motion"
        
        original_prompt = "Una puesta de sol en el mar"
        enhanced = enhance_video_prompt(original_prompt)
        
        # Verificar que el prompt ha sido mejorado
        self.assertNotEqual(original_prompt, enhanced)
        self.assertTrue(len(enhanced) > len(original_prompt))
        mock_orchestrator.generate_response.assert_called_once()

    @patch('main.orchestrator')
    def test_prompt_enhancement_failure(self, mock_orchestrator):
        """Verifica que se maneje correctamente un fallo en la mejora del prompt."""
        # Configurar el mock para que devuelva un error
        mock_orchestrator.generate_response.side_effect = Exception("Error de conexión")
        
        original_prompt = "Un coche deportivo rojo"
        result = enhance_video_prompt(original_prompt)
        
        # Verificar que se devuelve el prompt original
        self.assertEqual(original_prompt, result)

    @patch('main.orchestrator')
    def test_prompt_enhancement_empty_response(self, mock_orchestrator):
        """Verifica que se maneje correctamente una respuesta vacía."""
        # Configurar el mock para que devuelva una respuesta vacía
        mock_orchestrator.generate_response.return_value = ""
        
        original_prompt = "Gatos jugando"
        result = enhance_video_prompt(original_prompt)
        
        # Verificar que se devuelve el prompt original
        self.assertEqual(original_prompt, result)

    @patch('main.orchestrator')
    def test_prompt_enhancement_dict_response(self, mock_orchestrator):
        """Verifica que se maneje correctamente una respuesta en formato diccionario."""
        # Configurar el mock para que devuelva un diccionario
        mock_orchestrator.generate_response.return_value = {
            "content": "Playful cats chasing toys in a sunlit living room, close-up shots, dynamic camera movement, 4K resolution, soft natural lighting"
        }
        
        original_prompt = "Gatos jugando"
        enhanced = enhance_video_prompt(original_prompt)
        
        # Verificar que el prompt ha sido extraído correctamente del diccionario
        self.assertEqual("Playful cats chasing toys in a sunlit living room, close-up shots, dynamic camera movement, 4K resolution, soft natural lighting", enhanced)


if __name__ == "__main__":
    unittest.main()