"""
Comando 'media' para creación interactiva de contenido multimedia.
"""
import argparse
import os
import sys
import time
import importlib.util
from urllib.parse import urlparse
import requests
from ..core.ai_client import AIOrchestrator
from ..utils.profiles import (
    create_interactive_profile,
    get_active_profile,
    list_profiles,
    set_active_profile,
    load_profile,
    get_active_profile_name,
)
from ..utils.image import overlay_logo

# El catálogo de modelos se puede mover a un archivo de config, pero por ahora lo mantenemos aquí.
MODEL_CATALOG = {
    "Video": [
        "blackboxai/google/veo-3",
        "blackboxai/google/veo-3-fast",
    ],
    "Image": [
        "blackboxai/black-forest-labs/flux-1.1-pro-ultra",
        "blackboxai/black-forest-labs/flux-schnell",
        "blackboxai/bytedance/hyper-flux-8step",
        "blackboxai/stability-ai/stable-diffusion",
        "blackboxai/prompthero/openjourney",
    ],
    "Text": [
        "blackboxai/google/gemma-2-9b-it:free",
        "blackboxai/mistralai/mistral-7b-instruct:free",
        "blackboxai/meta-llama/llama-3.1-8b-instruct",
    ]
}

# Configuración de límites por modelo para imágenes
IMAGE_MODEL_LIMITS = {
    # Modelos que permiten 1 imagen por solicitud
    "blackboxai/salesforce/blip": 1,
    "blackboxai/andreasjansson/blip-2": 1,
    "blackboxai/philz1337x/clarity-upscaler": 1,
    "blackboxai/krthr/clip-embeddings": 1,
    "blackboxai/sczhou/codeformer": 1,
    "blackboxai/jagilley/controlnet-scribble": 1,
    "blackboxai/fofr/face-to-many": 1,
    "blackboxai/black-forest-labs/flux-1.1-pro": 1,
    "blackboxai/black-forest-labs/flux-1.1-pro-ultra": 1,
    "blackboxai/black-forest-labs/flux-kontext-pro": 1,
    "blackboxai/black-forest-labs/flux-pro": 1,
    "blackboxai/prunaai/flux.1-dev": 1,
    "blackboxai/tencentarc/gfpgan": 1,
    "blackboxai/xinntao/gfpgan": 1,
    "blackboxai/adirik/grounding-dino": 1,
    "blackboxai/pengdaqian2020/image-tagger": 1,
    "blackboxai/allenhooo/lama": 1,
    "blackboxai/yorickvp/llava-13b": 1,
    "blackboxai/google/nano-banana": 1,
    "blackboxai/falcons-ai/nsfw_image_detection": 1,
    "blackboxai/nightmareai/real-esrgan": 1,
    "blackboxai/daanelson/real-esrgan-a100": 1,
    "blackboxai/abiruyt/text-extract-ocr": 1,
    
    # Modelos que permiten 4 imágenes por solicitud
    "blackboxai/black-forest-labs/flux-dev": 4,
    "blackboxai/black-forest-labs/flux-schnell": 4,
    "blackboxai/bytedance/hyper-flux-8step": 4,
    "blackboxai/ai-forever/kandinsky-2.2": 4,
    "blackboxai/datacte/proteus-v0.2": 4,
    "blackboxai/stability-ai/sdxl": 4,
    "blackboxai/fofr/sdxl-emoji": 4,
    "blackboxai/bytedance/sdxl-lightning-4step": 4,
    "blackboxai/stability-ai/stable-diffusion": 4,
    "blackboxai/stability-ai/stable-diffusion-inpainting": 4,
    
    # Modelos con más capacidad
    "blackboxai/prompthero/openjourney": 10,
}

# Valor por defecto para modelos no listados
DEFAULT_IMAGE_LIMIT = 1

def download_media(url, model_name, extension_hint=None):
    """Descarga un archivo desde una URL y lo guarda localmente."""
    if not url or not isinstance(url, str) or not url.startswith("http"):
        print("URL inválida o vacía. No se puede descargar.")
        return None

    print(f"Intentando descargar desde: {url}")
    try:
        response = requests.get(url, stream=True, timeout=180)
        response.raise_for_status()

        # Determinar la extensión del archivo
        path = urlparse(url).path
        ext = os.path.splitext(path)[1]
        
        # Si no hay extensión, intentar determinarla por el Content-Type
        if not ext:
            content_type = response.headers.get('content-type', '')
            if 'video/mp4' in content_type or extension_hint == '.mp4': ext = '.mp4'
            elif 'image/webp' in content_type or extension_hint == '.webp': ext = '.webp'
            elif 'image/jpeg' in content_type or extension_hint == '.jpg': ext = '.jpg'
            elif 'image/png' in content_type or extension_hint == '.png': ext = '.png'
            else: ext = '.out'

        # Crear un nombre de archivo seguro basado en el modelo y timestamp
        safe_model_name = model_name.split('/')[-1].replace(':', '_')
        filename = f"{safe_model_name}-{int(time.time())}{ext}"

        # Guardar el archivo
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"\n✅ ¡Éxito! Archivo guardado como: {filename}")
        
        # Mostrar mensaje adicional sobre la visualización en la interfaz web
        media_type = "Video" if ext.lower() in ['.mp4', '.webm', '.ogg'] else "Imagen"
        print(f"ℹ️ En la interfaz web, este {media_type.lower()} se mostrará automáticamente embebido en la conversación.")
        
        return filename
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Error al descargar: {e}")
        return None

def run_image_batch(orchestrator: AIOrchestrator, args):
    """Flujo para creación de imágenes en masa."""
    print("--- Creación de Imágenes en Masa ---")
    
    # 1. Perfil de marca
    profile = get_active_profile()
    if profile:
        print(f"ℹ️ Usando perfil activo: {get_active_profile_name()}")
        use_profile = input("¿Usar este perfil? (s/n, 'n' para crear uno nuevo): ").strip().lower()
        if use_profile != 's':
            profile = create_interactive_profile()
    else:
        print("No hay un perfil activo.")
        profile = create_interactive_profile()

    if not profile:
        print("No se seleccionó un perfil. Abortando.")
        return

    # 2. Prompt y cantidad
    prompt = input("Introduce el prompt base para las imágenes: ").strip()
    if not prompt:
        print("El prompt no puede estar vacío.")
        return
        
    while True:
        try:
            num_images = int(input("¿Cuántas imágenes quieres crear? (ej: 10): ").strip())
            if num_images > 0:
                break
            else:
                print("Por favor, introduce un número positivo.")
        except ValueError:
            print("Entrada inválida. Introduce un número.")
    
    # Preguntar si usar generación multiprompt
    use_multiprompt = input("\n¿Quieres usar generación multiprompt para crear imágenes relacionadas? (s/n): ").strip().lower() == 's'

    # 3. Construir prompt con branding
    brand_prompt_parts = [prompt]
    if profile.get("brand_focus"):
        brand_prompt_parts.append(f"Estilo: {profile['brand_focus']}.")
    if profile.get("color_palette"):
        palette = ", ".join(profile['color_palette'])
        brand_prompt_parts.append(f"Paleta de colores: {palette}.")
    
    final_prompt = " ".join(brand_prompt_parts)
    print(f"\n🎨 Prompt final con branding: {final_prompt}")

    # 4. Seleccionar modelo de imagen
    print("\n--- Modelos de Imagen Disponibles ---")
    image_models = MODEL_CATALOG["Image"]
    for i, model in enumerate(image_models, 1):
        print(f"{i}. {model}")
    
    while True:
        try:
            model_idx = int(input(f"Elige un modelo (1-{len(image_models)}): "))
            if 1 <= model_idx <= len(image_models):
                selected_model = image_models[model_idx - 1]
                break
            else:
                print("Número de modelo inválido.")
        except ValueError:
            print("Entrada inválida.")
    
    # 5. Generar imágenes
    if use_multiprompt:
        # Usar el sistema de generación multiprompt
        try:
            # Importar la función create_multiprompt_sequence de forma dinámica
            spec = importlib.util.spec_from_file_location("main", "../../main.py")
            main_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(main_module)
            create_multiprompt_sequence = main_module.create_multiprompt_sequence
            
            print("\n--- Analizando y dividiendo el prompt en segmentos ---")
            
            # Dividir el prompt en segmentos coherentes
            prompt_segments = create_multiprompt_sequence(final_prompt, media_type="Image")
            print(f"\n✅ Prompt dividido en {len(prompt_segments)} segmentos")
            
            # Obtener el límite de imágenes por solicitud para este modelo
            model_limit = IMAGE_MODEL_LIMITS.get(selected_model, DEFAULT_IMAGE_LIMIT)
            print(f"\nℹ️ Modelo {selected_model} permite {model_limit} imágenes por solicitud")
            
            # Generar imágenes
            image_urls = []
            
            # Si el modelo permite más de una imagen por solicitud y tenemos múltiples prompts
            if model_limit > 1 and len(prompt_segments) > 1:
                # Procesar en lotes según el límite del modelo
                for i in range(0, len(prompt_segments), model_limit):
                    batch_prompts = prompt_segments[i:i+model_limit]
                    print(f"\n--- Procesando lote {i//model_limit + 1}, con {len(batch_prompts)} prompts ---")
                    
                    # Para cada prompt en el lote actual
                    for j, segment_prompt in enumerate(batch_prompts):
                        prompt_index = i + j
                        print(f"\n--- ⏳ Generando imagen {prompt_index+1}/{len(prompt_segments)} ---")
                        print(f"Prompt: {segment_prompt}")
                        
                        try:
                            image_url = orchestrator.generate_response(
                                segment_prompt,
                                model_type=selected_model,
                                max_tokens=1024
                            )
                            
                            if image_url and image_url.startswith('http'):
                                image_urls.append(image_url)
                                downloaded_path = download_media(image_url, selected_model, extension_hint=".png")
                                
                                if downloaded_path and profile.get("logo_path"):
                                    output_with_logo = f"final_{os.path.basename(downloaded_path)}"
                                    overlay_logo(downloaded_path, profile["logo_path"], output_with_logo)
                                    print(f"🖼️ Imagen con logo guardada como: {output_with_logo}")
                            else:
                                print(f"Respuesta inesperada (no es una URL): {image_url}")
                                
                        except Exception as e:
                            print(f"❌ Error al generar la imagen del segmento {prompt_index+1}: {e}")
            else:
                # Modelo solo permite una imagen por solicitud o tenemos un solo prompt
                for i, segment_prompt in enumerate(prompt_segments):
                    print(f"\n--- ⏳ Generando imagen {i+1}/{len(prompt_segments)} ---")
                    print(f"Prompt: {segment_prompt}")
                    
                    try:
                        image_url = orchestrator.generate_response(
                            segment_prompt,
                            model_type=selected_model,
                            max_tokens=1024
                        )
                        
                        if image_url and image_url.startswith('http'):
                            image_urls.append(image_url)
                            downloaded_path = download_media(image_url, selected_model, extension_hint=".png")
                            
                            if downloaded_path and profile.get("logo_path"):
                                output_with_logo = f"final_{os.path.basename(downloaded_path)}"
                                overlay_logo(downloaded_path, profile["logo_path"], output_with_logo)
                                print(f"🖼️ Imagen con logo guardada como: {output_with_logo}")
                        else:
                            print(f"Respuesta inesperada (no es una URL): {image_url}")
                            
                    except Exception as e:
                        print(f"❌ Error al generar la imagen del segmento {i+1}: {e}")
            
            print(f"\n✅ Generación multiprompt completada: {len(image_urls)}/{len(prompt_segments)} imágenes creadas")
            
        except Exception as e:
            print(f"\n❌ Error en la generación multiprompt: {e}")
            print("Continuando con el método de generación estándar...")
            use_multiprompt = False
    
    if not use_multiprompt:
        # Generación estándar (una imagen por prompt)
        for i in range(num_images):
            print(f"\n--- ⏳ Generando imagen {i + 1}/{num_images} con {selected_model} ---")
            try:
                image_url = orchestrator.generate_response(
                    final_prompt,
                    model_type=selected_model,
                    max_tokens=1024  # Ajustar según sea necesario para modelos de imagen
                )
                
                if image_url and image_url.startswith('http'):
                    downloaded_path = download_media(image_url, selected_model, extension_hint=".png")
                    
                    if downloaded_path and profile.get("logo_path"):
                        output_with_logo = f"final_{os.path.basename(downloaded_path)}"
                        overlay_logo(downloaded_path, profile["logo_path"], output_with_logo)
                        print(f"🖼️ Imagen con logo guardada como: {output_with_logo}")
                        
                    # Detectar extensión para determinar si se puede embeber
                    ext = os.path.splitext(image_url)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        print(f"🔗 URL para embebido web: {image_url}")
                else:
                    print(f"Respuesta inesperada (no es una URL): {image_url}")

            except Exception as e:
                print(f"❌ Error al generar la imagen {i + 1}: {e}")

def run_profile_command(args):
    """Maneja los subcomandos de perfiles."""
    if args.profile_subcommand == "create":
        create_interactive_profile()
    elif args.profile_subcommand == "list":
        print("--- Perfiles de Marca Disponibles ---")
        profiles = list_profiles()
        if not profiles:
            print("No se han encontrado perfiles.")
        else:
            active = get_active_profile_name()
            for p in profiles:
                print(f"- {p} {'(activo)' if p == active else ''}")
    elif args.profile_subcommand == "activate":
        if not args.name:
            print("Error: Debes especificar el nombre del perfil a activar.")
            return
        try:
            set_active_profile(args.name)
            print(f"✅ Perfil '{args.name}' activado.")
        except FileNotFoundError as e:
            print(f"❌ Error: {e}")
    elif args.profile_subcommand == "show":
        profile_name = args.name or get_active_profile_name()
        if not profile_name:
            print("No hay un perfil activo. Especifica un nombre con --name.")
            return
        profile_data = load_profile(profile_name)
        if profile_data:
            import json
            print(f"--- Perfil: {profile_name} ---")
            print(json.dumps(profile_data, indent=2))
        else:
            print(f"No se encontró el perfil '{profile_name}'.")

def run_media_command(orchestrator: AIOrchestrator):
    """Punto de entrada principal para el comando 'media'."""
    parser = argparse.ArgumentParser(description="Herramienta de creación multimedia interactiva.")
    subparsers = parser.add_subparsers(dest="media_command", help="Comandos de medios")

    # Subcomando para imágenes en masa
    img_parser = subparsers.add_parser("image-batch", help="Crear múltiples imágenes con un perfil de marca.")
    
    # Subcomando para perfiles
    prof_parser = subparsers.add_parser("profile", help="Gestionar perfiles de marca.")
    prof_sub = prof_parser.add_subparsers(dest="profile_subcommand", help="Acciones de perfil")
    prof_sub.add_parser("create", help="Crear un nuevo perfil interactivamente.")
    prof_sub.add_parser("list", help="Listar perfiles existentes.")
    activate_parser = prof_sub.add_parser("activate", help="Establecer un perfil como activo.")
    activate_parser.add_argument("name", help="Nombre del perfil a activar.")
    show_parser = prof_sub.add_parser("show", help="Mostrar detalles de un perfil.")
    show_parser.add_argument("--name", help="Nombre del perfil a mostrar (por defecto, el activo).")

    # Parsear argumentos. Si no hay, mostrar ayuda.
    if len(sys.argv) < 3: # blackbox-tool media -> sin subcomando
        parser.print_help()
        return

    args = parser.parse_args(sys.argv[2:]) # Ignorar 'blackbox-tool' y 'media'

    if args.media_command == "image-batch":
        run_image_batch(orchestrator, args)
    elif args.media_command == "profile":
        run_profile_command(args)
    else:
        # Lógica original de chat de texto como fallback o comando por defecto
        print("Comando no reconocido. Para chat de texto, use el comando 'repl'.")
        parser.print_help()