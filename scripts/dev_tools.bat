@echo off
:: ========================================
:: JOBFIT AGENT - MODO DESARROLLADOR
:: ========================================
:: Script para desarrolladores con opciones avanzadas
:: ========================================

title JobFit Agent - Modo Desarrollador
color 0B
:: Asegurar que trabajamos desde el directorio del script (raíz del proyecto)
cd /d "%~dp0"

:menu
cls
echo.
echo ==========================================
echo    JOBFIT AGENT - MODO DESARROLLADOR
echo ==========================================
echo.
echo Selecciona una opción:
echo.
echo [1] 🚀 Iniciar aplicación normal
echo [2] 🧪 Ejecutar tests
echo [3] 🔧 Instalar dependencias
echo [4] 📊 Ver estado del proyecto
echo [5] 📝 Generar requirements actualizado
echo [6] 🔄 Reiniciar entorno virtual
echo [0] ❌ Salir
echo.
echo ==========================================

set /p choice="Ingresa tu opción (0-6): "

if "%choice%"=="1" goto start_app
if "%choice%"=="2" goto run_tests
if "%choice%"=="3" goto install_deps
if "%choice%"=="4" goto project_status
if "%choice%"=="5" goto generate_requirements
if "%choice%"=="6" goto reset_venv
if "%choice%"=="0" goto exit

echo Opción inválida. Presiona cualquier tecla...
pause >nul
goto menu

:start_app
echo.
echo 🚀 Iniciando JobFit Agent...
call venv\Scripts\activate.bat
python main.py
pause
goto menu

:run_tests
echo.
echo 🧪 Ejecutando tests...
	call venv\Scripts\activate.bat
	echo.
	echo 🧪 Ejecutando test suite con pytest...
	
	:: Preferir el pytest del entorno activo usando -m
	python -m pytest -q
	
	echo.
	echo ✅ Tests completados
	pause
	goto menu

:install_deps
echo.
echo 📦 Instalando dependencias...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo ✅ Dependencias instaladas
pause
goto menu

:project_status
echo.
echo 📊 Estado del proyecto:
echo.
echo Estructura de carpetas:
dir /b src
echo.
call venv\Scripts\activate.bat
echo Paquetes instalados:
pip list | findstr "gradio\|torch"
echo.
echo Archivos de configuración:
if exist ".env" (echo ✅ .env encontrado) else (echo ❌ .env no encontrado)
if exist "requirements.txt" (echo ✅ requirements.txt encontrado) else (echo ❌ requirements.txt no encontrado)
echo.
pause
goto menu

:generate_requirements
echo.
echo 📝 Generando requirements actualizado...
call venv\Scripts\activate.bat
pip freeze > requirements_generated.txt
echo ✅ Archivo generado: requirements_generated.txt
pause
goto menu

:reset_venv
echo.
echo 🔄 ¿Estás seguro de que quieres reiniciar el entorno virtual?
echo Esto eliminará todas las dependencias instaladas.
set /p confirm="(y/N): "
if /i not "%confirm%"=="y" goto menu

echo Eliminando entorno virtual...
rmdir /s /q venv
echo Creando nuevo entorno virtual...
python -m venv venv
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
echo ✅ Entorno virtual reiniciado
pause
goto menu

:exit
echo.
echo 👋 ¡Hasta luego!
exit /b 0