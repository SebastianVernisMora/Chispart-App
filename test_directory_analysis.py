#!/usr/bin/env python3
"""
Script para probar la nueva funcionalidad de análisis de directorio.
"""

import requests
import json

def test_directory_analysis():
    """Prueba la funcionalidad de análisis de directorio."""
    url = "http://localhost:8006/chat"
    
    # Datos para la solicitud de análisis de directorio
    data = {
        "prompt": "Analiza el directorio actual",
        "analyze_directory": "."
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            print("Respuesta del análisis de directorio:")
            print(json.dumps(result, indent=2))
        else:
            print(f"Error HTTP {response.status_code}: {response.text}")
    except Exception as e:
        print(f"Error al conectar con el servidor: {e}")

if __name__ == "__main__":
    test_directory_analysis()