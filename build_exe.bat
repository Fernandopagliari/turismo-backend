@echo off
title Constructor de SistemaTurismo.exe - Estructura Completa
echo ===============================================
echo    GENERADOR DE EJECUTABLE - SISTEMA COMPLETO
echo ===============================================
echo.

REM Cambiar al directorio del script
cd /d "%~dp0"

REM Verificar que Python esté instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERROR: Python no encontrado en el sistema.
    echo    Instale Python 3.8+ y asegúrese de que esté en el PATH.
    pause
    exit /b 1
)

REM Verificar que PyInstaller esté instalado
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo ❌ PyInstaller no encontrado. Instalando...
    pip install pyinstaller
    if errorlevel 1 (
        echo ❌ Error instalando PyInstaller.
        pause
        exit /b 1
    )
)

REM Verificar archivos esenciales
if not exist "main.py" (
    echo ❌ ERROR: No se encuentra main.py
    pause
    exit /b 1
)

if not exist "interfaz\icono.ico" (
    echo ⚠️  Advertencia: No se encuentra icono.ico
    echo    Creando icono temporal...
    python -c "from PIL import Image, ImageDraw; img = Image.new('RGB', (256, 256), color='blue'); draw = ImageDraw.Draw(img); draw.ellipse([64, 64, 192, 192], fill='white'); img.save('interfaz/icono.ico', format='ICO')" 2>nul || echo    No se pudo crear icono, se usará por defecto.
)

echo ✅ Verificaciones completadas.
echo.

REM Limpiar builds anteriores
echo 🧹 Limpiando builds anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "SistemaTurismo.spec" del "SistemaTurismo.spec"
if exist "SistemaTurismo.exe" del "SistemaTurismo.exe"

REM Instalar dependencias necesarias
echo 📦 Instalando/verificando dependencias...
pip install -r requirements.txt

REM Generar el ejecutable con TODOS los archivos necesarios
echo 🏗️  Generando SistemaTurismo.exe...
echo    Esto puede tomar varios minutos...
echo    Incluyendo: Backend + Interfaz + Assets + Frontend build...

python -m PyInstaller ^
  --onefile ^
  --windowed ^
  --icon=interfaz\icono.ico ^
  --name=SistemaTurismo ^
  --add-data="interfaz;interfaz" ^
  --add-data="public;public" ^
  --add-data="assets;assets" ^
  --add-data="cache_imagenes;cache_imagenes" ^
  --add-data="react-build;react-build" ^
  --add-data="dist;dist" ^
  --add-data="build;build" ^
  --add-data=".env;." ^
  --add-data="config.ini;." ^
  --add-data="mysql_config.json;." ^
  --add-data="key.key;." ^
  --hidden-import=PyQt5.QtCore ^
  --hidden-import=PyQt5.QtGui ^
  --hidden-import=PyQt5.QtWidgets ^
  --hidden-import=mysql.connector ^
  --hidden-import=mysql.connector.locales.eng.client_error ^
  --hidden-import=mysql.connector.locales.eng.mysql_error ^
  --hidden-import=requests ^
  --hidden-import=psutil ^
  --hidden-import=urllib3 ^
  --hidden-import=chardet ^
  --hidden-import=idna ^
  --hidden-import=certifi ^
  --hidden-import=cryptography.fernet ^
  --hidden-import=PIL ^
  --hidden-import=PIL.Image ^
  --hidden-import=PIL.ImageDraw ^
  main.py

REM Verificar si se generó exitosamente
if exist "dist\SistemaTurismo.exe" (
    echo.
    echo ===============================================
    echo    ✅ EJECUTABLE GENERADO EXITOSAMENTE!
    echo ===============================================
    echo.
    echo 📁 Ubicación: dist\SistemaTurismo.exe
    for %%F in ("dist\SistemaTurismo.exe") do (
        set /a size=%%~zF/1024/1024
        echo 📏 Tamaño: !size! MB
    )
    echo.
    echo 📦 Archivos incluidos:
    echo    ✅ Backend Python (app_*.py, database_*.py)
    echo    ✅ Interfaces Qt (.ui files)
    echo    ✅ Assets e imágenes
    echo    ✅ Frontend build (React/Vite)
    echo    ✅ Configuraciones (.env, .ini, .json)
    echo    ✅ Cache de imágenes
    echo.
    echo 🧪 Para probar el ejecutable:
    echo    dist\SistemaTurismo.exe
    echo.
    
    REM Copiar a la raíz para facilitar acceso
    copy "dist\SistemaTurismo.exe" "SistemaTurismo.exe" >nul
    echo 📋 Copiado también a: SistemaTurismo.exe
    echo.
) else (
    echo.
    echo ❌ ERROR: No se pudo generar el ejecutable.
    echo    Revise los mensajes de error arriba.
)

echo ⏳ Finalizando...
timeout /t 3 >nul