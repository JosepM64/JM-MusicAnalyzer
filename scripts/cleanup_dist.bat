@echo off
setlocal EnableDelayedExpansion
REM =====================================================
REM Script para limpiar archivos innecesarios del dist
REM =====================================================

cd /d "%~dp0.."

set DIST_PATH=dist\JM-MusicAnalyzer\_internal
REM PySide6 >= 6.5: plugins i traduccions viuen directament a _internal\PySide6 (sense subcarpeta Qt6)
set QT_PLUGINS=%DIST_PATH%\PySide6\plugins
set QT_TRANSLATIONS=%DIST_PATH%\PySide6\translations

echo ====================================
echo Limpiando archivos innecesarios...
echo ====================================
echo.

REM Excluir DLLs Qt sense us (coherent amb filtres del .spec)
echo - Eliminando OpenGL software, Quick/QML, PDF i VirtualKeyboard...
if exist "%DIST_PATH%\PySide6\opengl32sw.dll" del /q "%DIST_PATH%\PySide6\opengl32sw.dll"
if exist "%DIST_PATH%\PySide6\Qt6Quick*.dll" del /q "%DIST_PATH%\PySide6\Qt6Quick*.dll"
if exist "%DIST_PATH%\PySide6\Qt6Qml*.dll" del /q "%DIST_PATH%\PySide6\Qt6Qml*.dll"
if exist "%DIST_PATH%\PySide6\Qt6Pdf*.dll" del /q "%DIST_PATH%\PySide6\Qt6Pdf*.dll"
if exist "%DIST_PATH%\PySide6\qpdf.dll" del /q "%DIST_PATH%\PySide6\qpdf.dll"
if exist "%DIST_PATH%\PySide6\Qt6VirtualKeyboard.dll" del /q "%DIST_PATH%\PySide6\Qt6VirtualKeyboard.dll"

REM Eliminar QtWebEngine DLLs
echo - Eliminando QtWebEngine...
if exist "%DIST_PATH%\PySide6\Qt6WebEngineCore.dll" del /q "%DIST_PATH%\PySide6\Qt6WebEngineCore.dll"
if exist "%DIST_PATH%\PySide6\Qt6WebEngine.dll" del /q "%DIST_PATH%\PySide6\Qt6WebEngine.dll"
if exist "%DIST_PATH%\PySide6\Qt6WebEngineQuick.dll" del /q "%DIST_PATH%\PySide6\Qt6WebEngineQuick.dll"
if exist "%DIST_PATH%\PySide6\Qt6WebEngineWidgets.dll" del /q "%DIST_PATH%\PySide6\Qt6WebEngineWidgets.dll"

REM Eliminar Qt3D
echo - Eliminando Qt3D...
if exist "%DIST_PATH%\PySide6\Qt63DRender.dll" del /q "%DIST_PATH%\PySide6\Qt63DRender.dll"
if exist "%DIST_PATH%\PySide6\Qt6Quick3D.dll" del /q "%DIST_PATH%\PySide6\Qt6Quick3D.dll"
if exist "%DIST_PATH%\PySide6\Qt6Quick3DRuntimeRender.dll" del /q "%DIST_PATH%\PySide6\Qt6Quick3DRuntimeRender.dll"
if exist "%DIST_PATH%\PySide6\Qt63DCore.dll" del /q "%DIST_PATH%\PySide6\Qt63DCore.dll"
if exist "%DIST_PATH%\PySide6\Qt63DExtras.dll" del /q "%DIST_PATH%\PySide6\Qt63DExtras.dll"
if exist "%DIST_PATH%\PySide6\Qt63DInput.dll" del /q "%DIST_PATH%\PySide6\Qt63DInput.dll"
if exist "%DIST_PATH%\PySide6\Qt63DLogic.dll" del /q "%DIST_PATH%\PySide6\Qt63DLogic.dll"
if exist "%DIST_PATH%\PySide6\Qt63DAnimation.dll" del /q "%DIST_PATH%\PySide6\Qt63DAnimation.dll"

REM Eliminar QtOpenGL
echo - Eliminando QtOpenGL...
if exist "%DIST_PATH%\PySide6\Qt6OpenGL.dll" del /q "%DIST_PATH%\PySide6\Qt6OpenGL.dll"
if exist "%DIST_PATH%\PySide6\Qt6OpenGLWidgets.dll" del /q "%DIST_PATH%\PySide6\Qt6OpenGLWidgets.dll"

REM Eliminar QtSvg
echo - Eliminando QtSvg...
if exist "%DIST_PATH%\PySide6\Qt6Svg.dll" del /q "%DIST_PATH%\PySide6\Qt6Svg.dll"

REM Eliminar QtXml
echo - Eliminando QtXml...
if exist "%DIST_PATH%\PySide6\Qt6Xml.dll" del /q "%DIST_PATH%\PySide6\Qt6Xml.dll"

REM Eliminar QtMultimediaWidgets
echo - Eliminando QtMultimediaWidgets...
if exist "%DIST_PATH%\PySide6\Qt6MultimediaWidgets.dll" del /q "%DIST_PATH%\PySide6\Qt6MultimediaWidgets.dll"

REM Eliminar otros Qt innecesarios
echo - Eliminando Qt innecesarios...
if exist "%DIST_PATH%\PySide6\Qt6Charts.dll" del /q "%DIST_PATH%\PySide6\Qt6Charts.dll"
if exist "%DIST_PATH%\PySide6\Qt6DataVisualization.dll" del /q "%DIST_PATH%\PySide6\Qt6DataVisualization.dll"
if exist "%DIST_PATH%\PySide6\Qt6PrintSupport.dll" del /q "%DIST_PATH%\PySide6\Qt6PrintSupport.dll"
if exist "%DIST_PATH%\PySide6\Qt6Designer.dll" del /q "%DIST_PATH%\PySide6\Qt6Designer.dll"
if exist "%DIST_PATH%\PySide6\Qt6Help.dll" del /q "%DIST_PATH%\PySide6\Qt6Help.dll"
if exist "%DIST_PATH%\PySide6\Qt6Location.dll" del /q "%DIST_PATH%\PySide6\Qt6Location.dll"
if exist "%DIST_PATH%\PySide6\Qt6Nfc.dll" del /q "%DIST_PATH%\PySide6\Qt6Nfc.dll"
if exist "%DIST_PATH%\PySide6\Qt6Sensors.dll" del /q "%DIST_PATH%\PySide6\Qt6Sensors.dll"
if exist "%DIST_PATH%\PySide6\Qt6SerialPort.dll" del /q "%DIST_PATH%\PySide6\Qt6SerialPort.dll"
if exist "%DIST_PATH%\PySide6\Qt6TextToSpeech.dll" del /q "%DIST_PATH%\PySide6\Qt6TextToSpeech.dll"
if exist "%DIST_PATH%\PySide6\Qt6Bluetooth.dll" del /q "%DIST_PATH%\PySide6\Qt6Bluetooth.dll"
if exist "%DIST_PATH%\PySide6\Qt6Positioning.dll" del /q "%DIST_PATH%\PySide6\Qt6Positioning.dll"
if exist "%DIST_PATH%\PySide6\Qt6WebSockets.dll" del /q "%DIST_PATH%\PySide6\Qt6WebSockets.dll"
if exist "%DIST_PATH%\PySide6\Qt6WebChannel.dll" del /q "%DIST_PATH%\PySide6\Qt6WebChannel.dll"

REM Eliminar QtWebEngine en resources
echo - Eliminando WebEngine de resources...
if exist "%DIST_PATH%\resources\qtwebengine*" del /q "%DIST_PATH%\resources\qtwebengine*" 2>nul
if exist "%DIST_PATH%\resources\v8_context*" del /q "%DIST_PATH%\resources\v8_context*" 2>nul
if exist "%DIST_PATH%\resources\icudtl.dat" del /q "%DIST_PATH%\resources\icudtl.dat" 2>nul

REM Eliminar QML si no se usa
echo - Eliminando QML...
if exist "%DIST_PATH%\qml" rmdir /s /q "%DIST_PATH%\qml" 2>nul

REM Eliminar plugins Qt innecessaris.
REM NO tocar: platforms, styles, imageformats, iconengines, multimedia, mediaservice,
REM           tls, networkinformation, platforminputcontexts, generic
REM (imageformats=caratules JPG, styles=estil natiu Windows, multimedia=QMediaPlayer,
REM  tls=HTTPS QtNetwork, iconengines=icones SVG)
echo - Eliminando plugins Qt innecesarios...
if exist "%QT_PLUGINS%\accessible" rmdir /s /q "%QT_PLUGINS%\accessible" 2>nul
if exist "%QT_PLUGINS%\accessiblebridge" rmdir /s /q "%QT_PLUGINS%\accessiblebridge" 2>nul
if exist "%QT_PLUGINS%\audio" rmdir /s /q "%QT_PLUGINS%\audio" 2>nul
if exist "%QT_PLUGINS%\bearer" rmdir /s /q "%QT_PLUGINS%\bearer" 2>nul
if exist "%QT_PLUGINS%\canbus" rmdir /s /q "%QT_PLUGINS%\canbus" 2>nul
if exist "%QT_PLUGINS%\designer" rmdir /s /q "%QT_PLUGINS%\designer" 2>nul
if exist "%QT_PLUGINS%\gamepads" rmdir /s /q "%QT_PLUGINS%\gamepads" 2>nul
if exist "%QT_PLUGINS%\geoservices" rmdir /s /q "%QT_PLUGINS%\geoservices" 2>nul
if exist "%QT_PLUGINS%\kms" rmdir /s /q "%QT_PLUGINS%\kms" 2>nul
if exist "%QT_PLUGINS%\playlistformats" rmdir /s /q "%QT_PLUGINS%\playlistformats" 2>nul
if exist "%QT_PLUGINS%\position" rmdir /s /q "%QT_PLUGINS%\position" 2>nul
if exist "%QT_PLUGINS%\printsupport" rmdir /s /q "%QT_PLUGINS%\printsupport" 2>nul
if exist "%QT_PLUGINS%\qmltooling" rmdir /s /q "%QT_PLUGINS%\qmltooling" 2>nul
if exist "%QT_PLUGINS%\renderers" rmdir /s /q "%QT_PLUGINS%\renderers" 2>nul
if exist "%QT_PLUGINS%\renderplugins" rmdir /s /q "%QT_PLUGINS%\renderplugins" 2>nul
if exist "%QT_PLUGINS%\scenegraph" rmdir /s /q "%QT_PLUGINS%\scenegraph" 2>nul
if exist "%QT_PLUGINS%\sensors" rmdir /s /q "%QT_PLUGINS%\sensors" 2>nul
if exist "%QT_PLUGINS%\sensorgestures" rmdir /s /q "%QT_PLUGINS%\sensorgestures" 2>nul
if exist "%QT_PLUGINS%\sqldrivers" rmdir /s /q "%QT_PLUGINS%\sqldrivers" 2>nul
if exist "%QT_PLUGINS%\texttospeech" rmdir /s /q "%QT_PLUGINS%\texttospeech" 2>nul
if exist "%QT_PLUGINS%\virtualkeyboard" rmdir /s /q "%QT_PLUGINS%\virtualkeyboard" 2>nul
if exist "%QT_PLUGINS%\wayland-decoration-client" rmdir /s /q "%QT_PLUGINS%\wayland-decoration-client" 2>nul
if exist "%QT_PLUGINS%\wayland-graphics-integration-client" rmdir /s /q "%QT_PLUGINS%\wayland-graphics-integration-client" 2>nul
if exist "%QT_PLUGINS%\wayland-shell-integration" rmdir /s /q "%QT_PLUGINS%\wayland-shell-integration" 2>nul
if exist "%QT_PLUGINS%\webview" rmdir /s /q "%QT_PLUGINS%\webview" 2>nul

REM Mantener solo qwindows.dll en platforms
echo - Limpiando plugins de plataformas...
if exist "%QT_PLUGINS%\platforms" (
    for %%f in ("%QT_PLUGINS%\platforms\*") do (
        if /i not "%%~nxf"=="qwindows.dll" del /q "%%f" 2>nul
    )
    for /d %%d in ("%QT_PLUGINS%\platforms\*") do (
        if /i not "%%~nxd"=="." rmdir /s /q "%%d" 2>nul
    )
)

REM Estils: mantenir TOT el folder (Qt 6.7+ nomes inclou qmodernwindowsstyle;
REM filtrar per noms antics esborraria l'unic estil i l'app cauria a Fusion)
echo - Estils Qt: es mantenen

REM Eliminar traducciones innecesarias (solo espanol, catalan e ingles)
REM sense espai abans del pipe: l'espai trencaria l'ancora $ de findstr
echo - Limpiando traducciones...
if exist "%QT_TRANSLATIONS%" (
    for %%f in ("%QT_TRANSLATIONS%\*.qm") do (
        set "FNAME=%%~nxf"
        echo !FNAME!| findstr /i /r /c:"_es\.qm *$" /c:"_ca\.qm *$" /c:"_en\.qm *$" >nul
        if errorlevel 1 del /q "%%f"
    )
)

REM Eliminar archivos .pyc innecesarios
echo - Eliminando archivos de debug y docs...
if exist "%DIST_PATH%\numpy\tests" rmdir /s /q "%DIST_PATH%\numpy\tests" 2>nul
if exist "%DIST_PATH%\numpy\_core\tests" rmdir /s /q "%DIST_PATH%\numpy\_core\tests" 2>nul
if exist "%DIST_PATH%\numpy\random\tests" rmdir /s /q "%DIST_PATH%\numpy\random\tests" 2>nul
REM for /r "%DIST_PATH%" %%f in (*.pyc) do del /q "%%f" 2>nul

REM Eliminar scipy (no usado - ~70MB) y cryptography (no usado - ~9MB)
echo - Eliminando scipy, cryptography y otras libs no usadas...
if exist "%DIST_PATH%\scipy" rmdir /s /q "%DIST_PATH%\scipy" 2>nul
if exist "%DIST_PATH%\scipy.libs" rmdir /s /q "%DIST_PATH%\scipy.libs" 2>nul
if exist "%DIST_PATH%\cryptography" rmdir /s /q "%DIST_PATH%\cryptography" 2>nul
if exist "%DIST_PATH%\PIL" rmdir /s /q "%DIST_PATH%\PIL" 2>nul
if exist "%DIST_PATH%\Pillow.libs" rmdir /s /q "%DIST_PATH%\Pillow.libs" 2>nul

REM Eliminar librerias de librosa/ML no usadas (v4.0+) - NOTA: soxr SI es usa (resampleig dsp.py)
echo - Eliminando librosa, llvmlite, numba, sklearn, msgpack...
if exist "%DIST_PATH%\librosa" rmdir /s /q "%DIST_PATH%\librosa" 2>nul
if exist "%DIST_PATH%\llvmlite" rmdir /s /q "%DIST_PATH%\llvmlite" 2>nul
if exist "%DIST_PATH%\llvmlite.libs" rmdir /s /q "%DIST_PATH%\llvmlite.libs" 2>nul
if exist "%DIST_PATH%\numba" rmdir /s /q "%DIST_PATH%\numba" 2>nul
if exist "%DIST_PATH%\sklearn" rmdir /s /q "%DIST_PATH%\sklearn" 2>nul
if exist "%DIST_PATH%\msgpack" rmdir /s /q "%DIST_PATH%\msgpack" 2>nul

REM Eliminar DLLs MKL de numpy (~570 MB, no necesarias)
echo - Eliminando DLLs MKL de numpy...
del /q "%DIST_PATH%\mkl_*.dll" 2>nul

REM Mantenir ffmpeg.exe (necessari per plugin yt_dl) i fpcalc.exe (fingerprinting AcoustID)
echo - Manteniendo ffmpeg.exe y fpcalc.exe...

echo.
echo ====================================
echo Limpieza completada!
echo ====================================
