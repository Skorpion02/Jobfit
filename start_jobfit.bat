@echo off
:: ===================================# Instalar/actualizar dependencias
echo 📦 Verificando e instalando dependencias...
    :: Asegurar directorio del script
    cd /d "%~dp0"
    
    python -m pip install --upgrade pip --quiet
    python -m pip install -r requirements.txt --upgrade

if errorlevel 1 (
    echo ❌ Error al instalar dependencias
    echo 💡 Intentando instalación más permisiva...
    pip install -r requirements.txt --upgrade --force-reinstall
    if errorlevel 1 (
        echo ❌ Error persistente. Verifica requirements.txt
        echo 💡 Puedes continuar - el sistema puede funcionar con dependencias parciales
        echo.
        choice /C YN /M "¿Continuar de todos modos (Y/N)?"
        if errorlevel 2 exit /b 1
    )
)

:: ========================================
:: JOBFIT AGENT - LAUNCHER AUTOMATIZADO
:: ========================================

title JobFit Agent - Iniciando...
color 0A

echo.
echo ==========================================
echo    JOBFIT AGENT - SISTEMA AUTOMATIZADO
echo ==========================================
echo    🚀 Iniciando entorno de desarrollo...
echo ==========================================
echo.

:: Cambiar al directorio del proyecto
cd /d "%~dp0"

:: Verificar si existe el entorno virtual
if not exist "venv\" (
    echo ❌ ERROR: No se encontro el entorno virtual 'venv'
    echo.
    echo 📝 Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Error al crear el entorno virtual
        pause
        exit /b 1
    )
    echo ✅ Entorno virtual creado exitosamente
    echo.
)

:: Activar entorno virtual
echo 🔧 Activando entorno virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Error al activar el entorno virtual
    pause
    exit /b 1
)

echo ✅ Entorno virtual activado: %VIRTUAL_ENV%
echo.

:: Instalar/actualizar dependencias
echo 📦 Verificando e instalando dependencias...
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo ❌ Error al instalar dependencias
    echo 💡 Intenta ejecutar manualmente: pip install -r requirements.txt
    pause
    exit /b 1
)

echo ✅ Dependencias instaladas correctamente
echo.

:: Configurar variables de entorno si existe .env
if exist ".env" (
    echo 🔧 Cargando configuración desde .env...
    echo ✅ Archivo de configuración encontrado
) else (
    echo ⚠️  Archivo .env no encontrado
    echo 💡 El sistema usará configuración por defecto
)

echo.
echo ==========================================
echo    INICIANDO JOBFIT AGENT...
echo ==========================================
echo.
echo 🌐 La aplicación se abrirá en: http://localhost:7860
echo 🔄 Puerto alternativo si ocupado: 7861-7864
echo.
echo 📋 FUNCIONALIDADES DISPONIBLES:
echo    • Auditoría inteligente de ofertas de trabajo
echo    • Score de realismo automatizado (0-100)
echo    • Adaptación profesional de CV
echo    • Exportación en formato DOCX corporativo
echo.
echo 🛑 Para detener el servidor: Ctrl+C
echo ==========================================
echo.

:: Cambiar título y ejecutar aplicación
title JobFit Agent - EJECUTANDO en http://localhost:7860
python main.py

:: Si el script termina, mostrar mensaje
echo.
echo ==========================================
echo    JOBFIT AGENT FINALIZADO
echo ==========================================
echo.
pause