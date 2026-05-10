#!/bin/bash
# 计算传播论文追踪系统 - 定时任务脚本
# 用法: ./scripts/run_tracker.sh

# 设置工作目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 设置环境变量（如果需要）
# export ANTHROPIC_API_KEY="your-api-key-here"

# 运行论文追踪
echo "=========================================="
echo "开始运行论文追踪 - $(date)"
echo "=========================================="

python -m src.main "$@"

EXIT_CODE=$?

echo ""
echo "=========================================="
echo "运行完成 - $(date) - 退出码: $EXIT_CODE"
echo "=========================================="

exit $EXIT_CODE
