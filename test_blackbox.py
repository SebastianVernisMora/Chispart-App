#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración de Blackbox AI
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from blackbox_hybrid_tool.core.ai_client import AIOrchestrator

def test_blackbox_connection():
    """Prueba la conexión con Blackbox AI"""
    print("🔧 Probando configuración de Blackbox AI...")

    try:
        # Crear orquestador
        orchestrator = AIOrchestrator()

        # Intentar obtener cliente Blackbox
        client = orchestrator.get_client("blackbox")
        print("✅ Cliente Blackbox creado exitosamente")

        # Probar una consulta simple
        print("🔄 Probando consulta a Blackbox AI...")
        response = orchestrator.generate_response(
            "Hola, ¿puedes confirmar que estás funcionando?",
            model_type="blackbox"
        )

        if "Error" in response:
            print(f"❌ Error en la respuesta: {response}")
            return False
        else:
            print("✅ Respuesta exitosa de Blackbox AI:")
            print(f"   Respuesta: {response[:100]}...")
            return True

    except Exception as e:
        print(f"❌ Error al probar Blackbox: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_blackbox_connection()
    if success:
        print("\n🎉 ¡La configuración de Blackbox AI está funcionando correctamente!")
        print("Puedes proceder con el despliegue del contenedor.")
    else:
        print("\n💥 Hay problemas con la configuración de Blackbox AI.")
        print("Revisa la configuración antes de intentar el despliegue.")
