@echo off
:: ========================================
:: JOBFIT AGENT - INSTALADOR ROBUSTO
:: ========================================
:: Instalación paso a paso con resolución de conflictos
:: ========================================

title JobFit Agent - Instalador
color 0C

echo.
echo ==========================================
echo    JOBFIT AGENT - INSTALACIÓN ROBUSTA
echo ==========================================
echo    🔧 Configurando entorno paso a paso...
echo ==========================================
echo.

:: Cambiar al directorio del proyecto
cd /d "%~dp0"

:: 1. Verificar Python
echo 🐍 Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado
    echo 💡 Instala Python 3.8+ desde https://python.org
    pause
    exit /b 1
)

python --version
echo ✅ Python encontrado
echo.

:: 2. Crear/verificar entorno virtual
echo 🏗️ Configurando entorno virtual...
if not exist "venv\" (
    echo 📝 Creando entorno virtual...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Error al crear entorno virtual
        pause
        exit /b 1
    )
    echo ✅ Entorno virtual creado
) else (
    echo ✅ Entorno virtual existente encontrado
)
echo.

:: 3. Activar entorno virtual
echo 🔧 Activando entorno virtual...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Error al activar entorno virtual
    pause
    exit /b 1
)
echo ✅ Entorno virtual activado
echo.

:: 4. Actualizar pip
echo 📦 Actualizando pip...
python -m pip install --upgrade pip --quiet
echo ✅ Pip actualizado
echo.

:: 5. Instalar dependencias por categorías (más robusto)
echo 🔄 Instalando dependencias por categorías...

echo   📚 Instalando dependencias básicas...
pip install python-dotenv tqdm loguru --quiet
if errorlevel 1 echo ⚠️ Warning: Error en dependencias básicas

echo   🌐 Instalando framework web...
pip install gradio --quiet
if errorlevel 1 echo ⚠️ Warning: Error en Gradio

echo   🤖 Instalando cliente LM Studio (OpenAI compatible)...
pip install openai --quiet
if errorlevel 1 echo ⚠️ Warning: Error en OpenAI (opcional)

echo   📊 Instalando procesamiento de datos...
pip install pandas numpy scikit-learn --quiet
if errorlevel 1 echo ⚠️ Warning: Error en dependencias de datos

echo   📄 Instalando procesamiento de documentos...
pip install python-docx PyPDF2 --quiet
if errorlevel 1 echo ⚠️ Warning: Error en dependencias de documentos

echo   🌐 Instalando web scraping...
pip install requests beautifulsoup4 --quiet
if errorlevel 1 echo ⚠️ Warning: Error en dependencias de scraping

echo   🧠 Instalando IA/NLP (esto puede tomar tiempo)...
pip install sentence-transformers --quiet
if errorlevel 1 echo ⚠️ Warning: Error en sentence-transformers

echo ✅ Instalación completada
echo.

:: 6. Verificar instalación
echo 🔍 Verificando instalación...
echo Verificando componentes críticos...

python -c "import gradio; print('✅ Gradio:', gradio.__version__)" 2>nul || echo "❌ Gradio no disponible"
python -c "import openai; print('✅ OpenAI disponible')" 2>nul || echo "⚠️ OpenAI no disponible (funcionará en modo fallback)"
python -c "import sentence_transformers; print('✅ Sentence Transformers disponible')" 2>nul || echo "⚠️ Sentence Transformers no disponible"
python -c "from docx import Document; print('✅ python-docx disponible')" 2>nul || echo "⚠️ python-docx no disponible"

echo.

:: 7. Configurar archivo .env si no existe
if not exist ".env" (
    echo 🔧 Creando archivo de configuración...
    copy .env.example .env >nul 2>&1
    if exist ".env" (
        echo ✅ Archivo .env creado desde .env.example
    ) else (
        echo ⚠️ No se pudo crear .env automáticamente
        echo 💡 Copia manualmente .env.example a .env si necesitas configuración personalizada
    )
) else (
    echo ✅ Archivo .env ya existe
)
echo.

:: 8. Test rápido del sistema
echo 🧪 Probando el sistema...
echo Ejecutando test básico...

python scripts\check_env.py 2>nul || echo "⚠️ Warning: Error en test básico (ver salida)"

echo.

:: 9. Resumen final
echo ==========================================
echo    INSTALACIÓN COMPLETADA
echo ==========================================
echo.
echo 📋 RESUMEN:
echo   ✅ Entorno virtual configurado
echo   ✅ Dependencias instaladas (con posibles warnings)
echo   ✅ Configuración básica lista
echo.
echo 🚀 PRÓXIMOS PASOS:
echo   1. Ejecutar: start_jobfit.bat
echo   2. (Opcional) Instalar LM Studio desde https://lmstudio.ai
echo   3. (Opcional) Cargar un modelo en LM Studio (ej: llama-3)
echo.
echo 🔧 HERRAMIENTAS DISPONIBLES:
echo   • start_jobfit.bat - Lanzar aplicación
echo   • dev_tools.bat - Panel de desarrollador
echo   • tests\ - Suite de pruebas
echo.
echo ==========================================
pause