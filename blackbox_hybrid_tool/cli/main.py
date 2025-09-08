#!/usr/bin/env python3
"""
Interfaz CLI para Blackbox Hybrid Tool
Herramienta híbrida de testing y análisis de código
"""

import argparse
import sys
import os
import json
from pathlib import Path
from typing import Optional

# Añadir el directorio raíz al path para importar módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_client import AIOrchestrator
from core.test_generator import TestGeneratorClass, CoverageAnalyzer
from utils.patcher import apply_unified_diff, parse_unified_diff
from utils.self_repo import (
    embed_snapshot,
    extract_snapshot,
    analyze_dependencies,
    ensure_embedded_snapshot,
    backup_current,
    replace_tree,
    make_snapshot,
)
from utils.github_client import GitHubClient
from utils.web import WebFetcher, WebSearch
from utils.ssh import run_ssh_command, sync_files, deploy_remote

# Helper function for JSON serialization
def json_dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


class CLI:
    """Interfaz de línea de comandos principal"""

    def __init__(self):
        self.ai_orchestrator = AIOrchestrator()
        self.test_generator = TestGeneratorClass(self.ai_orchestrator)
        self.coverage_analyzer = CoverageAnalyzer()

    def setup_parser(self) -> argparse.ArgumentParser:
        """Configura el parser de argumentos"""
        parser = argparse.ArgumentParser(
            description="Blackbox Hybrid Tool - Testing y análisis de código con IA",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Ejemplos de uso:
  %(prog)s generate-tests archivo.py
  %(prog)s analyze-coverage tests/
  %(prog)s ai-query "Cómo mejorar la cobertura de tests"
  %(prog)s switch-model blackboxai/openai/o1
            """
        )

        # Opción global de depuración
        parser.add_argument(
            '--debug', action='store_true', help='Imprime payloads y respuestas de la API'
        )

        subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')

        # Shell interactiva del proyecto con prompt CHISPART
        shell_parser = subparsers.add_parser(
            'shell',
            help='Inicia una shell interactiva del proyecto con tema CHISPART'
        )
        shell_parser.add_argument(
            '--no-clear', action='store_true', help='No limpiar pantalla antes de iniciar'
        )

        # Comando para generar tests
        generate_parser = subparsers.add_parser(
            'generate-tests',
            help='Genera tests automáticamente para un archivo'
        )
        generate_parser.add_argument(
            'file',
            help='Archivo fuente para generar tests'
        )
        generate_parser.add_argument(
            '-o', '--output',
            default='tests',
            help='Directorio de salida para los tests (por defecto: tests)'
        )
        generate_parser.add_argument(
            '-l', '--language',
            choices=['python', 'javascript', 'java', 'go'],
            default='python',
            help='Lenguaje del archivo fuente'
        )

        # Comando para analizar cobertura
        coverage_parser = subparsers.add_parser(
            'analyze-coverage',
            help='Analiza cobertura de código'
        )
        coverage_parser.add_argument(
            'path',
            help='Ruta al directorio de tests o archivo'
        )
        coverage_parser.add_argument(
            '-f', '--format',
            choices=['text', 'json'],
            default='text',
            help='Formato del reporte de cobertura'
        )

        # Comando para consultas AI
        ai_parser = subparsers.add_parser(
            'ai-query',
            help='Realiza consultas a la IA'
        )
        ai_parser.add_argument(
            'query',
            help='Consulta para la IA'
        )
        ai_parser.add_argument(
            '-m', '--model',
            help='Modelo AI a usar (opcional)'
        )

        # Comando para desarrollo asistido por IA
        aidx = subparsers.add_parser(
            'ai-dev', help='Genera un parche unified diff a partir de una instrucción'
        )
        aidx.add_argument('instruction', help='Instrucción de desarrollo (qué cambiar/agregar)')
        aidx.add_argument('-s', '--strategy', choices=['auto','fast','reasoning','code'], default='auto', help='Estrategia/modelo sugerido')
        aidx.add_argument('-m', '--model', help='Identificador de modelo a forzar (opcional)')
        aidx.add_argument('--allow-web', action='store_true', help='Permitir búsqueda web y uso en contexto')
        aidx.add_argument('-e', '--engine', choices=['serpapi','tavily'], help='Motor de búsqueda')
        aidx.add_argument('--apply', action='store_true', help='Aplicar automáticamente el parche si tests pasan')
        aidx.add_argument('--out-dir', default='patches', help='Directorio donde guardar el .patch propuesto')
        aidx.add_argument('--max-tokens', type=int, default=2048)
        aidx.add_argument('--temperature', type=float, default=0.3)

        # Comando para chat interactivo (REPL)
        repl_parser = subparsers.add_parser(
            'repl',
            help='Inicia una sesión de chat interactiva con contexto'
        )
        repl_parser.add_argument(
            '-m', '--model',
            help='Identificador de Blackbox a usar durante la sesión'
        )
        repl_parser.add_argument(
            '-s', '--session',
            help='Nombre de sesión para cargar/guardar historial (persistencia)'
        )
        repl_parser.add_argument(
            '-t', '--transcript',
            help='Ruta de archivo para guardar un log de la sesión (texto)'
        )

        # Comando para chat interactivo por categorías
        media_parser = subparsers.add_parser(
            'media',
            help='Inicia un chat interactivo para diferentes categorías de modelos (Video, Imagen, Texto).'
        )

        # Comando para crear/escribir archivos de texto
        wf_parser = subparsers.add_parser(
            'write-file',
            help='Crea o escribe un archivo de texto'
        )
        wf_parser.add_argument('path', help='Ruta del archivo a crear/escribir')
        group_src = wf_parser.add_mutually_exclusive_group(required=False)
        group_src.add_argument('-c', '--content', help='Contenido a escribir (texto)')
        group_src.add_argument('--stdin', action='store_true', help='Leer contenido desde STDIN')
        group_src.add_argument('-e', '--editor', action='store_true', help='Abrir editor ($EDITOR, nano o vi) para escribir el contenido')
        wf_parser.add_argument('--overwrite', action='store_true', help='Permitir sobrescribir si el archivo ya existe')

        # Comando para aplicar parches unified diff
        ap_parser = subparsers.add_parser(
            'apply-patch',
            help='Aplica un parche en formato unified diff al árbol de archivos'
        )
        srcgrp = ap_parser.add_mutually_exclusive_group(required=True)
        srcgrp.add_argument('-f', '--file', dest='patch_file', help='Archivo de parche (.patch/.diff)')
        srcgrp.add_argument('--stdin', action='store_true', help='Leer parche desde STDIN')
        ap_parser.add_argument('--root', default='.', help='Directorio raíz sobre el que aplicar (por defecto: .)')
        ap_parser.add_argument('--dry-run', action='store_true', help='Simula sin escribir cambios')

        # Comandos GitHub básicos
        gh_status = subparsers.add_parser(
            'gh-status', help='Muestra info del token y usuario de GitHub'
        )
        gh_gist = subparsers.add_parser(
            'gh-create-gist', help='Crea un Gist con contenido'
        )
        gsrc = gh_gist.add_mutually_exclusive_group(required=True)
        gsrc.add_argument('-f', '--file', dest='gist_file', help='Archivo a subir como Gist')
        gsrc.add_argument('--stdin', action='store_true', help='Leer contenido desde STDIN')
        gh_gist.add_argument('-n', '--name', default='snippet.txt', help='Nombre del archivo en el Gist')
        gh_gist.add_argument('-d', '--description', default='', help='Descripción del Gist')
        gh_gist.add_argument('--public', action='store_true', help='Gist público (por defecto es secreto)')

        # Comandos de auto-repo
        ss = subparsers.add_parser('self-snapshot', help='Genera y embebe un snapshot comprimido del repo actual')
        se = subparsers.add_parser('self-extract', help='Extrae el snapshot embebido a un directorio destino')
        se.add_argument('-o', '--out', default='.self_extract', help='Directorio de salida (por defecto ./.self_extract)')
        sa = subparsers.add_parser('self-analyze', help='Analiza dependencias y estructura (actual o snapshot)')
        sa.add_argument('--from', dest='source', choices=['current','embedded'], default='current', help='Fuente del análisis')
        st = subparsers.add_parser('self-test', help='Ejecuta tests en el árbol actual')
        sup = subparsers.add_parser('self-apply-patch', help='Aplica parche en copia, corre tests y si pasan, sustituye')
        grp = sup.add_mutually_exclusive_group(required=True)
        grp.add_argument('-f', '--file', dest='patch_file', help='Archivo de parche')
        grp.add_argument('--stdin', action='store_true', help='Leer parche desde STDIN')
        sup.add_argument('--use-embedded', action='store_true', help='Aplicar sobre snapshot embebido en lugar del árbol actual')

        # Web: búsqueda y fetch
        ws = subparsers.add_parser('web-search', help='Busca en la web (requiere SERPAPI_KEY o TAVILY_API_KEY)')
        ws.add_argument('-q', '--query', required=True, help='Consulta de búsqueda')
        ws.add_argument('-e', '--engine', choices=['serpapi','tavily'], help='Motor de búsqueda a usar')
        ws.add_argument('-n', '--num', type=int, default=5, help='Número de resultados (default 5)')
        wf = subparsers.add_parser('web-fetch', help='Descarga una URL y la convierte a texto')
        wf.add_argument('url', help='URL a descargar')

        # Comandos GitHub básicos
        gh_status = subparsers.add_parser(
            'gh-status', help='Muestra info del token y usuario de GitHub'
        )
        gh_gist = subparsers.add_parser(
            'gh-create-gist', help='Crea un Gist con contenido'
        )
        gsrc = gh_gist.add_mutually_exclusive_group(required=True)
        gsrc.add_argument('-f', '--file', dest='gist_file', help='Archivo a subir como Gist')
        gsrc.add_argument('--stdin', action='store_true', help='Leer contenido desde STDIN')
        gh_gist.add_argument('-n', '--name', default='snippet.txt', help='Nombre del archivo en el Gist')
        gh_gist.add_argument('-d', '--description', default='', help='Descripción del Gist')
        gh_gist.add_argument('--public', action='store_true', help='Gist público (por defecto es secreto)')

        # Comando para cambiar modelo
        switch_parser = subparsers.add_parser(
            'switch-model',
            help='Cambia el modelo AI por defecto'
        )
        switch_parser.add_argument(
            'model',
            help="'blackbox' o identificador de Blackbox (p. ej. blackboxai/openai/o1)"
        )

        # Comando para listar modelos disponibles
        list_parser = subparsers.add_parser(
            'list-models',
            help='Lista los modelos AI disponibles'
        )

        # Comando para configuración
        config_parser = subparsers.add_parser(
            'config',
            help='Muestra configuración actual'
        )

        # Herramientas SSH / despliegue
        ssh_exec = subparsers.add_parser('ssh-exec', help='Ejecuta un comando remoto via SSH')
        ssh_exec.add_argument('--host', required=True)
        ssh_exec.add_argument('--user')
        ssh_exec.add_argument('--key')
        ssh_exec.add_argument('--port', type=int, default=22)
        ssh_exec.add_argument('cmd', help='Comando remoto a ejecutar entre comillas')

        ssh_sync = subparsers.add_parser('ssh-sync', help='Sincroniza/copias archivos al remoto via SCP')
        ssh_sync.add_argument('--host', required=True)
        ssh_sync.add_argument('--user')
        ssh_sync.add_argument('--key')
        ssh_sync.add_argument('--port', type=int, default=22)
        ssh_sync.add_argument('--recursive', action='store_true')
        ssh_sync.add_argument('local')
        ssh_sync.add_argument('remote')

        deploy = subparsers.add_parser('deploy-remote', help='Despliegue remoto (Docker/Compose o sin Docker)')
        deploy.add_argument('--host', required=True)
        deploy.add_argument('--user')
        deploy.add_argument('--key')
        deploy.add_argument('--port', type=int, default=22)
        deploy.add_argument('--dir', required=True, help='Directorio del proyecto en el servidor')
        deploy.add_argument('--no-docker', dest='no_docker', action='store_true')
        deploy.add_argument('--compose', action='store_true')

        return parser

    def run_generate_tests(self, args):
        """Ejecuta el comando de generación de tests"""
        try:
            print(f"🔍 Analizando {args.file}...")
            test_file = self.test_generator.create_test_file(args.file, args.output)

            print(f"✅ Tests generados exitosamente: {test_file}")
            print(f"📊 Ejecutando tests...")

            # Ejecutar tests generados
            self.run_tests(test_file)

        except Exception as e:
            print(f"❌ Error generando tests: {str(e)}")
            return 1

        return 0

    def run_analyze_coverage(self, args):
        """Ejecuta el comando de análisis de cobertura"""
        try:
            print(f"📊 Analizando cobertura en {args.path}...")

            # Simulación de análisis de cobertura
            # En un caso real, esto ejecutaría pytest con coverage
            coverage_data = {
                'total_lines': 150,
                'covered_lines': 120,
                'coverage_percentage': 80.0,
                'missing_lines': [45, 67, 89]
            }

            report = self.coverage_analyzer.generate_coverage_report(
                coverage_data, args.format
            )

            print(report)

        except Exception as e:
            print(f"❌ Error analizando cobertura: {str(e)}")
            return 1

        return 0

    def run_ai_query(self, args):
        """Ejecuta consulta a la IA"""
        try:
            print(f"🤖 Consultando {args.model or 'modelo por defecto'}...")

            response = self.ai_orchestrator.generate_response(
                args.query,
                model_type=args.model,
                debug=getattr(args, 'debug', False)
            )

            print("\n📝 Respuesta:")
            print(response)

        except Exception as e:
            print(f"❌ Error en consulta AI: {str(e)}")
            return 1

        return 0

    def run_media(self, args):
        """Ejecuta el chat interactivo por categorías."""
        from .media import run_media_command
        try:
            run_media_command(self.ai_orchestrator)
            return 0
        except Exception as e:
            print(f"❌ Error en el comando media: {e}")
            return 1

    def _choose_model(self, strategy: str, override: Optional[str]) -> Optional[str]:
        # 1) Respeta override explícito
        if override:
            return override

        # 2) Respeta mapeos por entorno (permite fijar modelos por estrategia)
        env_map = {
            'auto': os.getenv('MODEL_FOR_AUTO'),
            'fast': os.getenv('MODEL_FOR_FAST'),
            'reasoning': os.getenv('MODEL_FOR_REASONING'),
            'code': os.getenv('MODEL_FOR_CODE'),
        }
        if env_map.get(strategy):
            return env_map[strategy]

        # 3) Construye candidatos a partir de available_models + modelo por defecto
        cfg = self.ai_orchestrator.models_config
        default_model = (
            cfg.get('models', {}).get('blackbox', {}).get('model') or 'blackbox'
        )
        avail_list = [m.get('model', '') for m in cfg.get('available_models', []) if m.get('model')]
        if default_model and default_model not in avail_list:
            avail_list.append(default_model)

        # 4) Heurísticas por estrategia con preferencias ordenadas
        prefs_map = {
            'fast': [
                'flash',
                'mini',
                'gpt-4o-mini',
                'o3-mini',
            ],
            'reasoning': [
                'claude-3.7', 'claude-3.5', 'claude',
                'o3', 'o1',
                'deepseek-r1', 'reasoning',
            ],
            'code': [
                'o1', 'gpt-4o', 'gpt-4.1',
                'mixtral', 'llama-3.1', 'qwen3',
            ],
            'auto': [],
        }

        if strategy == 'auto':
            # Prefiere el modelo por defecto configurado (ya optimizado por el orquestador)
            return default_model

        prefs = prefs_map.get(strategy, [])
        # Normaliza y puntúa candidatos según primera coincidencia en prefs
        def score(model_id: str) -> tuple:
            mid = model_id.lower()
            for i, key in enumerate(prefs):
                if key.lower() in mid:
                    return (0, i)  # preferidos
            # secundario: tokens clave genéricos
            generic = ['flash', 'mini', 'pro', 'latest']
            for j, k in enumerate(generic):
                if k in mid:
                    return (1, j)
            # fallback: lo que sea
            return (2, len(mid))

        if avail_list:
            best = sorted(avail_list, key=score)[0]
            return best

        # 5) Fallback final: None (que la orquestación use el modelo por defecto)
        return None

    def run_ai_dev(self, args):
        try:
            analysis = analyze_dependencies(Path('.').resolve())
            files = []
            for p in Path('.').rglob('*'):
                if p.is_file() and len(files) < 60 and not any(seg in {'.git','__pycache__','.venv','venv','.self_backup','htmlcov','logs'} for seg in p.parts):
                    try:
                        rel = str(p.relative_to(Path('.').resolve()))
                    except Exception:
                        rel = str(p)
                    files.append(rel)
            web_snippets = []
            if args.allow_web and (args.engine or os.getenv('WEB_SEARCH_ENGINE')) and (os.getenv('SERPAPI_KEY') or os.getenv('TAVILY_API_KEY')):
                try:
                    ws = WebSearch(engine=args.engine)
                    sr = ws.search(args.instruction, num_results=3)
                    for r in sr.get('results', [])[:3]:
                        try:
                            wf = WebFetcher()
                            page = wf.fetch(r.get('link'))
                            web_snippets.append({
                                'title': r.get('title'),
                                'url': r.get('link'),
                                'snippet': (page.get('text_stripped','')[:2000])
                            })
                        except Exception:
                            continue
                except Exception:
                    pass

            system = (
                "Eres un asistente de desarrollo. Debes devolver EXCLUSIVAMENTE un parche en formato unified diff que aplique sobre el repo actual. "
                "Usa rutas relativas, incluye hunks @@ y las líneas con +/-. No incluyas explicaciones ni markdown."
            )
            repo_summary = {
                'analysis': analysis,
                'files_sample': files[:60],
                'notes': 'Responde sólo con unified diff válido. No mezcles otros textos.'
            }
            content_user = (
                f"Instrucción: {args.instruction}\n\n"
                f"Contexto del repo (resumen JSON):\n{json_dumps(repo_summary)}\n\n"
                + (f"Recursos web:\n{json_dumps(web_snippets)}\n\n" if web_snippets else "")
                + "Genera el parche ahora."
            )
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": content_user},
            ]

            model_id = self._choose_model(args.strategy, args.model)

            patch_text = self.ai_orchestrator.generate_response(
                prompt=args.instruction,
                model_type=model_id,
                messages=messages,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
                debug=getattr(args, 'debug', False)
            )

            out_dir = Path(args.out_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            import time
            ts = time.strftime('%Y%m%d-%H%M%S')
            out_file = out_dir / f"ai-dev-{ts}.patch"
            out_file.write_text(patch_text, encoding='utf-8')
            print(f"📝 Parche propuesto: {out_file}")

            if args.apply:
                print("🔧 Aplicando parche en copia y corriendo tests...")
                class A: pass
                a = A()
                a.patch_file = str(out_file)
                a.stdin = False
                a.use_embedded = False
                return self.run_self_apply_patch(a)
            return 0
        except Exception as e:
            print(f"❌ Error en ai-dev: {e}")
            return 1

    def run_repl(self, args):
        """Chat interactivo con contexto y cambio de modelo en vivo"""
        debug = getattr(args, 'debug', False)
        history = []  # lista de mensajes estilo chat.completions
        current_model = args.model  # identificador Blackbox opcional
        if not current_model:
            try:
                current_model = (
                    self.ai_orchestrator.models_config
                    .get('models', {})
                    .get('blackbox', {})
                    .get('model')
                )
            except Exception:
                current_model = None

        # Persistencia de sesión
        session_name = args.session
        transcript_path = Path(args.transcript).expanduser() if args.transcript else None
        sessions_dir = Path.home() / '.blackbox_hybrid_tool' / 'sessions'
        session_file = None
        if session_name:
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_file = sessions_dir / f"{session_name}.json"
            if session_file.exists():
                try:
                    import json
                    data = json.loads(session_file.read_text(encoding='utf-8'))
                    history = data.get('messages', [])
                    # Si el archivo tiene modelo guardado y no se pasó por CLI, úsalo
                    if not current_model and data.get('model'):
                        current_model = data['model']
                    print(f"📂 Sesión cargada: {session_file}")
                except Exception as e:
                    print(f"⚠️  No se pudo cargar la sesión: {e}")

        def save_session():
            if not session_file:
                return
            try:
                import json, datetime
                payload = {
                    'model': current_model,
                    'messages': history,
                    'updated_at': datetime.datetime.utcnow().isoformat() + 'Z'
                }
                session_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f"💾 Sesión guardada: {session_file}")
            except Exception as e:
                print(f"⚠️  Error guardando sesión: {e}")

        def append_transcript(role: str, content: str):
            if not transcript_path:
                return
            try:
                transcript_path.parent.mkdir(parents=True, exist_ok=True)
                with open(transcript_path, 'a', encoding='utf-8') as f:
                    f.write(f"{role}: {content}\n")
            except Exception as e:
                print(f"⚠️  Error escribiendo transcript: {e}")

        print("💬 REPL de Blackbox. Comandos: /model <id>, /reset, /exit, /help")
        print("🛠️  Herramientas disponibles para el asistente: write-file, web-search, web-fetch, self-apply-patch")
        print("ℹ️  Para invocar herramientas, el asistente emitirá JSON: {\"tool\":\"<name>\", \"args\":{...}}")
        if current_model:
            print(f"➡️  Modelo inicial: {current_model}")
        if session_file:
            print(f"➡️  Sesión: {session_name} ({session_file})")
        if transcript_path:
            print(f"➡️  Transcript: {transcript_path}")

        def tool_system_prompt() -> str:
            return (
                "Tienes acceso a herramientas. Cuando necesites usarlas, responde únicamente con un objeto JSON sin texto adicional, "
                "con la forma: {\"tool\": \"<name>\", \"args\": { ... }}. NO incluyas markdown ni explicaciones.\n"
                "Herramientas:\n"
                "- write-file: args={path:str, content:str, overwrite:bool?} -> crea/sobrescribe archivo.\n"
                "- web-search: args={query:str, engine:'serpapi'|'tavily'?, num:int?} -> resultados de búsqueda.\n"
                "- web-fetch: args={url:str} -> descarga y devuelve texto procesado.\n"
                "- self-apply-patch: args={patch:str} -> aplica un unified diff en copia, corre tests y sustituye si pasan.\n"
                "Si no necesitas una herramienta, responde con texto normal."
            )

        def parse_tool_call(text: str):
            import json, re
            s = text.strip()
            # Extrae JSON puro o dentro de ```json ... ```
            m = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", s, re.I)
            if m:
                s = m.group(1)
            if s.startswith('{') and s.endswith('}'):
                try:
                    obj = json.loads(s)
                    if isinstance(obj, dict) and 'tool' in obj and 'args' in obj:
                        return obj
                except Exception:
                    return None
            return None

        def exec_tool_call(tool_obj: dict):
            import json, tempfile, subprocess, shutil
            name = tool_obj.get('tool')
            args_ = tool_obj.get('args') or {}
            try:
                if name == 'write-file':
                    dest = Path(args_.get('path', '')).expanduser()
                    content = args_.get('content', '')
                    overwrite = bool(args_.get('overwrite', False))
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    if dest.exists() and not overwrite:
                        return {"status":"error","error":"exists","path":str(dest)}
                    dest.write_text(content, encoding='utf-8')
                    return {"status":"ok","path":str(dest),"written":len(content)}
                if name == 'web-search':
                    ws = WebSearch(engine=args_.get('engine'))
                    res = ws.search(args_.get('query',''), num_results=int(args_.get('num',5)))
                    return {"status":"ok","results":res.get('results',[]),"engine":res.get('engine')}
                if name == 'web-fetch':
                    wf = WebFetcher()
                    res = wf.fetch(args_.get('url',''))
                    out = {k: (v[:4000] + '...') if isinstance(v, str) and len(v) > 4000 else v for k, v in res.items() if k in ('url','status','content_type','text_stripped')}
                    return {"status":"ok","fetch":out}
                if name == 'self-apply-patch':
                    patch_text = args_.get('patch','')
                    # Guardar temp y reutilizar rutina existente
                    with tempfile.NamedTemporaryFile('w', delete=False, encoding='utf-8', suffix='.patch') as tf:
                        tf.write(patch_text)
                        tf.flush()
                        tmpfile = tf.name
                    class A: pass
                    a = A(); a.patch_file = tmpfile; a.stdin = False; a.use_embedded = False
                    code = self.run_self_apply_patch(a)
                    try:
                        os.unlink(tmpfile)
                    except Exception:
                        pass
                    return {"status":"ok" if code==0 else "failed","exit_code":code}
                return {"status":"error","error":"unknown_tool","tool":name}
            except Exception as e:
                return {"status":"error","error":str(e)}

        def list_tools() -> str:
            # Descripción breve y esquema de args
            return "\n".join([
                "Herramientas disponibles:",
                " - write-file: args={path:str, content:str, overwrite?:bool}",
                " - web-search: args={query:str, engine?:'serpapi'|'tavily', num?:int}",
                " - web-fetch: args={url:str}",
                " - self-apply-patch: args={patch:str}",
                "Uso: /tools <name> <args_json>  |  /tools <name> (y luego ingresa JSON)",
            ])

        # Inserta mensaje system inicial con descripción de herramientas
        history.append({"role":"system","content": tool_system_prompt()})

        while True:
            try:
                user = input("You> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Fin de la sesión.")
                save_session()
                return 0

            if not user:
                continue

            if user.startswith('/'):
                cmd, *rest = user[1:].split(maxsplit=1)
                arg = rest[0] if rest else ''
                if cmd in ('exit', 'quit'):  # salir
                    print("👋 Fin de la sesión.")
                    save_session()
                    return 0
                elif cmd == 'reset':
                    history.clear()
                    print("🔄 Contexto limpiado.")
                    continue
                elif cmd == 'model':
                    if not arg:
                        print("Uso: /model <blackbox_identifier>")
                    else:
                        current_model = arg
                        print(f"✅ Modelo actualizado: {current_model}")
                    continue
                elif cmd == 'save':
                    save_session()
                    continue
                elif cmd == 'session':
                    if not arg:
                        print("Uso: /session <nombre>")
                        continue
                    # Guardar sesión actual y cambiar
                    save_session()
                    session_name = arg
                    sessions_dir.mkdir(parents=True, exist_ok=True)
                    session_file = sessions_dir / f"{session_name}.json"
                    history = []
                    if session_file.exists():
                        try:
                            import json
                            data = json.loads(session_file.read_text(encoding='utf-8'))
                            history = data.get('messages', [])
                            if data.get('model'):
                                current_model = data['model']
                            print(f"📂 Sesión cambiada y cargada: {session_file}")
                        except Exception as e:
                            print(f"⚠️  No se pudo cargar la sesión: {e}")
                    else:
                        print(f"🆕 Nueva sesión: {session_file}")
                    continue
                elif cmd == 'transcript':
                    if not arg:
                        print("Uso: /transcript <ruta>")
                        continue
                    transcript_path = Path(arg).expanduser()
                    print(f"📝 Transcript activado en: {transcript_path}")
                    continue
                elif cmd == 'tools':
                    # Manual: listar o ejecutar herramienta con args JSON
                    if not arg:
                        print(list_tools())
                        continue
                    parts = arg.split(maxsplit=1)
                    tname = parts[0]
                    args_json = parts[1] if len(parts) > 1 else ''
                    if not args_json:
                        try:
                            args_json = input("args JSON> ")
                        except (EOFError, KeyboardInterrupt):
                            print()
                            continue
                    try:
                        import json
                        targs = json.loads(args_json) if args_json.strip() else {}
                        result = exec_tool_call({"tool": tname, "args": targs})
                        print("🔧 Resultado:")
                        print(json_dumps(result))
                        # Inyectar al historial como evidencia
                        history.append({"role":"system","content": f"TOOL_RESULT {tname}: {json_dumps(result)}"})
                    except Exception as e:
                        print(f"❌ Error al ejecutar herramienta: {e}")
                    continue
                elif cmd == 'help':
                    print("Comandos: /model <id>, /reset, /save, /session <nombre>, /transcript <ruta>, /tools [<name> [args_json]], /exit, /help")
                    continue
                else:
                    print("❓ Comando no reconocido. Usa /help")
                    continue

            # Añadir mensaje del usuario al historial
            history.append({"role": "user", "content": user})
            append_transcript('You', user)

            # Generar respuesta (usa historial y modelo actual si se definió)
            # Bucle de herramienta: permite que el asistente invoque herramientas antes de la respuesta final
            tool_steps = 0
            reply = None
            while True:
                reply = self.ai_orchestrator.generate_response(
                    prompt=user,  # por compatibilidad
                    model_type=current_model,
                    messages=history,
                    debug=debug
                )
                tool_call = parse_tool_call(reply or '')
                if tool_call and tool_steps < 5:
                    result = exec_tool_call(tool_call)
                    # Registrar rastro visible y en historial
                    print(f"🔧 Tool {tool_call.get('tool')} -> {result.get('status')}")
                    history.append({"role":"assistant","content": reply})
                    history.append({"role":"system","content": f"TOOL_RESULT {tool_call.get('tool')}: {json_dumps(result)}"})
                    tool_steps += 1
                    continue
                break

            # Añadir respuesta de asistente al historial si no es error crudo
            if reply and not reply.startswith("Error en la API de Blackbox:"):
                history.append({"role": "assistant", "content": reply})

            print("AI>", reply or "<respuesta vacía>")
            append_transcript('AI', reply or '')
            # Guardado oportunista tras cada turno si hay sesión
            save_session()
        return 0

    def run_self_snapshot(self, args):
        try:
            changed, meta = ensure_embedded_snapshot(Path('.').resolve())
            if changed:
                print(f"✅ Snapshot embebido actualizado (files={meta.get('file_count')}, hash={str(meta.get('sha256'))[:8]}...)")
            else:
                print("ℹ️  Snapshot ya estaba al día")
            return 0
        except Exception as e:
            print(f"❌ Error generando snapshot: {e}")
            return 1

    def run_self_extract(self, args):
        try:
            out = Path(args.out).expanduser()
            info = extract_snapshot(out)
            print(f"✅ Extraído snapshot en: {info['path']} (files={info['meta'].get('file_count')})")
            return 0
        except Exception as e:
            print(f"❌ Error extrayendo snapshot: {e}")
            return 1

    def run_self_analyze(self, args):
        try:
            if args.source == 'embedded':
                tmp = Path('.self_extract')
                info = extract_snapshot(tmp)
                root = Path(info['path'])
            else:
                root = Path('.')
            report = analyze_dependencies(root.resolve())
            print(json_dumps(report))
            return 0
        except Exception as e:
            print(f"❌ Error analizando: {e}")
            return 1

    def run_self_test(self, args):
        try:
            return self.run_tests('tests')
        except Exception as e:
            print(f"❌ Error ejecutando pruebas: {e}")
            return 1

    def run_self_apply_patch(self, args):
        try:
            # Prepare working copy
            workdir = Path('.self_work')
            if workdir.exists():
                import shutil
                shutil.rmtree(workdir)
            if args.use_embedded:
                extract_snapshot(workdir)
            else:
                from utils.self_repo import make_snapshot
                snap = make_snapshot(Path('.').resolve())
                import tarfile, io
                with tarfile.open(fileobj=io.BytesIO(snap['data']), mode='r:gz') as tar:  # type: ignore
                    tar.extractall(workdir)

            # Read patch
            if args.stdin:
                patch_text = sys.stdin.read()
            else:
                patch_text = Path(args.patch_file).read_text(encoding='utf-8')

            # Apply patch to workdir
            res = apply_unified_diff(patch_text, workdir)
            if res.get('errors'):
                print("⚠️  Errores al aplicar parche en copia:")
                for e in res['errors']:
                    print(f" - {e.get('file')}: {e.get('error')}")
                return 2

            # Run tests inside copy (best-effort using current python path)
            print("🧪 Ejecutando pruebas en copia...")
            import subprocess
            code = subprocess.call([sys.executable, '-m', 'pytest', '-q'], cwd=str(workdir))
            if code != 0:
                print(f"❌ Pruebas fallaron en copia (exit={code}). No se aplican cambios.")
                return code

            # Backup current and replace
            bkp = backup_current(Path('.').resolve())
            replace_tree(workdir, Path('.').resolve())
            print(f"✅ Cambios aplicados. Backup: {bkp}")
            # Refresh embedded snapshot
            try:
                ensure_embedded_snapshot(Path('.').resolve())
            except Exception:
                pass
            return 0
        except Exception as e:
            print(f"❌ Error en self-apply-patch: {e}")
            return 1

    def run_web_search(self, args):
        try:
            ws = WebSearch(engine=args.engine)
            res = ws.search(args.query, num_results=args.num)
            print(json_dumps(res))
            return 0
        except Exception as e:
            print(f"❌ Error en web-search: {e}")
            return 1

    def run_web_fetch(self, args):
        try:
            wf = WebFetcher()
            res = wf.fetch(args.url)
            out = {k: (v[:2000] + '...') if isinstance(v, str) and len(v) > 2000 else v for k, v in res.items() if k in ('url','status','content_type','text_stripped')}
            print(json_dumps(out))
            return 0
        except Exception as e:
            print(f"❌ Error en web-fetch: {e}")
            return 1

    def run_write_file(self, args):
        """Crea/escribe un archivo de texto con contenido desde --content, STDIN o editor interactivo."""
        try:
            dest = Path(args.path).expanduser()
            dest.parent.mkdir(parents=True, exist_ok=True)

            if dest.exists() and not args.overwrite:
                print(f"❌ El archivo ya existe: {dest} (usa --overwrite para sobrescribir)")
                return 1

            content = None
            if args.content is not None:
                content = args.content
            elif args.stdin:
                content = sys.stdin.read()
            elif args.editor:
                import tempfile
                import subprocess
                initial = (args.content or "")
                with tempfile.NamedTemporaryFile('w+', delete=False, encoding='utf-8', suffix='.txt') as tf:
                    tf.write(initial)
                    tf.flush()
                    tmp_path = tf.name
                editor = os.environ.get('EDITOR') or 'nano'
                try_editors = [editor]
                if editor != 'nano':
                    try_editors.append('nano')
                if 'vi' not in try_editors:
                    try_editors.append('vi')
                opened = False
                for ed in try_editors:
                    try:
                        import shutil
                        if not shutil.which(ed):
                            continue
                        subprocess.run([ed, tmp_path])
                        opened = True
                        break
                    except FileNotFoundError:
                        continue
                if not opened:
                    print("❌ No se encontró un editor disponible ($EDITOR, nano o vi)")
                    return 1
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
            else:
                print("❌ Debes proporcionar contenido con --content, --stdin o --editor")
                return 1

            with open(dest, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✅ Escrito {len(content or '')} bytes en: {dest}")
            return 0
        except Exception as e:
            print(f"❌ Error escribiendo archivo: {e}")
            return 1

    def run_apply_patch(self, args):
        """Aplica un parche unified diff al filesystem."""
        try:
            if args.stdin:
                patch_text = sys.stdin.read()
            else:
                if not args.patch_file:
                    print("❌ Debes pasar --stdin o --file")
                    return 1
                patch_text = Path(args.patch_file).read_text(encoding='utf-8')

            if args.dry_run:
                patches = parse_unified_diff(patch_text)
                files = []
                for p in patches:
                    src = p.src.split()[-1]
                    dst = p.dst.split()[-1]
                    files.append({'src': src, 'dst': dst})
                print("🔎 Dry run. Archivos involucrados:")
                for f in files:
                    print(f" - {f['src']} -> {f['dst']}")
                return 0

            result = apply_unified_diff(patch_text, args.root)
            if result.get('errors'):
                print("⚠️  Errores al aplicar:")
                for e in result['errors']:
                    print(f" - {e.get('file')}: {e.get('error')}")
            if result.get('created'):
                print("🆕 Creados:")
                for p in result['created']:
                    print(f" - {p}")
            if result.get('applied'):
                print("✅ Modificados:")
                for p in result['applied']:
                    print(f" - {p}")
            if result.get('deleted'):
                print("🗑️  Eliminados:")
                for p in result['deleted']:
                    print(f" - {p}")
            return 0 if not result.get('errors') else 2
        except Exception as e:
            print(f"❌ Error aplicando parche: {e}")
            return 1

    def run_gh_status(self, args):
        try:
            gh = GitHubClient()
            me = gh.get_user()
            print("✅ GitHub token OK")
            print(f"Usuario: {me.get('login')} | ID: {me.get('id')} | Nombre: {me.get('name')}")
            return 0
        except Exception as e:
            print(f"❌ Error con GitHub: {e}")
            return 1

    def run_gh_create_gist(self, args):
        try:
            if args.stdin:
                content = sys.stdin.read()
            else:
                content = Path(args.gist_file).read_text(encoding='utf-8')
            gh = GitHubClient()
            result = gh.create_gist({args.name: content}, description=args.description, public=args.public)
            print("✅ Gist creado:")
            print(result.get('html_url') or result.get('url'))
            return 0
        except Exception as e:
            print(f"❌ Error creando Gist: {e}")
            return 1

    def run_switch_model(self, args):
        """Cambia el modelo AI por defecto"""
        try:
            # Si se pasa un identificador de Blackbox (contiene '/')
            if '/' in args.model:
                # Actualizar el identificador por defecto de Blackbox en el config
                self.ai_orchestrator.models_config.setdefault('models', {}).setdefault('blackbox', {})['model'] = args.model
                # Asegurar base_url por si falta
                self.ai_orchestrator.models_config['models']['blackbox'].setdefault(
                    'base_url', 'https://api.blackbox.ai/chat/completions'
                )
                # Mantener enabled/api_key existentes
                self.ai_orchestrator._save_config()
                print(f"✅ Identificador de Blackbox actualizado: {args.model}")
            else:
                # Mantener compatibilidad: solo 'blackbox' es válido como nombre lógico
                if args.model != 'blackbox':
                    raise ValueError("Modelo inválido. Use 'blackbox' o un identificador de Blackbox con '/'.")
                self.ai_orchestrator.switch_model(args.model)
                print(f"✅ Modelo lógico cambiado a: {args.model}")

        except Exception as e:
            print(f"❌ Error cambiando modelo: {str(e)}")
            return 1

        return 0

    def run_list_models(self, args):
        """Lista modelos disponibles"""
        models_config = self.ai_orchestrator.models_config
        current_model = models_config.get('default_model', 'auto')

        print("🤖 Modelos AI disponibles:")
        print(f"Modelo actual: {current_model}")
        print("\nModelos configurados:")

        for model_name, config in models_config.get('models', {}).items():
            status = "✅ Habilitado" if config.get('enabled', False) else "❌ Deshabilitado"
            print(f"  • {model_name}: {status}")

        return 0

    def run_config(self, args):
        """Muestra configuración actual"""
        try:
            models_config = self.ai_orchestrator.models_config

            print("⚙️  Configuración actual:")
            print(f"Modelo por defecto: {models_config.get('default_model', 'auto')}")
            print("\nModelos:")
            for model_name, config in models_config.get('models', {}).items():
                print(f"  {model_name}:")
                print(f"    Habilitado: {config.get('enabled', False)}")
                print(f"    Modelo: {config.get('model', 'N/A')}")
                print(f"    API Key: {'Configurada' if config.get('api_key') else 'No configurada'}")

        except Exception as e:
            print(f"❌ Error obteniendo configuración: {str(e)}")
            return 1

        return 0

    def run_ssh_exec(self, args):
        try:
            return run_ssh_command(args.host, args.cmd, user=args.user, key_path=args.key, port=args.port)
        except Exception as e:
            print(f"❌ Error SSH: {e}")
            return 1

    def run_ssh_sync(self, args):
        try:
            return sync_files(args.local, args.remote, args.host, user=args.user, key_path=args.key, port=args.port, recursive=args.recursive)
        except Exception as e:
            print(f"❌ Error SCP: {e}")
            return 1

    def run_deploy_remote(self, args):
        try:
            return deploy_remote(args.host, args.dir, user=args.user, key_path=args.key, port=args.port, use_docker=not args.no_docker, compose=args.compose)
        except Exception as e:
            print(f"❌ Error de despliegue: {e}")
            return 1

    def run_tests(self, test_file: str):
        """Ejecuta tests usando pytest"""
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', test_file, '-v'],
                capture_output=True,
                text=True
            )

            print("\n📊 Resultados de tests:")
            print(result.stdout)

            if result.stderr:
                print("⚠️  Advertencias:")
                print(result.stderr)

            return result.returncode

        except ImportError:
            print("⚠️  pytest no está instalado. Instalalo con: pip install pytest")
            return 1

    def run_shell(self, args):
        """Inicia una shell bash interactiva con tema CHISPART sólo para esta sesión."""
        import shutil
        import subprocess
        from pathlib import Path

        theme_path = Path(__file__).parent.parent / 'config' / 'chispart.omp.json'
        omp = shutil.which('oh-my-posh')
        logo = shutil.which('oh-my-logo')

        env = os.environ.copy()

        try:
            if not getattr(args, 'no_clear', False):
                subprocess.run(['clear'])
        except Exception:
            pass

        # Banner de inicio
        try:
            if logo:
                subprocess.run([logo, 'Chispart CLI', '--filled', 'nebula', '--letter-spacing', '0.1'])
            else:
                print("======================")
                print("   Chispart CLI 🐉   ")
                print("======================")
        except Exception:
            print("Chispart CLI")

        # Configurar prompt temporal
        if omp and theme_path.exists():
            env['PROMPT_COMMAND'] = f'PS1="$({omp} print primary --config {theme_path} --shell bash)"'
        else:
            # Fallback simple si no está oh-my-posh
            env['PS1'] = "[CHISPART \w \A]$ "

        # Lanzar bash interactivo sin cargar perfiles del usuario
        try:
            code = subprocess.call(['bash', '--noprofile', '--norc', '-i'], env=env)
            return int(code) if isinstance(code, int) else 0
        except FileNotFoundError:
            print("❌ No se encontró bash en el sistema.")
            return 1
        except Exception as e:
            print(f"❌ Error ejecutando tests: {str(e)}")
            return 1

    def run(self):
        """Ejecuta la interfaz CLI"""
        parser = self.setup_parser()
        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            return 0

        # Mapear comandos a métodos
        command_map = {
            'generate-tests': self.run_generate_tests,
            'analyze-coverage': self.run_analyze_coverage,
            'ai-query': self.run_ai_query,
            'ai-dev': self.run_ai_dev,
            'repl': self.run_repl,
            'media': self.run_media,
            'shell': self.run_shell,
            'self-snapshot': self.run_self_snapshot,
            'self-extract': self.run_self_extract,
            'self-analyze': self.run_self_analyze,
            'self-test': self.run_self_test,
            'self-apply-patch': self.run_self_apply_patch,
            'apply-patch': self.run_apply_patch,
            'write-file': self.run_write_file,
            'gh-status': self.run_gh_status,
            'gh-create-gist': self.run_gh_create_gist,
            'switch-model': self.run_switch_model,
            'list-models': self.run_list_models,
            'config': self.run_config,
            'ssh-exec': self.run_ssh_exec,
            'ssh-sync': self.run_ssh_sync,
            'deploy-remote': self.run_deploy_remote,
        }

        command_func = command_map.get(args.command)
        if command_func:
            return command_func(args)
        else:
            print(f"❌ Comando desconocido: {args.command}")
            return 1


def main():
    """Función principal"""
    cli = CLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
