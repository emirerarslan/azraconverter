@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo      AZRA CONVERTER - PREMIUM BUILD
echo ============================================
echo.

set "TESS_DIR=C:\Program Files\Tesseract-OCR"

rem Always build with Python 3.  This prevents a system Python association
rem from interpreting UTF-8 source files with a legacy code page.
where py >nul 2>nul
if errorlevel 1 (
    set "PYTHON_CMD=python"
) else (
    set "PYTHON_CMD=py -3"
)

if not exist "main.py" (
    echo HATA: main.py bulunamadi.
    pause
    exit /b 1
)

if not exist "azra.ico" (
    echo HATA: azra.ico bulunamadi.
    pause
    exit /b 1
)

if not exist "azra-logo.png" (
    echo HATA: azra-logo.png bulunamadi.
    pause
    exit /b 1
)

if not exist "%TESS_DIR%\tesseract.exe" (
    echo HATA: Tesseract bulunamadi:
    echo %TESS_DIR%\tesseract.exe
    pause
    exit /b 1
)

%PYTHON_CMD% -m pip install --upgrade pyinstaller
if errorlevel 1 (
    echo HATA: PyInstaller kurulumu basarisiz.
    pause
    exit /b 1
)

echo.
echo Eski build temizleniyor...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "AZRA CONVERTER.spec" del /q "AZRA CONVERTER.spec"

echo.
echo PREMIUM EXE klasoru olusturuluyor...
%PYTHON_CMD% -m PyInstaller --noconfirm --clean --onedir --windowed ^
 --name "AZRA CONVERTER" ^
 --icon "azra.ico" ^
 --add-data "azra.ico;." ^
 --add-data "azra-logo.png;." ^
 --add-data "rafine.ico;." ^
 --add-data "rafine-logo.jpg;." ^
 --add-data "emir-logo.jpg;." ^
 --add-data "emir-video.mp4;." ^
 --add-data "emir-yıldız.png;." ^
 --add-data "update_config.json;." ^
 --add-data "%TESS_DIR%;tesseract" ^
 main.py

if errorlevel 1 (
    echo.
    echo HATA: EXE olusturulamadi.
    pause
    exit /b 1
)

echo.
echo ============================================
echo BASARILI!
echo Program: dist\AZRA CONVERTER\AZRA CONVERTER.exe
echo ICO:     dist\AZRA CONVERTER\azra.ico
echo ============================================
echo.
pause
