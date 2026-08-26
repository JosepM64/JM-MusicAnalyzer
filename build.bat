@echo off
REM =====================================================
REM BUILD.BAT - Build automatico para JM-MusicAnalyzer
REM Usa entorno conda jm_pyside_313 (Python 3.13)
REM =====================================================

cd /d "%~dp0"

set PYTHONNOUSERSITE=1

set APP_NAME=JM-MusicAnalyzer
set CONDA_ENV=jm_pyside_313

REM Sanitize PATH: remove conflicting Qt DLL directories from other builds
set "PATH=%PATH:C:\Varis\JMComander\_internal;=%"
set "PATH=%PATH:C:\Varis\JM-MusicAnalyzer\_internal;=%"

REM Detectar conda automaticamente
set CONDA_PATH=
for /f "tokens=*" %%i in ('where.exe conda 2^>nul') do (
    set "CONDA_PATH=%%i"
    goto :found_conda
)

:found_conda
if "%CONDA_PATH%"=="" (
    echo ERROR: No se encontró conda. Asegúrate de tener Miniconda instalado y en el PATH.
    pause
    exit /b 1
)

for /f "tokens=*" %%b in ('"%CONDA_PATH%" info --base 2^>nul') do set "CONDA_BASE=%%b"
if not "%CONDA_BASE%"=="" (
    set "CONDA_PATH=%CONDA_BASE%\Scripts\conda.exe"
)
echo [OK] Conda detectado: %CONDA_PATH%
echo Usando entorno: %CONDA_ENV%

REM Detectar python.exe del entorno conda directamente
REM (evita "conda run" que falla con espacios en el path del usuario)
set "PYTHON_EXE=%CONDA_BASE%\envs\%CONDA_ENV%\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=%USERPROFILE%\miniconda3\envs\%CONDA_ENV%\python.exe"
)
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=%USERPROFILE%\.conda\envs\%CONDA_ENV%\python.exe"
)
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=%LOCALAPPDATA%\miniconda3\envs\%CONDA_ENV%\python.exe"
)
if not exist "%PYTHON_EXE%" (
    for /f "tokens=*" %%e in ('"%CONDA_PATH%" info --envs 2^>nul ^| findstr /C:"%CONDA_ENV%"') do (
        for /f "tokens=2" %%p in ("%%e") do (
            if exist "%%p\python.exe" set "PYTHON_EXE=%%p\python.exe"
        )
    )
)
if not exist "%PYTHON_EXE%" (
    echo ERROR: No se pudo encontrar python.exe del entorno %CONDA_ENV%.
    echo Buscado: %PYTHON_EXE%
    pause
    exit /b 1
)
echo [OK] Python detectado: %PYTHON_EXE%

REM Add conda Qt binary paths to PATH for correct DLL resolution during build
for %%p in ("%PYTHON_EXE%") do set "CONDA_ENV_DIR=%%~dp0.."
set "PATH=%CONDA_ENV_DIR%\Library\bin;%CONDA_ENV_DIR%\Library\lib\qt6\bin;%PATH%"

REM Verificar entorno conda
"%CONDA_PATH%" env list | findstr /C:"%CONDA_ENV%" >nul
if %ERRORLEVEL% neq 0 (
    echo ERROR: El entorno %CONDA_ENV% no existe.
    echo Ejecuta primero build.bat de JMComander para crearlo.
    pause
    exit /b 1
)

REM Generate version_info.txt from canonical source
echo Generating version_info.txt from JM_MusicAnalizer/__init__.py...
"%PYTHON_EXE%" scripts\generate_version_info.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Error generating version_info.txt, continuing...
)

REM Cerrar procesos
echo Cerrando procesos de %APP_NAME%.exe...
taskkill /F /IM %APP_NAME%.exe >nul 2>&1
taskkill /F /IM %APP_NAME%.exe >nul 2>&1
timeout /t 2 /nobreak >nul

REM Limpiar builds anteriores
echo Limpiando builds anteriores...
if exist "dist\%APP_NAME%" (
    echo   Eliminando dist\%APP_NAME%...
    rmdir /s /q "dist\%APP_NAME%" 2>nul
    if exist "dist\%APP_NAME%" (
        echo   [WARN] No se pudo eliminar dist\%APP_NAME%, reintentando...
        timeout /t 2 /nobreak >nul
        rmdir /s /q "dist\%APP_NAME%" 2>nul
    )
)
if exist "build" rmdir /s /q build 2>nul
if exist "dist" rmdir /s /q dist 2>nul
echo.

REM Instalar dependencias (solo si no existe PyInstaller)
echo Verificando dependencias...
"%PYTHON_EXE%" -m pip show PyInstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   Instalando PyInstaller via conda...
    "%CONDA_PATH%" install -n %CONDA_ENV% pyinstaller -y
    if %ERRORLEVEL% NEQ 0 (
        echo [WARN] Error instalando PyInstaller via conda, intentant pip...
        "%PYTHON_EXE%" -m pip install PyInstaller
        if %ERRORLEVEL% NEQ 0 (
            echo [WARN] Error instalando PyInstaller
        )
    )
) else (
    echo   PyInstaller ya esta instalado
)

REM Ejecutar PyInstaller
echo.
echo Compilando con PyInstaller...
echo Por favor espera...

"%PYTHON_EXE%" -m PyInstaller --noconfirm --clean JM-MusicAnalyzer.spec

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ====================================
    echo BUILD FALLIDO
    echo ====================================
    pause
    exit /b 1
)

REM Cleanup: ffmpeg is bundled by the spec (from ~/.spotdl/ffmpeg.exe) for yt-dlp plugin

REM Copiar DLLs de Qt6
echo.
echo Copiando Qt6 DLLs...
call scripts\copy_qt_dlls.bat

REM Copiar modulos que PyInstaller no encuentra (acoustid, audioread)
echo.
echo Copiando modulos externos (acoustid, audioread)...
"%PYTHON_EXE%" scripts\copy_extra_modules.py

REM Limpiar archivos innecesarios
echo.
echo Limpiando archivos innecesarios...
call scripts\cleanup_dist.bat

REM Eliminar EXE residual (etapa EXE) - solo queremos onedir
if exist "dist\%APP_NAME%.exe" (
    echo Eliminando EXE residual dist\%APP_NAME%.exe...
    del /f /q "dist\%APP_NAME%.exe" >nul 2>&1
)

echo.
echo ====================================
echo BUILD EXITOSO
echo ====================================
echo.
echo La release onedir está en: dist\%APP_NAME%\
echo.
echo Presiona cualquier tecla para cerrar...
pause >nul
exit /b 0
