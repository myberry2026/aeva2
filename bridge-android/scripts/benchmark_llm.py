import requests
import json
import time
import statistics

def benchmark_hermes(port=8081, rounds=3):
    url = f"http://localhost:{port}/v1/chat/completions"
    prompt = "Explain quantum entanglement in one paragraph."
    
    print(f"🚀 Starting Benchmark on port {port} ({rounds} rounds)...")
    print(f"Target Prompt: {prompt}\n")
    
    results = []
    
    for i in range(rounds):
        print(f"Round {i+1}/{rounds}...", end="", flush=True)
        
        start_time = time.time()
        try:
            response = requests.post(
                url,
                json={
                    "model": "Gemma-4-E2B-it",
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=120
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                
                # Rough Token Estimation: ~4 characters per token
                char_count = len(content)
                word_count = len(content.split())
                est_tokens = max(word_count * 1.3, char_count / 4) 
                
                tps = est_tokens / elapsed
                results.append({
                    "elapsed": elapsed,
                    "tokens": est_tokens,
                    "tps": tps
                })
                print(f" Done! {tps:.2f} tokens/sec ({elapsed:.2f}s)")
            else:
                print(f" Failed! HTTP {response.status_code}")
        except Exception as e:
            print(f" Error: {e}")

    if results:
        avg_tps = statistics.mean([r["tps"] for r in results])
        avg_time = statistics.mean([r["elapsed"] for r in results])
        print(f"\n{'-'*30}")
        print(f"📊 BENCHMARK SUMMARY")
        print(f"Avg Speed: {avg_tps:.2f} tokens/sec")
        print(f"Avg Latency: {avg_time:.2f} seconds")
        print(f"{'-'*30}")
    else:
        print("\nNo successful rounds to summarize.")

if __name__ == "__main__":
    benchmark_hermes()
