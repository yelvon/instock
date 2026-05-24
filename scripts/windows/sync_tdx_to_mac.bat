@echo off
REM TDX vipdoc -> Mac ~/tdx-local (Parallels Z: = Mac home). Run inside Windows VM only.
setlocal
set "TDX_SRC=C:\new_tdx"
if exist "Z:\" (
    set "MAC_VIPDOC=Z:\tdx-local\vipdoc"
    set "MAC_HOME=Z:\"
) else (
    set "MAC_VIPDOC=\\Mac\Home\tdx-local\vipdoc"
    set "MAC_HOME=\\Mac\Home\"
)
set "LOG=%USERPROFILE%\sync_tdx_to_mac.log"

if not exist "%TDX_SRC%\vipdoc\sh\lday" (
    echo [ERROR] Missing %TDX_SRC%\vipdoc - run TDX post-market download first
    exit /b 1
)
if not exist "%MAC_HOME%" (
    echo [ERROR] Mac share not found - enable Parallels Shared Folders
    exit /b 1
)

mkdir "%MAC_HOME%tdx-local" 2>nul
mkdir "%MAC_VIPDOC%" 2>nul

echo [%date% %time%] sync start >> "%LOG%"
echo SRC: %TDX_SRC%\vipdoc
echo DST: %MAC_VIPDOC%

robocopy "%TDX_SRC%\vipdoc" "%MAC_VIPDOC%" /E /XO /R:2 /W:3 /NP /LOG+:"%LOG%" /TEE

set RC=%ERRORLEVEL%
echo robocopy exit: %RC%
if %RC% GEQ 8 exit /b %RC%
exit /b 0
