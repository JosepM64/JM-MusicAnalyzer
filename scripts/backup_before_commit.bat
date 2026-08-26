@echo off
REM Backup script para JM-MusicAnalyzer
REM Crea backup con timestamp de archivos modificados

set "PROYECTO=C:\Mega\JOSEP\_swing\jm varis\_POST FEINA\Feines\Programació\JM-MusicAnalizer"
set "BACKUP_DIR=%PROYECTO%\backups\pre_commit"

REM Crear directorio si no existe
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

REM Timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set "dt=%%I"
set "timestamp=%dt:~0,8%_%dt:~8,6%"

REM Copiar archivos críticos
copy "%PROYECTO%\ui\performance_window.py" "%BACKUP_DIR%\performance_window_%timestamp%.py" >nul
copy "%PROYECTO%\ui\widgets\audio_engine_player.py" "%BACKUP_DIR%\audio_engine_player_%timestamp%.py" >nul
copy "%PROYECTO%\ui\widgets\playlist_widget.py" "%BACKUP_DIR%\playlist_widget_%timestamp%.py" >nul
copy "%PROYECTO%\ui\main_window.py" "%BACKUP_DIR%\main_window_%timestamp%.py" >nul
copy "%PROYECTO%\ui\dialogs\about_dialog.py" "%BACKUP_DIR%\about_dialog_%timestamp%.py" >nul
copy "%PROYECTO%\JM-MusicAnalyzer.spec" "%BACKUP_DIR%\JM-MusicAnalyzer_%timestamp%.spec" >nul
copy "%PROYECTO%\main.py" "%BACKUP_DIR%\main_%timestamp%.py" >nul

echo Backup creado en %BACKUP_DIR% con timestamp %timestamp%
