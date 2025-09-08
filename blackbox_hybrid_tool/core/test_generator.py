"""
Generador de tests automatizado
Inspirado en qodo-cover con integración de Blackbox AI
"""

import os
import ast
import inspect
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import importlib.util
from .ai_client import AIOrchestrator


class CodeAnalyzer:
    """Analiza código fuente para extraer información de funciones y clases"""

    @staticmethod
    def analyze_python_file(file_path: str) -> Dict[str, Any]:
        """Analiza un archivo Python y extrae funciones, clases y dependencias"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            functions = []
            classes = []
            imports = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        'name': node.name,
                        'args': [arg.arg for arg in node.args.args],
                        'line': node.lineno,
                        'docstring': ast.get_docstring(node)
                    })
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append({
                                'name': item.name,
                                'args': [arg.arg for arg in item.args.args],
                                'line': item.lineno
                            })

                    classes.append({
                        'name': node.name,
                        'methods': methods,
                        'line': node.lineno,
                        'docstring': ast.get_docstring(node)
                    })
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")

            return {
                'file_path': file_path,
                'functions': functions,
                'classes': classes,
                'imports': imports,
                'content': content
            }

        except Exception as e:
            return {
                'file_path': file_path,
                'error': str(e),
                'functions': [],
                'classes': [],
                'imports': [],
                'content': ''
            }


class TestGeneratorClass:
    """Generador de tests automatizado usando AI"""

    def __init__(self, ai_orchestrator: Optional[AIOrchestrator] = None):
        self.ai = ai_orchestrator or AIOrchestrator()
        self.supported_languages = ['python', 'javascript', 'java', 'go']

    def generate_test_for_function(self, func_info: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Genera test para una función específica"""

        prompt = f"""
Genera un test unitario completo para la siguiente función Python:

Función: {func_info['name']}
Argumentos: {', '.join(func_info['args'])}
Docstring: {func_info.get('docstring', 'No disponible')}

Contexto del archivo:
```python
{context.get('content', '')}
```

Importaciones relevantes: {', '.join(context.get('imports', []))}

Por favor genera:
1. Un test unitario usando pytest
2. Casos de prueba que cubran diferentes escenarios
3. Mocks si es necesario para dependencias externas
4. Aserciones apropiadas

El test debe ser funcional y seguir las mejores prácticas de testing.
"""

        return self.ai.generate_response(prompt, temperature=0.3)

    def generate_test_for_class(self, class_info: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Genera tests para una clase completa"""

        prompt = f"""
Genera tests unitarios completos para la siguiente clase Python:

Clase: {class_info['name']}
Métodos: {[m['name'] for m in class_info['methods']]}
Docstring: {class_info.get('docstring', 'No disponible')}

Contexto del archivo:
```python
{context.get('content', '')}
```

Por favor genera:
1. Tests para cada método público
2. Tests de integración si es apropiado
3. Setup y teardown si es necesario
4. Casos de borde y escenarios de error

Usa pytest y sigue las mejores prácticas de testing en Python.
"""

        return self.ai.generate_response(prompt, temperature=0.3)

    def generate_tests_for_file(self, file_path: str, language: str = 'python') -> Dict[str, Any]:
        """Genera tests completos para un archivo"""

        if language.lower() not in self.supported_languages:
            return {
                'error': f'Lenguaje {language} no soportado. Lenguajes disponibles: {", ".join(self.supported_languages)}'
            }

        if language.lower() == 'python':
            analysis = CodeAnalyzer.analyze_python_file(file_path)

            if 'error' in analysis:
                return {'error': analysis['error']}

            tests = []

            # Generar tests para funciones
            for func in analysis['functions']:
                if not func['name'].startswith('_'):  # Solo funciones públicas
                    test_code = self.generate_test_for_function(func, analysis)
                    tests.append({
                        'type': 'function',
                        'target': func['name'],
                        'test_code': test_code
                    })

            # Generar tests para clases
            for cls in analysis['classes']:
                test_code = self.generate_test_for_class(cls, analysis)
                tests.append({
                    'type': 'class',
                    'target': cls['name'],
                    'test_code': test_code
                })

            return {
                'file_path': file_path,
                'language': language,
                'tests': tests,
                'total_functions': len(analysis['functions']),
                'total_classes': len(analysis['classes'])
            }

        else:
            return {
                'error': f'Generación de tests para {language} aún no implementada'
            }

    def create_test_file(self, source_file: str, output_dir: str = 'tests') -> str:
        """Crea archivo de test basado en el archivo fuente"""

        source_path = Path(source_file)
        if not source_path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {source_file}")

        # Determinar lenguaje por extensión
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.java': 'java',
            '.go': 'go'
        }

        language = language_map.get(source_path.suffix.lower(), 'python')

        # Generar tests
        result = self.generate_tests_for_file(str(source_path), language)

        if 'error' in result:
            raise ValueError(result['error'])

        # Crear directorio de tests si no existe
        test_dir = Path(output_dir)
        test_dir.mkdir(exist_ok=True)

        # Nombre del archivo de test
        test_filename = f"test_{source_path.stem}.py"
        test_filepath = test_dir / test_filename

        # Combinar todos los tests en un archivo
        test_content = f'''"""
Tests generados automáticamente para {source_path.name}
Generado por Blackbox Hybrid Tool
"""

import pytest
'''

        for test in result['tests']:
            test_content += f"\n\n# Tests para {test['target']}\n"
            test_content += test['test_code']
            test_content += "\n"

        # Escribir archivo de test
        with open(test_filepath, 'w', encoding='utf-8') as f:
            f.write(test_content)

        return str(test_filepath)


class CoverageAnalyzer:
    """Analiza cobertura de código (simplificado)"""

    def __init__(self):
        self.coverage_data = {}

    def analyze_coverage(self, test_results: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza resultados de cobertura"""

        # Implementación simplificada
        # En un caso real, esto integraría con coverage.py

        return {
            'total_lines': test_results.get('total_lines', 0),
            'covered_lines': test_results.get('covered_lines', 0),
            'coverage_percentage': test_results.get('coverage_percentage', 0),
            'missing_lines': test_results.get('missing_lines', [])
        }

    def generate_coverage_report(self, coverage_data: Dict[str, Any], format: str = 'text') -> str:
        """Genera reporte de cobertura"""

        if format == 'text':
            return f"""
Coverage Report
===============
Total Lines: {coverage_data.get('total_lines', 0)}
Covered Lines: {coverage_data.get('covered_lines', 0)}
Coverage: {coverage_data.get('coverage_percentage', 0):.1f}%
Missing Lines: {len(coverage_data.get('missing_lines', []))}
"""
        elif format == 'json':
            return json.dumps(coverage_data, indent=2)

        return "Formato no soportado"
