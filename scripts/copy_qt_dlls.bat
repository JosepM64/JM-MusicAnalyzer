@echo off
REM =====================================================
REM Script para copiar DLLs necesarios
REM =====================================================

REM Ir al directorio del proyecto (padre de scripts)
cd /d "%~dp0.."

set DIST_PATH=dist\JM-MusicAnalyzer
set QT_PLUGINS=%DIST_PATH%\Qt6\plugins

echo Copiando archivos al dist...

echo.
echo Completado!
