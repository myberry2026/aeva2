#!/bin/bash

# 默认值
VERIFY_STITCH="false"
THINKING="true"
CONTROL_BACKEND="adb"
AGENT_MODEL="REMOTE"
POSITIONAL_ARGS=()

# 解析参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --verify-stitch|-vs|--vs)
      VERIFY_STITCH="true"
      shift
      ;;
    --thinking=*)
      THINKING="${1#*=}"
      shift
      ;;
    --thinking|-t)
      THINKING="true"
      shift
      ;;
    --no-thinking|-nt)
      THINKING="false"
      shift
      ;;
    -b|--backend)
      CONTROL_BACKEND="$2"
      shift
      shift
      ;;
    -m|--model)
      AGENT_MODEL="$2"
      shift
      shift
      ;;
    -h|--help)
      echo "Usage: ./run.sh [options] [goal]"
      echo ""
      echo "Options:"
      echo "  --verify-stitch, -vs    开启决策核验时的图片拼接模式 (BEFORE/AFTER 左右拼接)"
      echo "  --thinking, -t          开启模型思考模式 (默认: true)"
      echo "  --no-thinking, -nt      禁用思考模式"
      echo "  --thinking=true/false   显式指定思考模式"
      echo "  --backend, -b           控制后端 (adb/bridge, 默认: adb)"
      echo "  --model, -m             模型后端 (WIN/REMOTE/GALLERY, 默认: REMOTE)"
      echo "  -h, --help              显示帮助信息"
      exit 0
      ;;
    *)
      POSITIONAL_ARGS+=("$1")
      shift
      ;;
  esac
done

export VERIFY_STITCH=$VERIFY_STITCH
export CONTROL_BACKEND=$CONTROL_BACKEND
export AGENT_MODEL=$AGENT_MODEL

echo "[*] VERIFY_STITCH: $VERIFY_STITCH"
echo "[*] THINKING: $THINKING"
echo "[*] BACKEND: $CONTROL_BACKEND"
echo "[*] MODEL: $AGENT_MODEL"

# 执行 Python 脚本
if [ ${#POSITIONAL_ARGS[@]} -eq 0 ]; then
    python3 humanoid_agent.py --thinking=$THINKING
else
    echo "[*] Using custom goal: ${POSITIONAL_ARGS[*]}"
    python3 humanoid_agent.py --thinking=$THINKING "${POSITIONAL_ARGS[@]}"
fi
