#!/bin/bash
# Spektrafilm 安装脚本
# 双击运行，自动安装所有依赖

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

notify() {
    osascript -e "display notification \"$1\" with title \"Spektrafilm 安装\"" 2>/dev/null
}

alert() {
    osascript -e "display alert \"Spektrafilm 安装\" message \"$1\" buttons {\"好的\"} default button 1" 2>/dev/null
}

close_terminal() {
    osascript -e 'tell application "Terminal" to close (every window whose name contains "安装")' 2>/dev/null
}

# ── 检查 uv ───────────────────────────────────────────────────────────────────

echo "=== Spektrafilm 安装程序 ==="
echo ""

UV_BIN=""
for candidate in \
    "$HOME/.local/bin/uv" \
    "$HOME/.cargo/bin/uv" \
    "/opt/homebrew/bin/uv" \
    "/usr/local/bin/uv" \
    "$(command -v uv 2>/dev/null)"
do
    if [ -x "$candidate" ]; then
        UV_BIN="$candidate"
        break
    fi
done

if [ -z "$UV_BIN" ]; then
    echo "未检测到 uv，正在安装..."
    notify "正在安装 uv 环境管理工具..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    for candidate in "$HOME/.local/bin/uv" "$HOME/.cargo/bin/uv" "/opt/homebrew/bin/uv"; do
        if [ -x "$candidate" ]; then UV_BIN="$candidate"; break; fi
    done
    if [ -z "$UV_BIN" ]; then
        alert "uv 安装失败，请检查网络连接后重试。"
        exit 1
    fi
    echo "uv 安装完成：$UV_BIN"
else
    echo "已检测到 uv：$UV_BIN"
fi

# ── 安装 Python 3.13 ─────────────────────────────────────────────────────────

echo ""
echo "正在检查 Python 3.13..."
notify "正在检查 Python 环境..."
"$UV_BIN" python install 3.13 2>&1 | tail -5

# ── 安装项目依赖 ──────────────────────────────────────────────────────────────

echo ""
echo "正在安装项目依赖（首次约需 5–15 分钟，请耐心等待）..."
notify "正在安装依赖，请耐心等待..."
"$UV_BIN" sync 2>&1

if [ $? -ne 0 ]; then
    alert "依赖安装失败，请检查网络连接后重试。"
    exit 1
fi

# ── 完成 ──────────────────────────────────────────────────────────────────────

echo ""
echo "=== 安装完成 ==="
echo "现在可以双击「启动.command」开始使用 Spektrafilm。"

notify "安装完成！现在可以双击「启动.command」开始使用。"
alert "安装完成！\n\n现在可以双击「启动.command」开始使用 Spektrafilm。"

close_terminal
