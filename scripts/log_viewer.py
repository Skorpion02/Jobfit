#!/usr/bin/env python3
"""
Visor de Logs en Tiempo Real para JobFit
Muestra los logs de forma continua y con colores
"""

import sys
import os
from pathlib import Path
import time

# Añadir src al path
sys.path.append(str(Path(__file__).parent.parent))

# Colores ANSI para terminal Windows
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    # Colores de texto
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GRAY = '\033[90m'

def colorize_line(line: str) -> str:
    """Colorea una línea según su contenido"""
    line_lower = line.lower()
    
    # Niveles de log
    if 'error' in line_lower or '❌' in line:
        return f"{Colors.RED}{line}{Colors.RESET}"
    elif 'warning' in line_lower or '⚠️' in line:
        return f"{Colors.YELLOW}{line}{Colors.RESET}"
    elif 'info' in line_lower or '✅' in line or '🤖' in line:
        return f"{Colors.GREEN}{line}{Colors.RESET}"
    elif 'debug' in line_lower:
        return f"{Colors.GRAY}{line}{Colors.RESET}"
    
    # Palabras clave
    if 'lm studio' in line_lower or 'lmstudio' in line_lower:
        return f"{Colors.CYAN}{Colors.BOLD}{line}{Colors.RESET}"
    elif 'conectado' in line_lower or 'exitosamente' in line_lower:
        return f"{Colors.GREEN}{Colors.BOLD}{line}{Colors.RESET}"
    elif '=====' in line:
        return f"{Colors.BLUE}{line}{Colors.RESET}"
    
    return line

def tail_log_file(log_path: str, num_lines: int = 50):
    """Muestra las últimas líneas del log y sigue mostrando nuevas"""
    
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}    🔍 VISOR DE LOGS EN TIEMPO REAL - JobFit Agent{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*80}{Colors.RESET}\n")
    print(f"{Colors.WHITE}📂 Archivo: {log_path}{Colors.RESET}")
    print(f"{Colors.WHITE}⌚ Presiona Ctrl+C para salir{Colors.RESET}\n")
    print(f"{Colors.BLUE}{'─'*80}{Colors.RESET}\n")
    
    try:
        # Leer las últimas líneas existentes
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Mostrar últimas N líneas
                for line in lines[-num_lines:]:
                    print(colorize_line(line.rstrip()))
        
        # Seguir el archivo en tiempo real
        with open(log_path, 'r', encoding='utf-8') as f:
            # Ir al final del archivo
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    print(colorize_line(line.rstrip()))
                else:
                    time.sleep(0.1)  # Esperar 100ms antes de verificar de nuevo
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}👋 Visor de logs cerrado{Colors.RESET}\n")
    except FileNotFoundError:
        print(f"\n{Colors.RED}❌ Error: No se encontró el archivo de log{Colors.RESET}")
        print(f"{Colors.YELLOW}💡 Ejecuta la aplicación primero para generar logs{Colors.RESET}\n")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Error: {e}{Colors.RESET}\n")

def show_log_summary(log_path: str):
    """Muestra un resumen de los logs recientes"""
    if not os.path.exists(log_path):
        print(f"{Colors.YELLOW}⚠️ No hay logs disponibles todavía{Colors.RESET}\n")
        return
    
    with open(log_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    errors = sum(1 for line in lines if 'ERROR' in line)
    warnings = sum(1 for line in lines if 'WARNING' in line)
    lmstudio_mentions = sum(1 for line in lines if 'LM Studio' in line or 'lmstudio' in line.lower())
    
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}    📊 RESUMEN DE LOGS{Colors.RESET}")
    print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")
    print(f"  📝 Total de líneas: {total_lines}")
    print(f"  {Colors.RED}❌ Errores: {errors}{Colors.RESET}")
    print(f"  {Colors.YELLOW}⚠️ Advertencias: {warnings}{Colors.RESET}")
    print(f"  {Colors.CYAN}🤖 Menciones LM Studio: {lmstudio_mentions}{Colors.RESET}")
    print(f"\n{Colors.CYAN}{'='*60}{Colors.RESET}\n")

if __name__ == "__main__":
    # Habilitar colores ANSI en Windows
    os.system('')
    
    log_path = Path(__file__).parent.parent / "logs" / "jobfit.log"
    
    import argparse
    parser = argparse.ArgumentParser(description='Visor de logs de JobFit')
    parser.add_argument('-n', '--lines', type=int, default=50, 
                       help='Número de líneas históricas a mostrar (default: 50)')
    parser.add_argument('-s', '--summary', action='store_true',
                       help='Mostrar solo un resumen estadístico')
    
    args = parser.parse_args()
    
    if args.summary:
        show_log_summary(str(log_path))
    else:
        tail_log_file(str(log_path), args.lines)
