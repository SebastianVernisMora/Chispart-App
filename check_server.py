#!/usr/bin/env python3

# Verificar si el servidor puede iniciarse
import sys
import os
sys.path.insert(0, '.')

try:
    print("Verificando importaciones...")
    from fastapi import FastAPI
    print("✅ FastAPI OK")
    
    from pathlib import Path
    print("✅ Path OK")
    
    import main
    print("✅ main.py se puede importar")
    
    print("\n🚀 Iniciando servidor...")
    
    if __name__ == "__main__":
        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=False)
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()