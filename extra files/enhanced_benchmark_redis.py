import os
import json
import time
import hashlib
import zlib
import redis
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# ----------------------------
# CONFIG
# ----------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ Missing GEMINI_API_KEY in .env")

genai.configure(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_TTL = 3600  # 1 hour sliding window

try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=2)
    r.ping()
    print("✅ Connected to Redis")
except redis.ConnectionError:
    raise RuntimeError(f"❌ Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT}")

INPUT_PRICE_PER_M = 0.30
OUTPUT_PRICE_PER_M = 2.50

# Global stats
cache_stats = {"hits": 0, "misses": 0}

# ----------------------------
# HELPERS
# ----------------------------
def now_str():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

def estimate_cost(input_tokens, output_tokens):
    return (input_tokens / 1_000_000) * INPUT_PRICE_PER_M + (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_M

def compress_data(data: str) -> bytes:
    return zlib.compress(data.encode("utf-8"))

def decompress_data(compressed: bytes) -> str:
    return zlib.decompress(compressed).decode("utf-8")

def get_with_sliding_ttl(key: str, ttl_seconds: int = 3600):
    """Get value and refresh TTL on access."""
    value = r.get(key)
    if value:
        r.expire(key, ttl_seconds)
    return value

def call_llm_with_cache(prompt: str, max_tokens: int = 1000, temperature: float = 0.0):
    # Create deterministic cache key
    key_str = f"toon:{MODEL_NAME}:{max_tokens}:{temperature}:{prompt}"
    cache_key = hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    # Try cache (with sliding TTL)
    compressed = get_with_sliding_ttl(cache_key, REDIS_TTL)
    if compressed:
        cache_stats["hits"] += 1
        print(f"[{now_str()}] 🗃️ CACHE HIT (TTL refreshed)")
        data_str = decompress_data(compressed)
        data = json.loads(data_str)
        return {
            "text": data["text"],
            "from_cache": True,
            "input_tokens": data["input_tokens"],
            "output_tokens": data["output_tokens"],
            "latency": 0.0,
        }

    # Cache miss
    cache_stats["misses"] += 1
    print(f"[{now_str()}] 🌐 CACHE MISS → calling LLM")
    start = time.time()

    model = genai.GenerativeModel(MODEL_NAME)
    safety = {
        genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
    }

    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            top_p=0.95,
        ),
        safety_settings=safety,
    )
    latency = time.time() - start

    # Extract real token counts
    try:
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count
        output_tokens = usage.candidates_token_count
    except Exception:
        input_tokens = len(prompt) // 4
        output_tokens = len(response.text) // 4

    result_text = response.text.strip()

    # Cache only if valid (optional: add TOON validation here)
    cache_value = json.dumps({
        "text": result_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
    })
    r.setex(cache_key, REDIS_TTL, compress_data(cache_value))

    print(f"[{now_str()}] ✅ LLM responded ({input_tokens}i / {output_tokens}o tokens)")
    return {
        "text": result_text,
        "from_cache": False,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency": latency,
    }

# ----------------------------
# TOON CONVERSION FUNCTIONS
# ----------------------------
def json_to_toon(json_str: str):
    prompt = f'''You are an expert data converter. Convert JSON to TOON format.

Rules:
- null → key: null
- Empty array [] → key[0]:
- Quote strings like "007", "1.0", "true", "null"
- Output ONLY TOON, no explanations.

JSON:
{json_str}

TOON:'''
    return call_llm_with_cache(prompt, max_tokens=2000, temperature=0.0)

def toon_to_json(toon_str: str):
    prompt = f'''You are an expert data converter. Convert TOON to valid JSON.

Rules:
- Output ONLY valid JSON. No extra text.
- Preserve quoted strings as strings.
- Empty key: → {{}}
- Use exact list counts.

TOON:
{toon_str}

JSON:'''
    return call_llm_with_cache(prompt, max_tokens=2000, temperature=0.0)

# ----------------------------
# BENCHMARK
# ----------------------------
test_cases = [
    ("User A", '{"name": "Alice", "age": 30}'),
    ("User B", '{"name": "Bob", "score": null}'),
    ("Nested Structures", json.dumps({
        "Heterogeneous Array of Objects": {
            "items": [
                {"type": "book", "title": "The Hobbit", "pages": 310},
                {"type": "movie", "title": "The Matrix", "duration_mins": 136},
                {"type": "audiobook", "title": "Dune", "narrator": "Scott Brick"}
            ]
        }
    }))
    # ("User A again", '{"name": "Alice", "age": 30}'),  # duplicate
]

def run_benchmark():
    total_latency = 0.0
    total_input = 0
    total_output = 0

    for name, json_input in test_cases:
        print(f"\n🧪 [{now_str()}] Running: {name}")
        res = json_to_toon(json_input)
        latency = res["latency"] if not res["from_cache"] else 0.01
        total_latency += latency
        total_input += res["input_tokens"]
        total_output += res["output_tokens"]
        print(f"[{now_str()}] ➤ Output length: {len(res['text'])} | Latency: {latency:.2f}s")

    cost = estimate_cost(total_input, total_output)
    hit_rate = cache_stats["hits"] / (cache_stats["hits"] + cache_stats["misses"]) if (cache_stats["hits"] + cache_stats["misses"]) > 0 else 0
    print(f"\n📊 [{now_str()}] Total latency: {total_latency:.2f}s | Cost: ${cost:.6f} | Hit rate: {hit_rate:.1%}")

# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    print("🚀 TOON Caching Benchmark (Redis + Sliding TTL + Compression)")
    print(f"Model: {MODEL_NAME} | Redis: {REDIS_HOST}:{REDIS_PORT}")

    print(f"\n[{now_str()}] [1/2] First run (populate cache):")
    run_benchmark()

    print(f"\n[{now_str()}] [2/2] Second run (should hit cache for duplicates):")
    run_benchmark()

    print(f"\n✅ Final cache hit rate: {cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses']):.1%}")