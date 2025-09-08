#!/usr/bin/env python3
"""
Prueba simple de endpoints
"""

import os
import shutil
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Test File API")

class ListDirectoryRequest(BaseModel):
    path: str = "."
    show_hidden: bool = False

@app.get("/")
async def root():
    return {"message": "File API Test"}

@app.post("/files/list")
async def list_directory(req: ListDirectoryRequest):
    """Lista archivos y directorios en una ruta específica"""
    try:
        base_dir = Path(".").resolve()
        target_path = (base_dir / req.path).resolve()
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Directorio no encontrado")
        
        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail="La ruta no es un directorio")
        
        items = []
        for item in target_path.iterdir():
            if not req.show_hidden and item.name.startswith('.'):
                continue
                
            relative_path = item.relative_to(base_dir)
            items.append({
                "name": item.name,
                "path": str(relative_path),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
                "modified": item.stat().st_mtime
            })
        
        # Ordenar: directorios primero, luego archivos
        items.sort(key=lambda x: (x['type'] != 'directory', x['name'].lower()))
        
        return {
            "status": "success",
            "path": str(target_path.relative_to(base_dir)),
            "items": items
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🧪 Servidor de prueba iniciando en http://localhost:8006")
    uvicorn.run(app, host="0.0.0.0", port=8006)