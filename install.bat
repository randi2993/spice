:: Created: 13/05/2026
:: Version: 1.5.0
:: Author: Randi Ortiz
:: Description: spice installer for Windows

@echo off
setlocal EnableDelayedExpansion

title s p i c e  --  agent toolkit

:: Obtener código de escape ANSI
for /F %%a in ('echo prompt $E ^| cmd') do set "ESC=%%a"

:: Etiquetas de estado (solo el corchete)
set "TAG_RUN=%ESC%[33m[Executing]%ESC%[0m"
set "TAG_OK=%ESC%[32m[OK]%ESC%[0m"
set "TAG_FAIL=%ESC%[31m[FAIL]%ESC%[0m"
set "TAG_WARN=%ESC%[31m [^!]%ESC%[0m"

:: Borrar línea actual y volver al inicio
set "CLR=%ESC%[2K%ESC%[G"

:: ---------------------------------------------------------------
:: Calcular ancho de consola
:: ---------------------------------------------------------------
for /f "tokens=2 delims=:" %%w in ('mode con ^| findstr "Columns"') do set /a "COLS=%%w"
if not defined COLS set /a "COLS=80"

set /a "PAD_BANNER=(COLS - 59) / 2"
if %PAD_BANNER% lss 0 set "PAD_BANNER=0"
set "SP_BANNER="
for /l %%i in (1,1,%PAD_BANNER%) do set "SP_BANNER=!SP_BANNER! "

set /a "PAD_TITLE=(COLS - 29) / 2"
if %PAD_TITLE% lss 0 set "PAD_TITLE=0"
set "SP_TITLE="
for /l %%i in (1,1,%PAD_TITLE%) do set "SP_TITLE=!SP_TITLE! "

set /a "PAD_QUOTE=(COLS - 50) / 2"
if %PAD_QUOTE% lss 0 set "PAD_QUOTE=0"
set "SP_QUOTE="
for /l %%i in (1,1,%PAD_QUOTE%) do set "SP_QUOTE=!SP_QUOTE! "

set /a "PAD_DUNE=(COLS - 4) / 2"
if %PAD_DUNE% lss 0 set "PAD_DUNE=0"
set "SP_DUNE="
for /l %%i in (1,1,%PAD_DUNE%) do set "SP_DUNE=!SP_DUNE! "

set /a "PAD_ART=(COLS - 35) / 2"
if %PAD_ART% lss 0 set "PAD_ART=0"
set "SP_ART="
for /l %%i in (1,1,%PAD_ART%) do set "SP_ART=!SP_ART! "

:: ---------------------------------------------------------------
:: Render del banner
:: ---------------------------------------------------------------
echo %ESC%[35m
echo !SP_BANNER!===========================================================
echo !SP_TITLE!s p i c e   i n s t a l l e r
echo.
echo !SP_QUOTE!%ESC%[34m"He who controls the spice controls the universe."%ESC%[35m
echo !SP_DUNE!%ESC%[37mDune%ESC%[35m
echo !SP_BANNER!===========================================================%ESC%[0m

echo %ESC%[36m
echo !SP_ART!         ............ ..
echo !SP_ART!      .....................
echo !SP_ART!     ........................
echo !SP_ART!    ..........................
echo !SP_ART!   ..............---............
echo !SP_ART!  ...........-++####+-........---
echo !SP_ART! ..........--++#####+-...........
echo !SP_ART!...........--+##++##+...-....-----
echo !SP_ART!............--++#++++--.-....----.
echo !SP_ART! ..............-#+---.---.....----
echo !SP_ART!   .......--++--###+---++--...---
echo !SP_ART!    ....----++--+##++##++--..---
echo !SP_ART!     ....--------++#####-....-##
echo !SP_ART!  .---...-------++#####+-...-+##+
echo !SP_ART!...----.....-..----++++-...--++++-
echo !SP_ART!..-...........-+++++++--..------++
echo !SP_ART!-...............------..----------
echo !SP_ART!-........................---------
echo !SP_ART!-......................----------+
echo !SP_ART!.........................--...----
echo !SP_ART!..........................---..---
echo !SP_ART!.......................------...-.
echo !SP_ART!..........................----....
echo !SP_ART!.............................--...
echo %ESC%[0m

:: ---------------------------------------------------------------
:: Check Python
:: ---------------------------------------------------------------
<nul set /p "=%TAG_RUN% Python check"
python --version >nul 2>&1
if errorlevel 1 (
    echo %CLR%%TAG_FAIL% Python check
    echo %ESC%[31m       spice requires Python 3.10+ in PATH.%ESC%[0m
    pause
    exit /b 1
)
python -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo %CLR%%TAG_FAIL% Python check
    echo %ESC%[31m       spice requires Python 3.10 or higher.%ESC%[0m
    python --version
    pause
    exit /b 1
)
echo %CLR%%TAG_OK% Python check

:: ---------------------------------------------------------------
:: Paths
:: ---------------------------------------------------------------
set "SPICE_DIR=%USERPROFILE%\.spice"
set "BIN_DIR=%SPICE_DIR%\bin"
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

:: ---------------------------------------------------------------
:: If install dir exists, ask before overwriting
:: ---------------------------------------------------------------
if exist "%SPICE_DIR%" (
    echo.
    echo !TAG_WARN! %ESC%[33mAn existing installation was found at: %SPICE_DIR%%ESC%[0m
    echo %ESC%[31m    Overwriting will DELETE its current contents.%ESC%[0m
    echo %ESC%[33m    providers.json will be preserved automatically.%ESC%[0m
    echo %ESC%[31m    Any other custom file placed there will be lost.%ESC%[0m
    echo.
    set "CONFIRM="
    set /p "CONFIRM=Do you want to overwrite it? [y/N]: "
    echo.

    if /I not "!CONFIRM!"=="y" if /I not "!CONFIRM!"=="yes" (
        echo !TAG_WARN! %ESC%[33mInstallation cancelled by user %ESC%[0m
        pause
        exit /b 1
    )

    :: providers.json used to live inside %SPICE_DIR%, so every reinstall
    :: destroyed it. Move it out before wiping; spice reads the new path.
    if exist "%SPICE_DIR%\providers.json" (
        if not exist "%APPDATA%\spice" mkdir "%APPDATA%\spice"
        if not exist "%APPDATA%\spice\providers.json" (
            copy /y "%SPICE_DIR%\providers.json" "%APPDATA%\spice\providers.json" >nul
            echo %TAG_OK% Preserved providers.json to %APPDATA%\spice\
        )
    )

    <nul set /p "=%TAG_RUN% Remove previous installation"
    rmdir /s /q "%SPICE_DIR%"
    echo %CLR%%TAG_OK% Remove previous installation
)

:: ---------------------------------------------------------------
:: Copy files
:: ---------------------------------------------------------------
<nul set /p "=%TAG_RUN% Install files to %SPICE_DIR%"
xcopy "%SCRIPT_DIR%" "%SPICE_DIR%" /e /i /q /exclude:%~dp0.installignore >nul 2>&1
if errorlevel 1 (
    xcopy "%SCRIPT_DIR%" "%SPICE_DIR%" /e /i /q >nul
)
if not exist "%BIN_DIR%" mkdir "%BIN_DIR%"

:: Record where this install came from, so `spice self-update` can find the
:: source checkout. xcopy skips hidden entries, so .git is never copied and the
:: installed copy is not a git repository.
> "%SPICE_DIR%\install-source.txt" echo %SCRIPT_DIR%

echo %CLR%%TAG_OK% Install files to %SPICE_DIR%

:: ---------------------------------------------------------------
:: Locate spice.py
:: ---------------------------------------------------------------
set "SPICE_PY="
if exist "%BIN_DIR%\spice.py"   set "SPICE_PY=%BIN_DIR%\spice.py"
if not defined SPICE_PY if exist "%SPICE_DIR%\spice.py" set "SPICE_PY=%SPICE_DIR%\spice.py"

if not defined SPICE_PY (
    echo %TAG_FAIL% Locate spice.py
    echo %ESC%[31m       spice.py not found in %BIN_DIR% nor in %SPICE_DIR%.%ESC%[0m
    pause
    exit /b 1
)

:: ---------------------------------------------------------------
:: Create launcher
:: ---------------------------------------------------------------
<nul set /p "=%TAG_RUN% Create launcher"
> "%BIN_DIR%\spice.bat" echo @echo off
>>"%BIN_DIR%\spice.bat" echo python "%SPICE_PY%" %%*
echo %CLR%%TAG_OK% Create launcher

:: ---------------------------------------------------------------
:: Update PATH
:: ---------------------------------------------------------------
<nul set /p "=%TAG_RUN% Update user PATH"
powershell -NoProfile -Command ^
  "$p = [Environment]::GetEnvironmentVariable('PATH','User');" ^
  "if ($p -notlike '*\.spice\bin*') {" ^
  "  [Environment]::SetEnvironmentVariable('PATH', $p.TrimEnd(';') + ';%BIN_DIR%', 'User');" ^
  "  exit 0" ^
  "} else { exit 2 }" >nul 2>&1
if errorlevel 2 (
    echo %CLR%%TAG_OK% Update user PATH (already contained spice, skipped^)
) else (
    echo %CLR%%TAG_OK% Update user PATH
)

echo.
echo %ESC%[32mDone.%ESC%[0m 
echo Open a new terminal and run: spice init
echo Press any key to close this window...
pause > nul