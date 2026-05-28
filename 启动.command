#!/bin/bash
# 关闭当前终端窗口，在后台静默启动
DIR="$(cd "$(dirname "$0")" && pwd)"

# 检查是否已经在运行
if pgrep -f "spektrafilm" > /dev/null 2>&1; then
    osascript -e 'display notification "Spektrafilm 已在运行中" with title "Spektrafilm"'
    # 关闭当前终端窗口
    osascript -e 'tell application "Terminal" to close (every window whose name contains "启动")' 2>/dev/null
    exit 0
fi

# 后台静默启动，不占用终端
cd "$DIR"
nohup uv run spektrafilm > /tmp/spektrafilm.log 2>&1 &

# 通知用户已启动
sleep 1
osascript -e 'display notification "Spektrafilm 已启动" with title "Spektrafilm"'

# 关闭当前终端窗口
osascript -e 'tell application "Terminal" to close (every window whose name contains "启动")' 2>/dev/null
