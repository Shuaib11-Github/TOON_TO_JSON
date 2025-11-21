import os
import json
import time
import hashlib
import redis
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

# Redis config
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_TTL = 3600  # 1 hour

# Connect to Redis
try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_connect_timeout=2)
    r.ping()  # Test connection
    print("✅ Connected to Redis")
except redis.ConnectionError:
    raise RuntimeError(f"❌ Failed to connect to Redis at {REDIS_HOST}:{REDIS_PORT}")

# Pricing (Together AI style, but Gemini used here for demo)
INPUT_PRICE_PER_M = 0.30
OUTPUT_PRICE_PER_M = 2.50

# ----------------------------
# HELPERS
# ----------------------------
def estimate_cost(input_tokens, output_tokens):
    return (input_tokens / 1_000_000) * INPUT_PRICE_PER_M + (output_tokens / 1_000_000) * OUTPUT_PRICE_PER_M

def rough_token_count(text):
    return max(1, len(text) // 4)

def call_gemini_raw(prompt, max_tokens=1000, temperature=0.0):
    model = genai.GenerativeModel(MODEL_NAME)
    safety = {
        genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_NONE,
        genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_NONE,
    }
    try:
        # Simulate real latency (optional — remove in prod)
        print("  🌐 Calling LLM (simulated delay)...")
        time.sleep(2)  # Make LLM calls visibly slow

        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
                top_p=0.95,
            ),
            safety_settings=safety,
        )
        return response.text.strip()
    except Exception as e:
        print(f"⚠️ LLM Error: {e}")
        return ""

def call_gemini_with_redis(prompt, max_tokens=1000, temperature=0.0):
    # Create cache key
    key_str = f"llm:{MODEL_NAME}:{prompt}:{max_tokens}:{temperature}"
    cache_key = hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    # Try cache
    cached = r.get(cache_key)
    if cached:
        print("  🗃️ CACHE HIT")
        data = json.loads(cached)
        return {
            "text": data["text"],
            "from_cache": True,
            "input_tokens": data["input_tokens"],
            "output_tokens": data["output_tokens"],
            "latency": 0.0,
        }

    # Cache miss → call LLM
    print("  🌐 CACHE MISS → calling LLM")
    start = time.time()
    result = call_gemini_raw(prompt, max_tokens, temperature)
    latency = time.time() - start

    input_tokens = rough_token_count(prompt)
    output_tokens = rough_token_count(result)

    # Save to Redis
    r.setex(
        cache_key,
        REDIS_TTL,
        json.dumps({
            "text": result,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        })
    )

    return {
        "text": result,
        "from_cache": False,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency": latency,
    }

# ----------------------------
# TEST PROMPTS
# ----------------------------
test_prompts = [
    ("Simple JSON", '{"name": "Alice", "age": 30}'),
    ("Edge case", '{"value": "null", "flag": "true"}'),
    ("Nested Structures", json.dumps({
        "Heterogeneous Array of Objects": {
            "items": [
                {"type": "book", "title": "The Hobbit", "pages": 310},
                {"type": "movie", "title": "The Matrix", "duration_mins": 136},
                {"type": "audiobook", "title": "Dune", "narrator": "Scott Brick"}
            ]
        }
    }))
]
   
# ----------------------------
def run_benchmark():
    total_latency = 0.0
    total_input = 0
    total_output = 0

    for name, prompt in test_prompts:
        print(f"\n🧪 Running: {name}")
        res = call_gemini_with_redis(prompt)
        latency = res["latency"] if not res["from_cache"] else 0.01  # near-zero for cache
        total_latency += latency
        total_input += res["input_tokens"]
        total_output += res["output_tokens"]

        print(f"  Result length: {len(res['text'])} chars")
        print(f"  Latency: {latency:.2f}s")

    cost = estimate_cost(total_input, total_output)
    print(f"\n📊 Total latency: {total_latency:.2f}s | Est. cost: ${cost:.6f}")

# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    print("🚀 LLM Benchmark with Redis Caching")
    print(f"Model: {MODEL_NAME} | Redis: {REDIS_HOST}:{REDIS_PORT}")

    print("\n[1/2] First run (populate cache):")
    run_benchmark()

    print("\n[2/2] Second run (should hit cache):")
    run_benchmark()

    print(f"\n✅ Cache keys expire in {REDIS_TTL} seconds")