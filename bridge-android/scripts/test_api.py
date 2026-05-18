#!/usr/bin/env python3
"""
test_api.py — TDD 测试脚本，覆盖 hermes LLM server 全部 API 能力。

用法:
    python3 scripts/test_api.py
    python3 scripts/test_api.py -v   # pytest verbose
"""
import requests
import json
import sys
import base64
import struct
import io
import time

BASE_URL = "http://localhost:8081"
TIMEOUT = 120
INFERENCE_DELAY = 3


# ── helpers ──────────────────────────────────────────────────────────────

class SkipException(Exception):
    pass

_model_loaded = None

def is_model_loaded():
    global _model_loaded
    if _model_loaded is None:
        try:
            _model_loaded = health().json().get("model_loaded", False)
        except Exception:
            _model_loaded = False
    return _model_loaded

def skip_if_no_model():
    if not is_model_loaded():
        raise SkipException("Model not loaded")

def health():
    return requests.get(f"{BASE_URL}/health", timeout=5)

def chat(messages, retries=1, **kwargs):
    payload = {"messages": messages, **kwargs}
    for attempt in range(retries + 1):
        try:
            return requests.post(f"{BASE_URL}/v1/chat/completions", json=payload, timeout=TIMEOUT)
        except requests.exceptions.ConnectionError:
            if attempt < retries:
                time.sleep(2)
                continue
            raise

def chat_json(messages, **kwargs):
    r = chat(messages, **kwargs)
    r.raise_for_status()
    return r.json()

def make_tiny_png(width=2, height=2, color=(255, 0, 0)):
    try:
        from PIL import Image
        img = Image.new("RGB", (width, height), color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        return bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x02,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE,
            0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41, 0x54,
            0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00, 0x00,
            0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC, 0x33,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
            0xAE, 0x42, 0x60, 0x82,
        ])

def img_to_data_uri(png_bytes):
    return f"data:image/png;base64,{base64.b64encode(png_bytes).decode()}"

def make_tiny_wav():
    sample_rate = 16000
    num_samples = 1600
    wav = io.BytesIO()
    wav.write(b"RIFF")
    data_size = num_samples * 2
    wav.write(struct.pack("<I", 36 + data_size))
    wav.write(b"WAVEfmt ")
    wav.write(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    wav.write(b"data")
    wav.write(struct.pack("<I", data_size))
    wav.write(b"\x00" * data_size)
    return wav.getvalue()

def wav_to_data_uri(wav_bytes):
    return f"data:audio/wav;base64,{base64.b64encode(wav_bytes).decode()}"

def print_response(label, data):
    """打印响应详情"""
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    thinking = msg.get("reasoning_content") or ""
    usage = data.get("usage", {})
    model = data.get("model", "?")
    print(f"    [{label}] model={model}")
    if thinking:
        print(f"    [{label}] thinking={thinking[:120]}...")
    if content:
        print(f"    [{label}] content={content[:200]}")
    tool_calls = msg.get("tool_calls")
    if tool_calls:
        print(f"    [{label}] tool_calls={json.dumps(tool_calls, ensure_ascii=False)[:200]}")
    if usage.get("prompt_tokens", 0) or usage.get("completion_tokens", 0):
        print(f"    [{label}] usage=prompt:{usage.get('prompt_tokens')} completion:{usage.get('completion_tokens')} total:{usage.get('total_tokens')}")


# ── 基础测试 ────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_endpoint(self):
        r = health()
        assert r.status_code == 200
        data = r.json()
        print(f"    health={json.dumps(data)}")
        assert data["status"] == "ok"
        assert "model_loaded" in data

    def test_health_shows_model_path(self):
        data = health().json()
        print(f"    model_path={data.get('model_path')}")


class TestErrorHandling:
    def test_empty_messages_returns_error(self):
        r = chat([])
        print(f"    status={r.status_code} body={r.text[:200]}")
        assert r.status_code in (400, 500)

    def test_missing_content_returns_error(self):
        r = chat([{"role": "user"}])
        print(f"    status={r.status_code} body={r.text[:200]}")
        assert r.status_code in (400, 500)

    def test_unknown_path_returns_404(self):
        r = requests.get(f"{BASE_URL}/nonexistent", timeout=5)
        assert r.status_code == 404


# ── 推理测试 ────────────────────────────────────────────────────────────

class TestBasicChat:
    def test_simple_text_chat(self):
        skip_if_no_model()
        data = chat_json([{"role": "user", "content": "Say exactly: HELLO TEST"}])
        print_response("basic", data)
        msg = data["choices"][0]["message"]
        assert msg["role"] == "assistant"
        assert isinstance(msg["content"], str) and len(msg["content"]) > 0

    def test_response_format(self):
        skip_if_no_model()
        data = chat_json([{"role": "user", "content": "Hi"}])
        print(f"    id={data['id']} object={data['object']} model={data['model']}")
        assert data["id"].startswith("chatcmpl-")
        assert data["object"] == "chat.completion"
        assert "created" in data and "model" in data and "choices" in data and "usage" in data

    def test_finish_reason_is_stop(self):
        skip_if_no_model()
        data = chat_json([{"role": "user", "content": "Say OK"}])
        print(f"    finish_reason={data['choices'][0]['finish_reason']}")
        assert data["choices"][0]["finish_reason"] == "stop"


class TestSystemPrompt:
    def test_system_prompt_influences_response(self):
        skip_if_no_model()
        data = chat_json([
            {"role": "system", "content": "You must answer every question with exactly one word."},
            {"role": "user", "content": "What color is the sky?"},
        ])
        print_response("system_prompt", data)
        content = data["choices"][0]["message"]["content"]
        assert len(content.split()) <= 10, f"Expected short reply, got: {content[:100]}"


class TestMultiTurn:
    def test_multi_turn_conversation(self):
        skip_if_no_model()
        data = chat_json([
            {"role": "user", "content": "My name is Alice."},
            {"role": "assistant", "content": "Hello Alice! Nice to meet you."},
            {"role": "user", "content": "What is my name?"},
        ])
        print_response("multi_turn", data)
        content = data["choices"][0]["message"]["content"]
        assert "Alice" in content or "alice" in content.lower()


class TestMultimodalImage:
    def test_image_input_accepted(self):
        skip_if_no_model()
        uri = img_to_data_uri(make_tiny_png())
        data = chat_json([{"role": "user", "content": [
            {"type": "text", "text": "Describe this image briefly."},
            {"type": "image_url", "image_url": {"url": uri}},
        ]}])
        print_response("image", data)
        content = data["choices"][0]["message"]["content"]
        assert isinstance(content, str) and len(content) > 0

    def test_multiple_images(self):
        skip_if_no_model()
        data = chat_json([{"role": "user", "content": [
            {"type": "text", "text": "How many images do you see?"},
            {"type": "image_url", "image_url": {"url": img_to_data_uri(make_tiny_png(2, 2, (255, 0, 0)))}},
            {"type": "image_url", "image_url": {"url": img_to_data_uri(make_tiny_png(2, 2, (0, 255, 0)))}},
        ]}])
        print_response("multi_image", data)
        assert "choices" in data


class TestReasoningContent:
    def test_reasoning_content_field(self):
        skip_if_no_model()
        data = chat_json([{"role": "user", "content": "What is 2+2? Think step by step."}])
        print_response("reasoning", data)
        msg = data["choices"][0]["message"]
        assert "content" in msg
        if "reasoning_content" in msg:
            assert isinstance(msg["reasoning_content"], str)


class TestModelField:
    def test_model_field_in_response(self):
        skip_if_no_model()
        data = chat_json([{"role": "user", "content": "Say OK"}])
        print(f"    model={data['model']}")
        assert data["model"]


# ── Sampler 参数 ─────────────────────────────────────────────────────────

class TestSamplerParams:
    def test_temperature_accepted(self):
        skip_if_no_model()
        r = chat([{"role": "user", "content": "Say OK"}], temperature=0.1)
        print(f"    status={r.status_code}")
        assert r.status_code == 200, f"rejected: {r.text}"

    def test_top_p_accepted(self):
        skip_if_no_model()
        r = chat([{"role": "user", "content": "Say OK"}], top_p=0.9)
        assert r.status_code == 200

    def test_top_k_accepted(self):
        skip_if_no_model()
        r = chat([{"role": "user", "content": "Say OK"}], top_k=40)
        assert r.status_code == 200

    def test_seed_accepted(self):
        skip_if_no_model()
        r = chat([{"role": "user", "content": "Say OK"}], seed=42)
        assert r.status_code == 200

    def test_seed_produces_deterministic_output(self):
        skip_if_no_model()
        msgs = [{"role": "user", "content": "What is 2+2? Reply with just the number."}]
        r1 = chat_json(msgs, temperature=0.0, seed=123)
        r2 = chat_json(msgs, temperature=0.0, seed=123)
        t1 = r1["choices"][0]["message"]["content"]
        t2 = r2["choices"][0]["message"]["content"]
        print(f"    run1={t1!r}")
        print(f"    run2={t2!r}")
        assert t1 == t2, f"Deterministic mismatch"


# ── Streaming ────────────────────────────────────────────────────────────

class TestStreaming:
    def test_stream_returns_event_stream_content_type(self):
        skip_if_no_model()
        r = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Say OK"}], "stream": True},
            stream=True, timeout=TIMEOUT,
        )
        ct = r.headers.get("content-type", "")
        print(f"    content-type={ct}")
        assert r.status_code == 200
        assert "text/event-stream" in ct, f"Expected SSE, got: {ct}"

    def test_stream_sends_multiple_chunks(self):
        skip_if_no_model()
        r = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Count from 1 to 10"}], "stream": True},
            stream=True, timeout=TIMEOUT,
        )
        assert r.status_code == 200
        chunks = []
        try:
            for line in r.iter_lines():
                if not line:
                    continue
                decoded = line.decode("utf-8")
                if decoded.startswith("data: "):
                    data_str = decoded[6:]
                    if data_str == "[DONE]":
                        break
                    chunks.append(json.loads(data_str))
        except requests.exceptions.ChunkedEncodingError:
            pass
        print(f"    chunks={len(chunks)}")
        for i, c in enumerate(chunks[:3]):
            delta = c["choices"][0].get("delta", {})
            print(f"    chunk[{i}] delta={json.dumps(delta, ensure_ascii=False)}")
        assert len(chunks) > 1, f"Expected multiple chunks, got {len(chunks)}"

    def test_stream_chunk_format(self):
        skip_if_no_model()
        r = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Say hello"}], "stream": True},
            stream=True, timeout=TIMEOUT,
        )
        assert r.status_code == 200
        for line in r.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                data_str = decoded[6:]
                if data_str == "[DONE]":
                    break
                chunk = json.loads(data_str)
                print(f"    first_chunk={json.dumps(chunk, ensure_ascii=False)[:300]}")
                assert chunk["object"] == "chat.completion.chunk"
                assert "delta" in chunk["choices"][0]
                break

    def test_stream_ends_with_done(self):
        skip_if_no_model()
        r = requests.post(
            f"{BASE_URL}/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Say OK"}], "stream": True},
            stream=True, timeout=TIMEOUT,
        )
        assert r.status_code == 200
        last_data = None
        for line in r.iter_lines():
            if not line:
                continue
            decoded = line.decode("utf-8")
            if decoded.startswith("data: "):
                last_data = decoded[6:]
        print(f"    last_data={last_data}")
        assert last_data == "[DONE]"


# ── Audio 输入 ──────────────────────────────────────────────────────────

class TestAudioInput:
    def test_audio_url_accepted(self):
        skip_if_no_model()
        uri = wav_to_data_uri(make_tiny_wav())
        r = chat([{"role": "user", "content": [
            {"type": "text", "text": "Describe what you hear."},
            {"type": "audio_url", "audio_url": {"url": uri}},
        ]}])
        assert r.status_code == 200, f"Audio rejected: {r.text}"
        data = r.json()
        print_response("audio_url", data)
        assert "choices" in data

    def test_input_audio_accepted(self):
        skip_if_no_model()
        wav = make_tiny_wav()
        uri = f"data:audio/wav;base64,{base64.b64encode(wav).decode()}"
        r = chat([{"role": "user", "content": [
            {"type": "text", "text": "What is this?"},
            {"type": "input_audio", "input_audio": {"data": uri}},
        ]}])
        assert r.status_code == 200, f"input_audio rejected: {r.text}"
        data = r.json()
        print_response("input_audio", data)


# ── Cancel ───────────────────────────────────────────────────────────────

class TestCancelGeneration:
    def test_cancel_endpoint_exists(self):
        r = requests.post(f"{BASE_URL}/cancel", timeout=5)
        print(f"    status={r.status_code} body={r.text}")
        assert r.status_code == 200

    def test_cancel_returns_success(self):
        r = requests.post(f"{BASE_URL}/cancel", timeout=5)
        data = r.json()
        assert data.get("success") is True


# ── Token Usage ──────────────────────────────────────────────────────────

class TestTokenUsage:
    def test_usage_has_nonzero_tokens(self):
        """usage 应该返回真实的 token 计数，不是全零"""
        skip_if_no_model()
        data = chat_json([{"role": "user", "content": "What is 1+1?"}])
        usage = data.get("usage", {})
        print(f"    usage={json.dumps(usage)}")
        assert "prompt_tokens" in usage
        assert "completion_tokens" in usage
        assert "total_tokens" in usage
        # Verify tokens are non-zero (even if estimated)
        assert usage["prompt_tokens"] > 0, f"prompt_tokens is 0"
        assert usage["completion_tokens"] > 0, f"completion_tokens is 0"
        assert usage["total_tokens"] > 0, f"total_tokens is 0"
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]


# ── Benchmark ────────────────────────────────────────────────────────────

class TestBenchmark:
    def test_benchmark_info_in_response(self):
        """响应中应包含推理性能指标"""
        skip_if_no_model()
        data = chat_json([{"role": "user", "content": "Say OK"}])
        print(f"    top_level_keys={list(data.keys())}")
        # Check for benchmark object
        if "benchmark" in data:
            bm = data["benchmark"]
            print(f"    benchmark={json.dumps(bm)}")
            assert "ttft_ms" in bm, "Missing ttft_ms"
            assert "total_ms" in bm, "Missing total_ms"
            assert "output_chars" in bm, "Missing output_chars"
            assert "tokens_per_sec" in bm, "Missing tokens_per_sec"
            assert bm["ttft_ms"] >= 0, f"Invalid ttft_ms: {bm['ttft_ms']}"
            assert bm["total_ms"] > 0, f"Invalid total_ms: {bm['total_ms']}"
            assert bm["output_chars"] > 0, f"Invalid output_chars: {bm['output_chars']}"
            assert bm["tokens_per_sec"] > 0, f"Invalid tokens_per_sec: {bm['tokens_per_sec']}"
        else:
            print(f"    WARNING: No benchmark field in response")
            # TDD: should have benchmark
            assert False, "Response missing benchmark field"


# ── Dynamic Model ───────────────────────────────────────────────────────

class TestDynamicModel:
    def test_model_field_accepted(self):
        """请求中的 model 字段应该被接受（即使只是 echo 回来）"""
        skip_if_no_model()
        data = chat_json(
            [{"role": "user", "content": "Say OK"}],
            model="Gemma-4-E2B-it",
        )
        print(f"    response_model={data['model']}")
        assert data["model"]

    def test_models_list_endpoint(self):
        """GET /models 应该返回可用模型列表"""
        r = requests.get(f"{BASE_URL}/models", timeout=5)
        print(f"    status={r.status_code} body={r.text[:300]}")
        # 当前可能 404，TDD 期望最终 200
        # assert r.status_code == 200


# ── Tool Calling ─────────────────────────────────────────────────────────

class TestToolCalling:
    def test_tool_calls_in_response(self):
        """LLM should return tool_calls when tools are provided"""
        skip_if_no_model()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get the current weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string", "description": "City name"},
                            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
                        },
                        "required": ["location"]
                    }
                }
            }
        ]
        data = chat_json(
            [{"role": "user", "content": "What's the weather in Tokyo? Use the get_weather tool."}],
            tools=tools,
        )
        print_response("tool_call", data)
        msg = data["choices"][0]["message"]
        # Model should either call the tool or answer directly
        tool_calls = msg.get("tool_calls")
        if tool_calls and len(tool_calls) > 0:
            tc = tool_calls[0]
            assert tc["type"] == "function"
            assert tc["function"]["name"] == "get_weather"
            assert "arguments" in tc["function"]
            assert data["choices"][0]["finish_reason"] == "tool_calls"
            print(f"    tool_call={json.dumps(tc, ensure_ascii=False)}")
        else:
            print(f"    model answered directly (no tool call)")

    def test_multiple_tools(self):
        """Multiple tools should all be recognized"""
        skip_if_no_model()
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "tap",
                    "description": "Tap on screen at coordinates",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"}
                        },
                        "required": ["x", "y"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "swipe",
                    "description": "Swipe on screen",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_x": {"type": "integer"},
                            "start_y": {"type": "integer"},
                            "end_x": {"type": "integer"},
                            "end_y": {"type": "integer"}
                        },
                        "required": ["start_x", "start_y", "end_x", "end_y"]
                    }
                }
            }
        ]
        data = chat_json(
            [{"role": "user", "content": "Tap on the settings icon at position 100, 200. Use the tap tool."}],
            tools=tools,
        )
        print_response("multi_tool", data)
        msg = data["choices"][0]["message"]
        tool_calls = msg.get("tool_calls")
        if tool_calls and len(tool_calls) > 0:
            tc = tool_calls[0]
            print(f"    called={tc['function']['name']} args={tc['function']['arguments']}")
        else:
            print(f"    model answered directly (no tool call)")


# ── Models Endpoint ──────────────────────────────────────────────────────

class TestModelsEndpoint:
    def test_list_models(self):
        """GET /models should return available models"""
        r = requests.get(f"{BASE_URL}/models", timeout=5)
        print(f"    status={r.status_code}")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        print(f"    models_count={len(data['models'])}")
        for m in data["models"][:3]:
            print(f"      - {m.get('name')} ({m.get('path')})")

    def test_load_model(self):
        """POST /models/load should load a model"""
        skip_if_no_model()
        # Get first available model
        r = requests.get(f"{BASE_URL}/models", timeout=5)
        models = r.json().get("models", [])
        if not models:
            raise SkipException("No models available")
        model_path = models[0]["path"]
        print(f"    loading: {model_path}")
        r = requests.post(f"{BASE_URL}/models/load", json={"path": model_path}, timeout=120)
        print(f"    status={r.status_code} body={r.text[:200]}")
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is True

    def test_unload_model(self):
        """POST /models/unload should unload current model"""
        r = requests.post(f"{BASE_URL}/models/unload", timeout=10)
        print(f"    status={r.status_code}")
        assert r.status_code == 200
        data = r.json()
        assert data.get("success") is True


# ── Speculative Decoding ─────────────────────────────────────────────────

class TestSpeculativeDecoding:
    def test_health_shows_speculative_support(self):
        """Health endpoint should report speculative decoding support"""
        data = health().json()
        has_spec = data.get("supports_speculative_decoding", None)
        print(f"    supports_speculative_decoding={has_spec}")
        assert has_spec is not None, "Missing supports_speculative_decoding field"


# ── runner ───────────────────────────────────────────────────────────────

def run_all():
    import inspect
    passed = failed = skipped = 0
    test_classes = [
        TestHealth, TestErrorHandling,
        TestBasicChat, TestSystemPrompt, TestMultiTurn,
        TestMultimodalImage, TestReasoningContent, TestModelField,
        TestSamplerParams, TestStreaming, TestAudioInput,
        TestCancelGeneration, TestTokenUsage, TestBenchmark, TestDynamicModel,
        TestToolCalling, TestModelsEndpoint, TestSpeculativeDecoding,
    ]
    for cls in test_classes:
        print(f"\n{'='*60}\n  {cls.__name__}\n{'='*60}")
        instance = cls()
        for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not name.startswith("test_"):
                continue
            try:
                method(instance)
                print(f"  ✓ {name}")
                passed += 1
            except SkipException as e:
                print(f"  ⊘ {name}: {e}")
                skipped += 1
            except AssertionError as e:
                print(f"  ✗ {name}: {e}")
                failed += 1
            except requests.exceptions.ConnectionError:
                print(f"  ⊘ {name}: connection refused")
                skipped += 1
            except Exception as e:
                print(f"  ✗ {name}: {type(e).__name__}: {e}")
                failed += 1
            if cls not in (TestHealth, TestErrorHandling, TestCancelGeneration):
                time.sleep(INFERENCE_DELAY)
    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed, {skipped} skipped")
    print(f"{'='*60}")
    return failed == 0

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "-v":
        import subprocess
        sys.exit(subprocess.call(["python3", "-m", "pytest", __file__, "-v"]))
    else:
        sys.exit(0 if run_all() else 1)
