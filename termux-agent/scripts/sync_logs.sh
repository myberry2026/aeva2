#!/usr/bin/env bash
# sync_logs.sh - 从手机同步最新 run_* 日志目录到本地
# 用法: sync_logs.sh <DEVICE_ID> <LOCAL_LOGS_DIR> [loop]
# 如果第三个参数为 "loop"，则每 5 秒循环同步直到被 kill

DEVICE_ID="$1"
LOCAL_LOGS_DIR="$2"
MODE="${3:-once}"  # "once" 或 "loop"

REMOTE_LOGS="/data/data/com.termux/files/home/phone-vision-memory/logs"
TERMUX_BASH="/data/data/com.termux/files/usr/bin/bash"
STAGING="/data/local/tmp/_log_sync"

do_sync() {
    # 找到手机上最新的 run_* 目录
    LATEST_DIR=$(ssh win "adb -s $DEVICE_ID shell 'run-as com.termux $TERMUX_BASH -c \"ls -dt $REMOTE_LOGS/run_* 2>/dev/null | head -n 1\"'" 2>/dev/null | tr -d '\r')
    [ -z "$LATEST_DIR" ] && return 1

    DIR_NAME=$(basename "$LATEST_DIR")
    LOCAL_DIR="$LOCAL_LOGS_DIR/$DIR_NAME"
    mkdir -p "$LOCAL_DIR"

    # 列出远程文件
    REMOTE_FILES=$(ssh win "adb -s $DEVICE_ID shell 'run-as com.termux ls \"$LATEST_DIR/\"'" 2>/dev/null | tr -d '\r')
    [ -z "$REMOTE_FILES" ] && return 1

    SYNCED=0
    for FILE in $REMOTE_FILES; do
        LOCAL_FILE="$LOCAL_DIR/$FILE"
        # 跳过已经存在且大小 >0 的文件 (截图一旦写完不会变)
        if [ -s "$LOCAL_FILE" ]; then
            continue
        fi
        # 通过 run-as cat 复制到 staging，再 adb pull 到 Win，再 scp 到 Mac
        ssh win "adb -s $DEVICE_ID shell 'mkdir -p $STAGING && run-as com.termux cat \"$LATEST_DIR/$FILE\" > \"$STAGING/$FILE\"' && adb -s $DEVICE_ID pull \"$STAGING/$FILE\" \"/tmp/_log_sync_$FILE\"" 2>/dev/null
        # scp 从 Win 到 Mac
        scp -q "win:/tmp/_log_sync_$FILE" "$LOCAL_FILE" 2>/dev/null
        if [ -s "$LOCAL_FILE" ]; then
            SYNCED=$((SYNCED + 1))
        fi
    done
    
    # 对 agent_debug.log 总是重新拉取（因为它会持续增长）
    ssh win "adb -s $DEVICE_ID shell 'run-as com.termux cat \"$LATEST_DIR/agent_debug.log\" > \"$STAGING/agent_debug.log\"' && adb -s $DEVICE_ID pull \"$STAGING/agent_debug.log\" \"/tmp/_log_sync_agent_debug.log\"" 2>/dev/null
    scp -q "win:/tmp/_log_sync_agent_debug.log" "$LOCAL_DIR/agent_debug.log" 2>/dev/null
    
    # 同样处理 agent_responses.log
    ssh win "adb -s $DEVICE_ID shell 'run-as com.termux cat \"$LATEST_DIR/agent_responses.log\" > \"$STAGING/agent_responses.log\"' && adb -s $DEVICE_ID pull \"$STAGING/agent_responses.log\" \"/tmp/_log_sync_agent_responses.log\"" 2>/dev/null
    scp -q "win:/tmp/_log_sync_agent_responses.log" "$LOCAL_DIR/agent_responses.log" 2>/dev/null

    [ $SYNCED -gt 0 ] && echo "[SYNC] +$SYNCED new files -> $LOCAL_DIR" >&2
    return 0
}

if [ "$MODE" = "loop" ]; then
    while true; do
        do_sync
        sleep 5
    done
else
    do_sync
    FILE_COUNT=$(find "$LOCAL_LOGS_DIR" -name "run_*" -type d -exec sh -c 'ls "{}" | wc -l' \; 2>/dev/null | tail -1 | tr -d ' ')
    echo "$FILE_COUNT"
fi
