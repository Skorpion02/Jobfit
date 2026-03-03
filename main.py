#!/usr/bin/env python3
"""
JobFit Agent - Archivo Principal
Agente Inteligente para Auditoría de Ofertas y Adaptación de CV

Autor: Skorpion02
Fecha: 2024-09-23
"""

import sys
import os
import argparse
import logging

from pathlib import Path

# Añadir src al path para imports
sys.path.append(str(Path(__file__).parent / "src"))

# --- Crear directorios necesarios antes de configurar logging ---
def setup_directories():
    """Crea directorios necesarios si no existen"""
    directories = [
        'data/examples',
        'data/templates',
        'data/temp',
        'logs',
        'exports'
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

setup_directories()

# Configurar logging con UTF-8 para soportar emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/jobfit.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Configurar el StreamHandler para usar UTF-8 en Windows
for handler in logging.root.handlers:
    if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except:
                pass  # Si falla, continuar sin UTF-8 en consola

logger = logging.getLogger(__name__)


def make_serializable(obj):
    """Recursively convert numpy types and other non-JSON-serializable
    objects into Python built-ins so json.dump won't fail.
    """
    try:
        import numpy as _np
    except Exception:
        _np = None

    # Recursive converter
    def _convert(o):
        # dict
        if isinstance(o, dict):
            return {k: _convert(v) for k, v in o.items()}
        # list/tuple
        if isinstance(o, (list, tuple)):
            return [_convert(v) for v in o]
        # numpy scalar
        if _np is not None and isinstance(o, _np.generic):
            try:
                return o.item()
            except Exception:
                return o.tolist() if hasattr(o, 'tolist') else str(o)
        # numpy arrays
        if _np is not None and isinstance(o, _np.ndarray):
            return o.tolist()
        # sets
        if isinstance(o, set):
            return [_convert(v) for v in o]
        # bytes
        if isinstance(o, (bytes, bytearray)):
            try:
                return o.decode('utf-8')
            except Exception:
                return str(o)
        # objects with tolist
        if hasattr(o, 'tolist') and not isinstance(o, str):
            try:
                return o.tolist()
            except Exception:
                pass
        return o

    return _convert(obj)

def check_dependencies():
    """Verifica que todas las dependencias estén instaladas"""
    # Mapeo de nombre de paquete pip -> nombre de importación
    package_mapping = {
        'gradio': 'gradio',
        'sentence_transformers': 'sentence_transformers',
        'python-docx': 'docx',
        'requests': 'requests',
        'beautifulsoup4': 'bs4',
        'PyPDF2': 'PyPDF2',
        'pydantic': 'pydantic',
        'scikit-learn': 'sklearn',
        'numpy': 'numpy',
    }
    
    missing_packages = []
    
    for pip_name, import_name in package_mapping.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(pip_name)
    
    if missing_packages:
        logger.error(f"Faltan dependencias: {', '.join(missing_packages)}")
        logger.error("Ejecuta: pip install -r requirements.txt")
        return False
    
    logger.info("Todas las dependencias están instaladas")
    return True


def load_environment():
    """Carga variables de entorno desde .env"""
    try:
        from dotenv import load_dotenv
        env_file = Path('.env')
        
        if env_file.exists():
            load_dotenv(env_file)
            logger.info("Variables de entorno cargadas desde .env")
        else:
            logger.warning("Archivo .env no encontrado. Usando configuración por defecto")
            
            # Crear .env de ejemplo
            example_env = """# JobFit Agent - Variables de Entorno

# API Keys (opcional)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# Configuración de modelos
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=gpt-4o-mini

# Configuración de scraping
SCRAPING_TIMEOUT=30
MAX_RETRIES=3
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36

# Límites de procesamiento
MAX_CV_SIZE_MB=10
MAX_JOB_DESCRIPTION_LENGTH=10000

# Thresholds de matching
SEMANTIC_SIMILARITY_THRESHOLD=0.7
EXACT_MATCH_THRESHOLD=0.9

# Configuración de exportación
EXPORT_FORMAT=docx
TEMPLATE_PATH=data/templates/
TEMP_PATH=data/temp/

# Debug
JOBFIT_DEBUG=false
"""
            
            with open('.env.example', 'w', encoding='utf-8') as f:
                f.write(example_env)
            
            logger.info("Creado archivo .env.example - cópialo a .env y configúralo")
    
    except ImportError:
        logger.warning("python-dotenv no instalado. Variables de entorno no cargadas")

def validate_configuration():
    """Valida la configuración antes de iniciar"""
    try:
        from config.settings import settings
        # Verificar configuración crítica
        if not settings.embedding_model:
            logger.error("EMBEDDING_MODEL no configurado")
            return False
        # Verificar espacio en disco
        import shutil
        free_space_gb = shutil.disk_usage('.').free / (1024**3)
        if free_space_gb < 2:
            logger.warning(f"Poco espacio en disco: {free_space_gb:.1f}GB")
        # Verificar memoria
        try:
            import psutil
            memory_gb = psutil.virtual_memory().total / (1024**3)
            if memory_gb < 4:
                logger.warning(f"Memoria limitada: {memory_gb:.1f}GB")
        except ImportError:
            pass
        logger.info("Configuración validada")
        return True
    except Exception as e:
        logger.error(f"Error validando configuración: {e}")
        return False

def run_gradio_app(args):
    """Ejecuta la aplicación Gradio"""
    try:
        from interface.gradio_app import JobFitApp
        logger.info("Iniciando JobFit Agent...")
        # Crear instancia de la aplicación
        app = JobFitApp()
        interface = app.create_interface()
        
        # Try multiple ports starting from the specified port
        ports_to_try = [args.port, args.port + 1, args.port + 2, args.port + 3, args.port + 4]
        
        successful_port = None
        for port in ports_to_try:
            try:
                # Configurar parámetros de lanzamiento
                launch_kwargs = {
                    'server_name': args.host,
                    'server_port': port,
                    'share': args.share,
                    'debug': args.debug,
                    'show_error': True,
                    'quiet': False
                }
                
                # Mensaje de inicio
                logger.info("=" * 60)
                logger.info("JOBFIT AGENT INICIADO")
                logger.info("=" * 60)
                logger.info(f"URL Local: http://{args.host}:{port}")
                if args.share:
                    logger.info("URL Pública se generará automáticamente")
                logger.info("Funcionalidades disponibles:")
                logger.info("   - Auditoría de ofertas de trabajo")
                logger.info("   - Score de realismo (0-100)")
                logger.info("   - Adaptación inteligente de CV")
                logger.info("   - Exportación en DOCX")
                logger.info("=" * 60)
                
                # Lanzar aplicación
                interface.launch(**launch_kwargs)
                successful_port = port
                break
                
            except Exception as e:
                if "Cannot find empty port" in str(e) and port != ports_to_try[-1]:
                    logger.warning(f"Puerto {port} ocupado, probando puerto {port + 1}...")
                    continue
                else:
                    raise e
        
        if successful_port is None:
            raise Exception("No se pudo encontrar un puerto disponible en el rango especificado")
            
    except KeyboardInterrupt:
        logger.info("\nAplicación cerrada por el usuario")
    except Exception as e:
        logger.error(f"Error ejecutando aplicación: {e}")
        raise

def run_cli_mode(args):
    """Ejecuta en modo línea de comandos"""
    try:
        from src.scraper.job_scraper import JobScraper
        from src.auditor.realism_scorer import RealismScorer
        from src.extractor.job_parser import JobParser
        from src.extractor.cv_parser import CVParser
        from src.matcher.semantic_matcher import SemanticMatcher
        from src.generator.cv_adapter import CVAdapter

        logger.info("Ejecutando en modo CLI...")

        # Inicializar componentes
        scraper = JobScraper()
        scorer = RealismScorer()
        job_parser = JobParser()
        cv_parser = CVParser()
        matcher = SemanticMatcher()
        adapter = CVAdapter()

        results = {}

        # 1. Procesar oferta de trabajo
        if args.job_url:
            logger.info(f"Scraping oferta: {args.job_url}")
            job_text = scraper.scrape_any_job_offer(args.job_url)
            if job_text:
                job_data = job_parser.extract_job_data(job_text)
                # Defensive normalization: ensure lists/strings exist
                if job_data is None:
                    job_data = {}
                if not isinstance(job_data.get('must_have'), list):
                    job_data['must_have'] = job_data.get('must_have') or []
                if not isinstance(job_data.get('nice_to_have'), list):
                    job_data['nice_to_have'] = job_data.get('nice_to_have') or []
                if not isinstance(job_data.get('raw_text'), str):
                    job_data['raw_text'] = job_text
                audit_result = scorer.calculate_realism_score(job_data)
                results['job_data'] = job_data
                results['audit'] = audit_result
                logger.info(f"Score de realismo: {audit_result['realism_score']}/100")
                logger.info(f"Titulo: {job_data.get('title', 'N/A')}")
                logger.info(f"Ubicacion: {job_data.get('location', 'N/A')}")
                # Guardar JSON de la oferta
                import json
                with open('exports/job_analysis.json', 'w', encoding='utf-8') as f:
                    json.dump(make_serializable({
                        'job_data': job_data,
                        'audit_result': audit_result
                    }), f, indent=2, ensure_ascii=False)
                logger.info("Analisis guardado en exports/job_analysis.json")
            else:
                logger.error("No se pudo extraer texto de la oferta (¿URL valida y publica?)")
                return

        # 2. Procesar CV si se proporciona
        if args.cv_path and 'job_data' in results:
            logger.info(f"Procesando CV: {args.cv_path}")
            from pathlib import Path
            if not Path(args.cv_path).exists():
                logger.error(f"Archivo CV no encontrado: {args.cv_path}")
                return
            # Parsear CV
            file_extension = Path(args.cv_path).suffix[1:].lower()
            cv_data = cv_parser.parse_cv(args.cv_path, file_extension)
            # Defensive normalization to avoid NoneType iteration errors
            if cv_data is None:
                cv_data = {}

            # Ensure lists for sections
            if not isinstance(cv_data.get('experience'), list):
                cv_data['experience'] = cv_data.get('experience') or []
            if not isinstance(cv_data.get('education'), list):
                cv_data['education'] = cv_data.get('education') or []
            if not isinstance(cv_data.get('projects'), list):
                cv_data['projects'] = cv_data.get('projects') or []

            # Normalize skills into a dict with 'technical' and 'other'
            skills_field = cv_data.get('skills')
            if isinstance(skills_field, list):
                cv_data['skills'] = {'technical': skills_field, 'other': []}
            elif isinstance(skills_field, dict):
                tech = skills_field.get('technical') or []
                other = skills_field.get('other') or []
                if isinstance(tech, str):
                    tech = [tech]
                if isinstance(other, str):
                    other = [other]
                cv_data['skills'] = {'technical': tech, 'other': other}
            else:
                cv_data['skills'] = {'technical': [], 'other': []}

            # Ensure raw_text
            if not isinstance(cv_data.get('raw_text'), str):
                cv_data['raw_text'] = ''

            # Realizar matching
            requirements = (results['job_data'].get('must_have', []) +
                            results['job_data'].get('nice_to_have', []))
            # Construir texto concatenado del CV para el matcher
            cv_text = ' '.join([
                ' '.join([str(exp) for exp in cv_data.get('experience', [])]),
                ' '.join(cv_data.get('skills', {}).get('technical', [])),
                ' '.join([str(proj) for proj in cv_data.get('projects', [])]),
                ' '.join([str(edu) for edu in cv_data.get('education', [])])
            ])

            # Run matching and adaptation inside try/except to catch unexpected types
            try:
                matching_results = matcher.match_requirements_to_cv(requirements, cv_text)
                # Adaptar CV
                adapted_cv = adapter.adapt_cv(cv_data, results['job_data'], matching_results)
            except Exception as e:
                logger.error(f"Error procesando matching/adaptación: {e}")
                logger.debug("CV data keys: %s", list(cv_data.keys()))
                return
            # Exportar CV adaptado
            output_path = f"exports/cv_adaptado_{args.output_suffix or 'cli'}.docx"
            adapter.export_to_docx(adapted_cv, output_path)
            results['cv_data'] = cv_data
            results['matching'] = matching_results
            results['adapted_cv'] = adapted_cv
            # SemanticMatcher devuelve 'coverage_percentage' en porcentaje
            coverage_pct = matching_results.get('coverage_percentage', 0.0)
            logger.info(f"Cobertura de requisitos: {coverage_pct:.1f}%")
            logger.info(f"Requisitos cubiertos: {len(matching_results.get('matches', []))}")
            logger.info(f"Requisitos faltantes: {len(matching_results.get('missing_requirements', []))}")
            logger.info(f"CV adaptado guardado en: {output_path}")
            # Guardar reporte completo
            import json
            with open('exports/matching_report.json', 'w', encoding='utf-8') as f:
                json.dump(make_serializable({
                    'matching_results': matching_results,
                    'adaptation_notes': adapted_cv.get('adaptation_notes', {})
                }), f, indent=2, ensure_ascii=False)
            logger.info("Reporte de matching guardado en exports/matching_report.json")

        logger.info("Procesamiento CLI completado")

    except Exception as e:
        logger.error(f"Error en modo CLI: {e}")
        raise

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description="JobFit Agent - Auditoría de Ofertas y Adaptación de CV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:

# Modo interfaz web (por defecto)
python main.py

# Modo interfaz con configuración personalizada
python main.py --host 0.0.0.0 --port 8080 --share

# Modo línea de comandos
python main.py --cli --job-url "https://ejemplo.com/oferta" --cv-path "mi_cv.pdf"

# Lanzar notebook de demostración
python main.py --notebook

# Solo auditar una oferta
python main.py --cli --job-url "https://ejemplo.com/oferta"

# Mostrar información del sistema
python main.py --system-info
        """
    )
    
    # Argumentos generales
    parser.add_argument(
        '--mode', 
        choices=['gradio', 'cli', 'notebook'], 
        default='gradio',
        help='Modo de ejecución (default: gradio)'
    )
    
    parser.add_argument(
        '--debug', 
        action='store_true',
        help='Activar modo debug'
    )
    
    parser.add_argument(
        '--system-info', 
        action='store_true',
        help='Mostrar información del sistema y salir'
    )
    
    # Argumentos para modo Gradio
    gradio_group = parser.add_argument_group('Opciones Gradio')
    gradio_group.add_argument(
        '--host', 
        default='127.0.0.1',
        help='Host para servir la aplicación (default: 127.0.0.1)'
    )
    
    gradio_group.add_argument(
        '--port', 
        type=int, 
        default=7860,
        help='Puerto para servir la aplicación (default: 7860)'
    )
    
    gradio_group.add_argument(
        '--share', 
        action='store_true',
        help='Crear enlace público compartible'
    )
    
    # Argumentos para modo CLI
    cli_group = parser.add_argument_group('Opciones CLI')
    cli_group.add_argument(
        '--cli', 
        action='store_true',
        help='Ejecutar en modo línea de comandos'
    )
    
    cli_group.add_argument(
        '--job-url',
        help='URL de la oferta de trabajo a analizar'
    )
    
    cli_group.add_argument(
        '--cv-path',
        help='Ruta al archivo CV (PDF, DOCX, TXT)'
    )
    
    cli_group.add_argument(
        '--output-suffix',
        help='Sufijo para archivos de salida'
    )
    
    # Argumentos para notebook
    parser.add_argument(
        '--notebook', 
        action='store_true',
        help='Lanzar Jupyter notebook de demostración'
    )
    
    args = parser.parse_args()
    
    # Configurar nivel de logging
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        os.environ['JOBFIT_DEBUG'] = 'true'
    
    try:
        # Mostrar información del sistema si se solicita
        if args.system_info:
            print_system_info()
            return
        
        # Verificaciones iniciales
        logger.info("Verificando dependencias...")
        if not check_dependencies():
            sys.exit(1)
        
        logger.info("Configurando directorios...")
        setup_directories()
        
        logger.info("Cargando configuración...")
        load_environment()
        
        logger.info("Validando configuración...")
        if not validate_configuration():
            logger.error("Configuración inválida. Revisa el archivo .env")
            sys.exit(1)
        
        # Determinar modo de ejecución
        if args.cli or args.job_url:
            run_cli_mode(args)
        elif args.notebook:
            run_notebook_mode()
        else:
            run_gradio_app(args)
    
    except KeyboardInterrupt:
        logger.info("\nPrograma interrumpido por el usuario")
    except Exception as e:
        logger.error(f"Error crítico: {e}")
        if args.debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()