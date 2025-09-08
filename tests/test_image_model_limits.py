"""
Tests para verificar la gestión de límites de modelos de imagen.
"""
import unittest
from unittest.mock import patch, MagicMock
import pytest

# Importaciones para pruebas directas de las funciones
from main import IMAGE_MODEL_LIMITS


class TestImageModelLimits(unittest.TestCase):
    """Pruebas para la funcionalidad de límites de modelos de imagen."""

    def test_image_model_limits_configuration(self):
        """Verifica que la configuración de límites de modelos exista y tenga el formato esperado."""
        # Verificar que IMAGE_MODEL_LIMITS existe y es un diccionario
        self.assertIsInstance(IMAGE_MODEL_LIMITS, dict)
        self.assertTrue(len(IMAGE_MODEL_LIMITS) > 0)
        
        # Verificar que todos los valores son enteros positivos
        for model, limit in IMAGE_MODEL_LIMITS.items():
            self.assertIsInstance(model, str)
            self.assertIsInstance(limit, int)
            self.assertGreater(limit, 0)
    
    def test_specific_model_limits(self):
        """Verifica que ciertos modelos tengan los límites esperados."""
        # Modelos con límite de 1
        self.assertEqual(IMAGE_MODEL_LIMITS.get("blackboxai/black-forest-labs/flux-1.1-pro-ultra"), 1)
        
        # Modelos con límite de 4
        self.assertEqual(IMAGE_MODEL_LIMITS.get("blackboxai/black-forest-labs/flux-schnell"), 4)
        self.assertEqual(IMAGE_MODEL_LIMITS.get("blackboxai/bytedance/hyper-flux-8step"), 4)
        self.assertEqual(IMAGE_MODEL_LIMITS.get("blackboxai/stability-ai/stable-diffusion"), 4)
        
        # Modelos con límite de 10
        self.assertEqual(IMAGE_MODEL_LIMITS.get("blackboxai/prompthero/openjourney"), 10)
    
    def test_model_categories_by_limit(self):
        """Verifica que haya una distribución adecuada de modelos por categoría de límite."""
        # Contar modelos por límite
        limits_count = {}
        for _, limit in IMAGE_MODEL_LIMITS.items():
            limits_count[limit] = limits_count.get(limit, 0) + 1
        
        # Verificar que hay modelos en distintas categorías
        self.assertIn(1, limits_count)
        self.assertIn(4, limits_count)
        
        # Verificar que hay varios modelos con límite 1
        self.assertGreaterEqual(limits_count.get(1, 0), 10)
        
        # Verificar que hay varios modelos con límite 4
        self.assertGreaterEqual(limits_count.get(4, 0), 5)


if __name__ == "__main__":
    unittest.main()