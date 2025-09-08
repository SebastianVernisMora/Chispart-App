"""
Utilidades para gestionar perfiles de creación de medios.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

PROFILE_DIR = Path.home() / ".config" / "blackbox_hybrid_tool" / "profiles"
ACTIVE_PROFILE_FILE = PROFILE_DIR / ".active_profile"

def ensure_profile_dir():
    """Asegura que el directorio de perfiles exista."""
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def save_profile(profile_name: str, data: Dict[str, Any]) -> Path:
    """Guarda un perfil en un archivo JSON."""
    ensure_profile_dir()
    profile_path = PROFILE_DIR / f"{profile_name}.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return profile_path

def load_profile(profile_name: str) -> Optional[Dict[str, Any]]:
    """Carga un perfil desde un archivo JSON."""
    profile_path = PROFILE_DIR / f"{profile_name}.json"
    if profile_path.exists():
        with open(profile_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def list_profiles() -> List[str]:
    """Lista los nombres de los perfiles disponibles."""
    ensure_profile_dir()
    return [p.stem for p in PROFILE_DIR.glob("*.json")]

def set_active_profile(profile_name: str):
    """Establece el perfil activo."""
    ensure_profile_dir()
    if (PROFILE_DIR / f"{profile_name}.json").exists():
        ACTIVE_PROFILE_FILE.write_text(profile_name, encoding="utf-8")
    else:
        raise FileNotFoundError(f"Perfil '{profile_name}' no encontrado.")

def get_active_profile_name() -> Optional[str]:
    """Obtiene el nombre del perfil activo."""
    if ACTIVE_PROFILE_FILE.exists():
        return ACTIVE_PROFILE_FILE.read_text(encoding="utf-8").strip()
    return None

def get_active_profile() -> Optional[Dict[str, Any]]:
    """Carga el perfil activo."""
    active_name = get_active_profile_name()
    if active_name:
        return load_profile(active_name)
    return None

def create_interactive_profile() -> Optional[Dict[str, Any]]:
    """Crea un nuevo perfil de forma interactiva."""
    print("--- Creación de Nuevo Perfil de Marca ---")
    profile_name = input("Nombre del perfil (ej: mi_marca): ").strip()
    if not profile_name:
        print("El nombre del perfil no puede estar vacío.")
        return None

    palette_str = input("Paleta de colores (ej: #FFFFFF, #000000): ").strip()
    color_palette = [c.strip() for c in palette_str.split(",") if c.strip()]

    logo_path_str = input("Ruta al archivo del logo (opcional): ").strip()
    logo_path = None
    if logo_path_str:
        if Path(logo_path_str).exists():
            logo_path = logo_path_str
        else:
            print(f"Advertencia: El archivo de logo '{logo_path_str}' no fue encontrado.")

    brand_focus = input("Enfoque de la marca (ej: moderna, minimalista): ").strip()

    profile_data = {
        "profile_name": profile_name,
        "color_palette": color_palette,
        "logo_path": logo_path,
        "brand_focus": brand_focus,
    }

    save_profile(profile_name, profile_data)
    print(f"✅ Perfil '{profile_name}' guardado.")
    
    set_active = input("¿Establecer este como perfil activo? (s/n): ").strip().lower()
    if set_active == 's':
        set_active_profile(profile_name)
        print(f"✅ Perfil '{profile_name}' establecido como activo.")

    return profile_data
