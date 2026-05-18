import asyncio
import json
import sys
import websockets

WS_URL = "ws://localhost:8765"

# 消息队列：存放用户输入但还没发出去的消息
message_queue = asyncio.Queue()

async def read_stdin():
    """专门负责读键盘输入的任务"""
    loop = asyncio.get_event_loop()
    print("[input] 键盘监听已就绪。")
    while True:
        # 即使没连上，你也可以在这儿输入
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line: # EOF
            break
        line = line.strip()
        if line:
            await message_queue.put(line)

async def connection_manager():
    """专门负责连接服务器并发送队列消息的任务"""
    print(f"[client] 启动。目标: {WS_URL}")
    
    while True:
        try:
            async with websockets.connect(WS_URL) as ws:
                print(f"\n[client] ✅ 已连接到 {WS_URL}。", flush=True)
                
                # 连上之后，立刻检查队列里有没有积压的消息
                while True:
                    # 从队列拿消息（如果没有消息，这里会异步等待，不阻塞连接）
                    line = await message_queue.get()
                    
                    try:
                        payload = json.dumps({"type": "text", "text": line}, ensure_ascii=False)
                        await ws.send(payload)
                        print(f"[client] → 已发送积压消息: {line}")
                    except Exception as e:
                        # 发送失败，把消息塞回队列头部，等下次连上再发
                        print(f"[client] ❌ 发送失败，消息已回滚到队列: {line}")
                        # 注意：这里需要一个稍微复杂的逻辑把消息插回队首，简单起见我们重新 put
                        await message_queue.put(line)
                        raise e # 抛出异常触发重连
                    finally:
                        # 标记任务完成
                        message_queue.task_done()
                        
        except (ConnectionRefusedError, websockets.exceptions.ConnectionClosedError, OSError):
            # 这里的 print 加上 \r 或者是清除行，避免刷屏
            sys.stdout.write(f"\r[client] 🔌 等待 Server 启动... (队列中积压: {message_queue.qsize()} 条)   ")
            sys.stdout.flush()
            await asyncio.sleep(2)
        except Exception as e:
            print(f"\n[client] ❌ 异常: {type(e).__name__}: {e}")
            await asyncio.sleep(2)

async def main():
    # 同时跑两个任务
    await asyncio.gather(
        read_stdin(),
        connection_manager()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[client] bye")
