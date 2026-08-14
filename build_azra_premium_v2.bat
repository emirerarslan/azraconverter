@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo      AZRA CONVERTER - PREMIUM BUILD
echo ============================================
echo.

set "TESS_DIR=C:\Program Files\Tesseract-OCR"

if not exist "main.py" (
    echo HATA: main.py bulunamadi.
    pause
    exit /b 1
)

if not exist "azra_gold.ico" (
    echo HATA: azra_gold.ico bulunamadi.
    pause
    exit /b 1
)

if not exist "azra_gold_logo_real_transparent.png" (
    echo HATA: azra_gold_logo_real_transparent.png bulunamadi.
    pause
    exit /b 1
)

if not exist "%TESS_DIR%\tesseract.exe" (
    echo HATA: Tesseract bulunamadi:
    echo %TESS_DIR%\tesseract.exe
    pause
    exit /b 1
)

python -m pip install --upgrade pyinstaller
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
python -m PyInstaller --noconfirm --clean --onedir --windowed ^
 --name "AZRA CONVERTER" ^
 --icon "azra_gold.ico" ^
 --add-data "azra_gold.ico;." ^
 --add-data "azra_gold_logo_real_transparent.png;." ^
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
echo ICO:     dist\AZRA CONVERTER\azra_gold.ico
echo ============================================
echo.
pause
