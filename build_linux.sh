#!/usr/bin/env bash
# =============================================================
# build_linux.sh — model-gateway Nuitka 编译脚本 (Linux)
# 使用方式: bash build_linux.sh [--onefile] [--clean]
# 依赖: Python 3.9+, nuitka, patchelf, gcc
# =============================================================

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENTRY="main.py"
APP_NAME="model-gateway"
ONEFILE=false
CLEAN=false

# 解析参数
for arg in "$@"; do
    case $arg in
        --onefile) ONEFILE=true ;;
        --clean)   CLEAN=true  ;;
        *) echo "未知参数: $arg"; exit 1 ;;
    esac
done

DIST_DIR="$PROJECT_ROOT/dist/linux"

echo "======================================"
echo "  Model Gateway — Linux Nuitka Build  "
echo "======================================"

# ── 清理旧产物 ────────────────────────────────────────────────
if $CLEAN; then
    echo ""
    echo "[1/5] 清理旧构建产物..."
    for d in main.build main.dist main.onefile-build dist; do
        p="$PROJECT_ROOT/$d"
        if [ -d "$p" ]; then
            rm -rf "$p"
            echo "  已删除: $d"
        fi
    done
fi

# ── 检查系统依赖 ──────────────────────────────────────────────
echo ""
echo "[2/5] 检查系统依赖..."

check_cmd() {
    if command -v "$1" &>/dev/null; then
        echo "  ✓ $1 ($(command -v $1))"
    else
        echo "  ✗ 未找到 $1，请先安装: $2"
        exit 1
    fi
}

check_cmd python3    "sudo apt install python3"
check_cmd gcc        "sudo apt install build-essential"
check_cmd patchelf   "sudo apt install patchelf"

PYTHON="python3"
PY_VER=$($PYTHON --version)
echo "  Python: $PY_VER"

# ── 安装/确认 nuitka ─────────────────────────────────────────
echo ""
echo "[3/5] 确认 Nuitka 已安装..."
if ! $PYTHON -m nuitka --version &>/dev/null; then
    echo "  未检测到 Nuitka，正在安装..."
    pip3 install nuitka
fi
$PYTHON -m nuitka --version

# ── 准备输出目录 ──────────────────────────────────────────────
echo ""
echo "[4/5] 准备输出目录: $DIST_DIR"
mkdir -p "$DIST_DIR"

# ── 执行编译 ─────────────────────────────────────────────────
echo ""
echo "[5/5] 开始编译..."
cd "$PROJECT_ROOT"

NUITKA_ARGS=(
    -m nuitka
    --show-progress
    --show-memory
    # 包含所有业务包
    --include-package=api
    --include-package=core
    --include-package=crud
    --include-package=db
    --include-package=middleware
    --include-package=models
    --include-package=providers
    # 关键第三方包
    --include-package=fastapi
    --include-package=uvicorn
    --include-package=pydantic
    --include-package=pydantic_settings
    --include-package=aiohttp
    --include-package=aiomysql
    --include-package=httpx
    --include-package=jose
    --include-package=passlib
    --include-package=cryptography
    --include-package=dotenv
    --include-package=shortuuid
    --include-package=ujson
    --include-package=starlette
    --include-package=anyio
    --include-package=click
    --include-package=h11
    # 包含静态文件数据
    "--include-data-dir=static=static"
    "--include-data-files=.env=.env"
    # 编译选项
    --assume-yes-for-downloads
    "--linux-onefile-icon=static/favicon.png"   # 若无此文件可删除此行
    "--output-dir=$DIST_DIR"
    "--output-filename=$APP_NAME"
    "$ENTRY"
)

if $ONEFILE; then
    echo "  模式: 单文件二进制 (--onefile)"
    NUITKA_ARGS+=(--onefile "--onefile-tempdir-spec=/tmp/.model-gateway")
else
    echo "  模式: 独立目录 (--standalone)"
    NUITKA_ARGS+=(--standalone)
fi

$PYTHON "${NUITKA_ARGS[@]}"

# ── 复制运行所需的额外文件 ────────────────────────────────────
echo ""
echo "Post-build: 复制运行资源..."

if $ONEFILE; then
    TARGET_DIR="$DIST_DIR"
else
    TARGET_DIR="$DIST_DIR/$APP_NAME.dist"
fi

# 复制 static 目录
if [ ! -d "$TARGET_DIR/static" ]; then
    cp -r "$PROJECT_ROOT/static" "$TARGET_DIR/"
    echo "  已复制 static/"
fi

# 复制 .env（如果存在）
if [ -f "$PROJECT_ROOT/.env" ]; then
    cp "$PROJECT_ROOT/.env" "$TARGET_DIR/"
    echo "  已复制 .env"
fi

# 复制 sql 初始化脚本
if [ -d "$PROJECT_ROOT/sql" ]; then
    cp -r "$PROJECT_ROOT/sql" "$TARGET_DIR/"
    echo "  已复制 sql/"
fi

# 设置可执行权限
if $ONEFILE; then
    chmod +x "$DIST_DIR/$APP_NAME"
else
    chmod +x "$TARGET_DIR/$APP_NAME"
fi

echo ""
echo "======================================"
echo "  编译完成！"
if $ONEFILE; then
    echo "  可执行文件: $DIST_DIR/$APP_NAME"
else
    echo "  可执行目录: $TARGET_DIR/"
    echo "  可执行文件: $TARGET_DIR/$APP_NAME"
fi
echo "  运行方式:   ./$APP_NAME"
echo "======================================"
