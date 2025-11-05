@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo ==============================================
echo  Preparando entorno para Arqueo de Caja (Flask)
echo ==============================================

:: Verificar que Python esté instalado
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo [ERROR] Python no encontrado en PATH.
  echo Instala Python 3.9+ y vuelve a ejecutar este archivo.
  pause
  exit /b 1
)

:: Crear entorno virtual si no existe
if not exist ".venv\Scripts\python.exe" (
  echo Creando entorno virtual en .venv ...
  python -m venv .venv
)

echo Actualizando pip e instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

:: Inicializar la base de datos (crea arqueo.db si no existe)
echo Inicializando base de datos...
".venv\Scripts\python.exe" init_db.py

echo.
echo Listo. Para iniciar la aplicación ejecuta: iniciar_app.bat
pause
endlocal