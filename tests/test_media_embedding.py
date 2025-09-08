"""
Test para verificar el embebido de multimedia en respuestas.
"""
import unittest
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

# Importaciones para pruebas directas de la función
from main import update_media_response


class TestMediaResponseFormatter(unittest.TestCase):
    """Pruebas para la funcionalidad de formateo de respuestas multimedia."""

    def test_image_embedding(self):
        """Verifica que las URLs de imágenes se formateen correctamente."""
        media_url = "https://example.com/test.jpg"
        media_type = "Image"
        
        response = update_media_response(media_url, media_type)
        
        # Verificar que la respuesta contiene la URL directa
        self.assertIn("https://example.com/test.jpg", response)
        # No debería contener 'Aquí está el enlace:'
        self.assertNotIn("Aquí está el enlace:", response)
        # Verificar formato específico para embebido
        self.assertIn("He generado tu image:\n", response)

    def test_video_embedding(self):
        """Verifica que las URLs de videos se formateen correctamente."""
        media_url = "https://example.com/test.mp4"
        media_type = "Video"
        
        response = update_media_response(media_url, media_type)
        
        # Verificar que la respuesta contiene la URL directa
        self.assertIn("https://example.com/test.mp4", response)
        # No debería contener 'Aquí está el enlace:'
        self.assertNotIn("Aquí está el enlace:", response)
        # Verificar formato específico para embebido
        self.assertIn("He generado tu video:\n", response)

    def test_unknown_media_type(self):
        """Verifica el manejo de URLs con tipos de archivo desconocidos."""
        media_url = "https://example.com/test.xyz"
        media_type = "Image"
        
        response = update_media_response(media_url, media_type)
        
        # Verificar que la respuesta contiene la URL pero como enlace
        self.assertIn("https://example.com/test.xyz", response)
        self.assertIn("Aquí está el enlace:", response)


if __name__ == "__main__":
    unittest.main()