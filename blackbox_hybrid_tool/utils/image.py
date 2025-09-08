"""
Utilidades para procesamiento de imágenes.
"""
from PIL import Image
from pathlib import Path

def overlay_logo(base_image_path: str, logo_path: str, output_path: str, position: str = "bottom_right", padding: int = 10):
    """
    Superpone un logo en una imagen base.

    Args:
        base_image_path (str): Ruta a la imagen base.
        logo_path (str): Ruta al logo.
        output_path (str): Ruta para guardar la imagen resultante.
        position (str): Posición del logo. Opciones: "bottom_right", "bottom_left", "top_right", "top_left".
        padding (int): Espacio en píxeles desde los bordes.
    """
    try:
        base_image = Image.open(base_image_path).convert("RGBA")
        logo = Image.open(logo_path).convert("RGBA")

        # Redimensionar el logo si es muy grande (ej: 15% del ancho de la imagen base)
        max_logo_width = int(base_image.width * 0.15)
        if logo.width > max_logo_width:
            ratio = max_logo_width / logo.width
            new_height = int(logo.height * ratio)
            logo = logo.resize((max_logo_width, new_height), Image.Resampling.LANCZOS)

        # Calcular posición
        if position == "bottom_right":
            pos = (base_image.width - logo.width - padding, base_image.height - logo.height - padding)
        elif position == "bottom_left":
            pos = (padding, base_image.height - logo.height - padding)
        elif position == "top_right":
            pos = (base_image.width - logo.width - padding, padding)
        elif position == "top_left":
            pos = (padding, padding)
        else:
            raise ValueError("Posición no válida.")

        # Crear una capa transparente para pegar el logo
        transparent_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
        transparent_layer.paste(logo, pos)

        # Componer la imagen base con la capa del logo
        composite = Image.alpha_composite(base_image, transparent_layer)
        
        # Guardar como PNG para mantener la transparencia
        composite.save(output_path, "PNG")
        
        print(f"✅ Logo superpuesto y guardado en: {output_path}")

    except FileNotFoundError as e:
        print(f"❌ Error: No se encontró el archivo - {e}")
    except Exception as e:
        print(f"❌ Error al superponer el logo: {e}")
