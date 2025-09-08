"""
Tests para el módulo test_generator
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from blackbox_hybrid_tool.core.test_generator import (
    TestGeneratorClass, 
    CodeAnalyzer, 
    CoverageAnalyzer
)


class TestCodeAnalyzer:
    """Tests para la clase CodeAnalyzer"""

    def test_analyze_python_file_success(self):
        """Test análisis exitoso de archivo Python"""
        # Código de ejemplo
        python_code = '''
def add_numbers(a, b):
    """Suma dos números"""
    return a + b

class Calculator:
    """Calculadora simple"""
    
    def multiply(self, a, b):
        return a * b

import os
from math import sqrt
'''
        
        with patch('builtins.open', mock_open(read_data=python_code)):
            result = CodeAnalyzer.analyze_python_file("test.py")
            
            # Verificar estructura del resultado
            assert result['file_path'] == "test.py"
            assert len(result['functions']) == 2  # add_numbers y multiply (método de clase también se cuenta)
            function_names = [f['name'] for f in result['functions']]
            assert 'add_numbers' in function_names
            assert len(result['classes']) == 1
            assert result['classes'][0]['name'] == 'Calculator'
            assert 'os' in result['imports']
            assert 'math.sqrt' in result['imports']

    def test_analyze_python_file_error(self):
        """Test manejo de errores en análisis"""
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = CodeAnalyzer.analyze_python_file("nonexistent.py")
            
            assert 'error' in result
            assert result['functions'] == []
            assert result['classes'] == []


class TestTestGenerator:
    """Tests para la clase TestGenerator"""

    def setup_method(self):
        """Configuración inicial para cada test"""
        # Mock del AIOrchestrator
        self.mock_ai = Mock()
        self.generator = TestGeneratorClass(self.mock_ai)

    def test_initialization(self):
        """Test de inicialización del generador"""
        assert self.generator is not None
        assert hasattr(self.generator, 'generate_tests_for_file')
        assert self.generator.supported_languages == ['python', 'javascript', 'java', 'go']

    def test_generate_test_for_function(self):
        """Test generación de test para función"""
        # Configurar mock
        self.mock_ai.generate_response.return_value = '''
def test_add_numbers():
    assert add_numbers(2, 3) == 5
    assert add_numbers(0, 0) == 0
    assert add_numbers(-1, 1) == 0
'''
        
        func_info = {
            'name': 'add_numbers',
            'args': ['a', 'b'],
            'docstring': 'Suma dos números'
        }
        
        context = {'content': 'def add_numbers(a, b): return a + b'}
        
        result = self.generator.generate_test_for_function(func_info, context)
        
        assert "def test_add_numbers" in result
        self.mock_ai.generate_response.assert_called_once()

    def test_generate_test_for_class(self):
        """Test generación de test para clase"""
        # Configurar mock
        self.mock_ai.generate_response.return_value = '''
class TestCalculator:
    def test_multiply(self):
        calc = Calculator()
        assert calc.multiply(2, 3) == 6
'''
        
        class_info = {
            'name': 'Calculator',
            'methods': [{'name': 'multiply', 'args': ['self', 'a', 'b']}],
            'docstring': 'Calculadora simple'
        }
        
        context = {'content': 'class Calculator: pass'}
        
        result = self.generator.generate_test_for_class(class_info, context)
        
        assert "TestCalculator" in result
        self.mock_ai.generate_response.assert_called_once()

    @patch('blackbox_hybrid_tool.core.test_generator.CodeAnalyzer.analyze_python_file')
    def test_generate_tests_for_file_python(self, mock_analyze):
        """Test generación de tests para archivo Python"""
        # Configurar mocks
        mock_analyze.return_value = {
            'file_path': 'test.py',
            'functions': [
                {'name': 'add_numbers', 'args': ['a', 'b'], 'docstring': 'Suma'}
            ],
            'classes': [
                {'name': 'Calculator', 'methods': [], 'docstring': 'Calc'}
            ],
            'imports': [],
            'content': 'test content'
        }
        
        self.mock_ai.generate_response.return_value = "test code"
        
        result = self.generator.generate_tests_for_file("test.py", "python")
        
        assert result['file_path'] == 'test.py'
        assert result['language'] == 'python'
        assert len(result['tests']) == 2  # 1 función + 1 clase
        assert result['total_functions'] == 1
        assert result['total_classes'] == 1

    def test_generate_tests_unsupported_language(self):
        """Test con lenguaje no soportado"""
        result = self.generator.generate_tests_for_file("test.xyz", "unsupported")
        
        assert 'error' in result
        assert 'no soportado' in result['error']

    @patch('blackbox_hybrid_tool.core.test_generator.CodeAnalyzer.analyze_python_file')
    @patch('builtins.open', mock_open())
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.mkdir')
    def test_create_test_file(self, mock_mkdir, mock_exists, mock_analyze):
        """Test creación de archivo de test"""
        # Configurar mocks
        mock_exists.return_value = True
        mock_analyze.return_value = {
            'functions': [{'name': 'test_func', 'args': []}],
            'classes': [],
            'imports': [],
            'content': 'def test_func(): pass'
        }
        
        self.mock_ai.generate_response.return_value = "def test_test_func(): pass"
        
        result = self.generator.create_test_file("test.py", "tests")
        
        assert result.endswith("test_test.py")
        mock_mkdir.assert_called_once()


class TestCoverageAnalyzer:
    """Tests para la clase CoverageAnalyzer"""

    def setup_method(self):
        """Configuración inicial para cada test"""
        self.analyzer = CoverageAnalyzer()

    def test_initialization(self):
        """Test de inicialización del analizador"""
        assert self.analyzer is not None
        assert hasattr(self.analyzer, 'analyze_coverage')

    def test_analyze_coverage(self):
        """Test análisis de cobertura"""
        test_results = {
            'total_lines': 100,
            'covered_lines': 80,
            'coverage_percentage': 80.0,
            'missing_lines': [10, 20, 30]
        }
        
        result = self.analyzer.analyze_coverage(test_results)
        
        assert result['total_lines'] == 100
        assert result['covered_lines'] == 80
        assert result['coverage_percentage'] == 80.0
        assert len(result['missing_lines']) == 3

    def test_generate_coverage_report_text(self):
        """Test generación de reporte en formato texto"""
        coverage_data = {
            'total_lines': 100,
            'covered_lines': 85,
            'coverage_percentage': 85.0,
            'missing_lines': [10, 20]
        }
        
        report = self.analyzer.generate_coverage_report(coverage_data, 'text')
        
        assert "Coverage Report" in report
        assert "Total Lines: 100" in report
        assert "Covered Lines: 85" in report
        assert "Coverage: 85.0%" in report

    def test_generate_coverage_report_json(self):
        """Test generación de reporte en formato JSON"""
        coverage_data = {
            'total_lines': 100,
            'covered_lines': 85,
            'coverage_percentage': 85.0,
            'missing_lines': [10, 20]
        }
        
        report = self.analyzer.generate_coverage_report(coverage_data, 'json')
        
        # Verificar que es JSON válido
        import json
        parsed = json.loads(report)
        assert parsed['total_lines'] == 100
        assert parsed['coverage_percentage'] == 85.0

    def test_generate_coverage_report_unsupported_format(self):
        """Test formato no soportado"""
        coverage_data = {'total_lines': 100}
        
        report = self.analyzer.generate_coverage_report(coverage_data, 'xml')
        
        assert report == "Formato no soportado"
