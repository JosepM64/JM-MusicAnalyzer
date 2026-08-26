@echo off
REM =====================================================
REM RUN.BAT - Ejecutar JM-MusicAnalyzer
REM =====================================================

cd /d "%~dp0"

echo Iniciando JM-MusicAnalyzer...
set PYTHONNOUSERSITE=1

REM Detectar python.exe del entorno conda jm_pyside_313
set CONDA_ENV=jm_pyside_313

REM Probar ubicaciones comunes
for %%p in (
    "%LOCALAPPDATA%\miniconda3\envs\%CONDA_ENV%\python.exe"
    "%USERPROFILE%\miniconda3\envs\%CONDA_ENV%\python.exe"
    "%USERPROFILE%\.conda\envs\%CONDA_ENV%\python.exe"
    "C:\ProgramData\miniconda3\envs\%CONDA_ENV%\python.exe"
    "C:\Users\JM\miniconda3\envs\%CONDA_ENV%\python.exe"
) do (
    if exist %%p (
        set "PYTHON_EXE=%%~p"
        goto :run
    )
)

echo ERROR: No se encontro python.exe del entorno %CONDA_ENV%.
echo Prueba a ejecutar manualmente:
echo   set PYTHONNOUSERSITE=1
echo   "C:\ruta\a\tu\python.exe" main.py
pause
exit /b 1

:run
"%PYTHON_EXE%" main.py
pause