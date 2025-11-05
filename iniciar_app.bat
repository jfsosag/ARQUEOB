@echo off
setlocal
cd /d "%~dp0"
echo ==============================================
echo  Iniciando Arqueo de Caja (Flask)
echo ==============================================

:: Verificar entorno virtual
if not exist ".venv\Scripts\python.exe" (
  echo [AVISO] No se encontró el entorno .venv.
  echo Ejecuta primero: instalar.bat
  pause
  exit /b 1
)

:: Opcional: abrir el navegador
start "" http://127.0.0.1:5000

:: Variables de entorno (modo desarrollo)
set FLASK_ENV=development
set FLASK_DEBUG=1

".venv\Scripts\python.exe" app.py

endlocal