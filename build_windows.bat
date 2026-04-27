@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

:: =============================================================
:: build_windows.bat — model-gateway Nuitka 编译脚本 (Windows)
:: 使用方式:
::   build_windows.bat           独立目录模式（默认）
::   build_windows.bat onefile   单文件 exe 模式
::   build_windows.bat clean     清理后独立目录模式
::   build_windows.bat onefile clean   清理后单文件模式
:: 依赖: Python 3.9+, nuitka, Visual Studio Build Tools (cl.exe)
:: =============================================================

set "PROJECT_ROOT=%~dp0"
set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"
set "ENTRY=main.py"
set "APP_NAME=model-gateway"
set "ONEFILE=0"
set "CLEAN=0"

:: 解析参数
for %%A in (%*) do (
    if /I "%%A"=="onefile" set "ONEFILE=1"
    if /I "%%A"=="clean"   set "CLEAN=1"
)

set "DIST_DIR=%PROJECT_ROOT%\dist\windows"

echo ======================================
echo   Model Gateway — Windows Nuitka Build
echo ======================================

:: ── 清理旧产物 ─────────────────────────────────────────────
if "%CLEAN%"=="1" (
    echo.
    echo [1/5] 清理旧构建产物...
    for %%D in (main.build main.dist main.onefile-build dist) do (
        if exist "%PROJECT_ROOT%\%%D" (
            rd /s /q "%PROJECT_ROOT%\%%D"
            echo   已删除: %%D
        )
    )
)

:: ── 检查 Python ────────────────────────────────────────────
echo.
echo [2/5] 检查 Python 环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo   ✗ 未找到 python，请确认已安装 Python 3.9+ 并加入 PATH
    exit /b 1
)
for /f "tokens=*" %%V in ('python --version 2^>^&1') do echo   Python: %%V

:: ── 检查 / 安装 Nuitka ────────────────────────────────────
echo.
echo [3/5] 确认 Nuitka 已安装...
python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo   未检测到 Nuitka，正在安装...
    pip install nuitka
    if errorlevel 1 (
        echo   ✗ Nuitka 安装失败，请手动执行: pip install nuitka
        exit /b 1
    )
)
for /f "tokens=*" %%V in ('python -m nuitka --version 2^>^&1') do echo   Nuitka: %%V

:: ── 准备输出目录 ───────────────────────────────────────────
echo.
echo [4/5] 准备输出目录: %DIST_DIR%
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

:: ── 执行编译 ──────────────────────────────────────────────
echo.
echo [5/5] 开始编译...
cd /d "%PROJECT_ROOT%"

set "NUITKA_ARGS=python -m nuitka"
set "NUITKA_ARGS=%NUITKA_ARGS% --show-progress"
set "NUITKA_ARGS=%NUITKA_ARGS% --show-memory"
set "NUITKA_ARGS=%NUITKA_ARGS% --assume-yes-for-downloads"
:: 业务包
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=api"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=core"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=crud"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=db"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=middleware"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=models"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=providers"
:: 关键第三方包
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=fastapi"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=uvicorn"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=pydantic"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=pydantic_settings"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=aiohttp"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=aiomysql"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=httpx"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=jose"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=passlib"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=cryptography"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=dotenv"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=shortuuid"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=ujson"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=starlette"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=anyio"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=click"
set "NUITKA_ARGS=%NUITKA_ARGS% --include-package=h11"
:: 静态文件
set "NUITKA_ARGS=%NUITKA_ARGS% --include-data-dir=static=static"
:: 输出配置
set "NUITKA_ARGS=%NUITKA_ARGS% --output-dir=%DIST_DIR%"
set "NUITKA_ARGS=%NUITKA_ARGS% --output-filename=%APP_NAME%.exe"
:: Windows 子系统（控制台程序）
set "NUITKA_ARGS=%NUITKA_ARGS% --windows-console-mode=attach"

if "%ONEFILE%"=="1" (
    echo   模式: 单文件 exe --onefile
    set "NUITKA_ARGS=%NUITKA_ARGS% --onefile"
    set "NUITKA_ARGS=%NUITKA_ARGS% --onefile-tempdir-spec={TEMP}\model-gateway"
) else (
    echo   模式: 独立目录 --standalone
    set "NUITKA_ARGS=%NUITKA_ARGS% --standalone"
)

set "NUITKA_ARGS=%NUITKA_ARGS% %ENTRY%"
%NUITKA_ARGS%
if errorlevel 1 (
    echo.
    echo ✗ 编译失败，请检查上方错误信息
    exit /b 1
)

:: ── 复制运行所需的额外文件 ─────────────────────────────────
echo.
echo Post-build: 复制运行资源...

if "%ONEFILE%"=="1" (
    set "TARGET_DIR=%DIST_DIR%"
) else (
    set "TARGET_DIR=%DIST_DIR%\%APP_NAME%.dist"
)

:: 复制 static（若编译时 --include-data-dir 未完整覆盖，则手动补充）
if not exist "!TARGET_DIR!\static" (
    xcopy /e /i /q "%PROJECT_ROOT%\static" "!TARGET_DIR!\static" >nul
    echo   已复制 static\
)

:: 复制 .env（如果存在）
if exist "%PROJECT_ROOT%\.env" (
    copy /y "%PROJECT_ROOT%\.env" "!TARGET_DIR!\" >nul
    echo   已复制 .env
)

:: 复制 sql 初始化脚本
if exist "%PROJECT_ROOT%\sql" (
    xcopy /e /i /q "%PROJECT_ROOT%\sql" "!TARGET_DIR!\sql" >nul
    echo   已复制 sql\
)

echo.
echo ======================================
echo   编译完成！
if "%ONEFILE%"=="1" (
    echo   可执行文件: %DIST_DIR%\%APP_NAME%.exe
) else (
    echo   可执行目录: !TARGET_DIR!\
    echo   可执行文件: !TARGET_DIR!\%APP_NAME%.exe
)
echo   运行方式:   双击 exe 或 cmd 中执行 %APP_NAME%.exe
echo ======================================

endlocal
pause
