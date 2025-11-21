import os
import re
import json
import time
import hashlib
import zlib
import redis
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from toon_format import encode, decode

# ----------------------------
# LOAD CONFIG
# ----------------------------
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ Missing GEMINI_API_KEY in .env file")

genai.configure(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"

# Sanitize model name for log file
def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

safe_model_name = sanitize_filename(MODEL_NAME)
LOG_FILE = f"full_test_run_log_{safe_model_name}_final_caching.txt"

# ----------------------------
# REDIS SETUP
# ----------------------------
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_TTL = 3600  # 1 hour (sliding)

try:
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=2)
    r.ping()
    print("✅ Connected to Redis")
except Exception as e:
    raise RuntimeError(f"❌ Redis connection failed: {e}")

# Cache stats
cache_stats = {"hits": 0, "misses": 0}

# ----------------------------
# COMPRESSION HELPERS
# ----------------------------
def _compress_cache_value(data: dict) -> bytes:
    return zlib.compress(json.dumps(data).encode("utf-8"))

def _decompress_cache_value(compressed: bytes) -> dict:
    return json.loads(zlib.decompress(compressed).decode("utf-8"))

# ============================================================================
# PROMPT 1: JSON → TOON CONVERSION (ENCODING)
# (Your prompt remains unchanged)
# ============================================================================
json_to_toon_prompt_base = '''You are an expert data converter. You convert JSON to the TOON format, EXACTLY replicating the official library's style.

CRITICAL RULES:
1.  **Handling `null`:** A JSON `null` value is ALWAYS written as `key: null`. It is NEVER an empty key.
2.  **Handling Empty Objects/Arrays:**
    - An empty JSON object `{}` becomes `key:` on a line by itself.
    - An empty JSON array `[]` becomes `key[0]:`.
3.  **Choosing Array Format (VERY IMPORTANT):**
    - **Use Compact Table (`key[n]{...}:`)** ONLY for arrays of objects that are simple, flat, and have IDENTICAL keys.
    - **Use Block Style (`- key: value`)** for everything else: arrays with complex nested objects, arrays with nested lists, or arrays where objects have DIFFERENT keys.
4.  **Preserving String Types:** If a JSON string value could be misinterpreted (e.g., "007", "1.0", "true", "null"), it MUST be wrapped in double quotes in the TOON output.
5.  **Quoting Special Characters:** If a JSON string contains special characters like `:`, `{`, `}`, `[`, `]`, `\n` (newline), it MUST be wrapped in double quotes in the TOON output to avoid ambiguity.

EXAMPLES:

Example 1 (Compact Table Style for Simple, Uniform Arrays):
JSON:
[
  { "event": "login", "user_id": 101, "success": true },
  { "event": "logout", "user_id": 101, "success": true }
]
TOON:
[2]{event,user_id,success}:
  login,101,true
  logout,101,true

Example 2 (Block Style for Complex/Nested Arrays):
JSON:
{
  "users": [
    { "id": 201, "name": "Maya", "age": null, "goals": ["weight_loss", "strength"] },
    { "id": 202, "name": "Ravi", "age": 35, "goals": ["running"] }
  ]
}
TOON:
users[2]:
  - id: 201
    name: Maya
    age: null
    goals[2]: weight_loss,strength
  - id: 202
    name: Ravi
    age: 35
    goals[1]: running

Example 3 (Handling `null`, Empty Arrays, and Quoted Strings):
JSON:
{
  "id": "user-123",
  "preferences": {
    "tags": [],
    "history": null,
    "version": "1.0"
  }
}
TOON:
id: user-123
preferences:
  tags[0]:
  history: null
  version: "1.0"

Example 4 (Quoting for Special Characters):
JSON:
{
  "trigger": "push:main",
  "command": "docker build -t my-app:latest ."
}
TOON:
trigger: "push:main"
command: "docker build -t my-app:latest ."

Now convert the following JSON to TOON. Output ONLY TOON.
'''

# ============================================================================
# PROMPT 2: TOON → JSON CONVERSION (DECODING)
# (Your prompt remains unchanged)
# ============================================================================
toon_to_json_prompt_base = '''You are an expert data converter. Convert TOON to valid JSON.

RULES:
- `key: value` → simple field (string/number/bool)
- `key:` → object with indented sub-fields
- `list[n]{...}:` → array of objects
- A key on a line by itself (`key:`) with no indented content → convert to an empty object `{}`
- Empty values in data rows (e.g., `, ,`) → convert to `null` in JSON
- **CRITICAL RULE #1: A value wrapped in double quotes in TOON (e.g., `"true"`, `"123"`) MUST be output as a JSON string. DO NOT convert it to another data type.**
- **CRITICAL RULE #2: The number 'n' in a list declaration like `key[n]:` is the PRECISE number of elements. The list MUST have exactly 'n' elements in the final JSON, no more and no less.**
- Strings must be quoted in the final JSON; numbers/booleans unquoted.
- Output ONLY valid JSON. No extra text.

EXAMPLES:

Example 1:
TOON:
app: FitTrack
users[2]{id,name}:
1,Alice
2,Bob

JSON:
{
  "app": "FitTrack",
  "users": [
    { "id": 1, "name": "Alice" },
    { "id": 2, "name": "Bob" }
  ]
}

Example 2:
TOON:
users[3]{id,name,role}:
1,Sreeni,admin
2,Krishna,admin
3,Aaron,user

JSON:
{
  "users": [
    { "id": 1, "name": "Sreeni", "role": "admin" },
    { "id": 2, "name": "Krishna", "role": "admin" },
    { "id": 3, "name": "Aaron", "role": "user" }
  ]
}

Example 3:
TOON:
project:
  name: Apollo
  team[1]{id,contact}:
    101,contact{email}:
      alice@ex.com

JSON:
{
  "project": {
    "name": "Apollo",
    "team": [
      {
        "id": 101,
        "contact": { "email": "alice@ex.com" }
      }
    ]
  }
}

Example 4:
TOON:
config:
  debug: true
  tags: web,api,auth

JSON:
{
  "config": {
    "debug": true,
    "tags": ["web", "api", "auth"]
  }
}

Example 5:
TOON:
app: HealthApp
users[2]{id,name,age}:
  301,Alex,
  302,Sam,29

JSON:
{
  "app": "HealthApp",
  "users": [
    { "id": 301, "name": "Alex", "age": null },
    { "id": 302, "name": "Sam", "age": 29 }
  ]
}

Example 6 (Empty Object):
TOON:
pipeline:
  name: deploy-prod
  config:
  steps: 10

JSON:
{
  "pipeline": {
    "name": "deploy-prod",
    "config": {},
    "steps": 10
  }
}

Example 7 (Preserving String Types):
TOON:
config:
  force_string: "true"
  id_code: "009"
  message: "null"
  is_real: true

JSON:
{
  "config": {
    "force_string": "true",
    "id_code": "009",
    "message": "null",
    "is_real": true
  }
}

Example 8 (Lists with Nulls and Exact Counts):
TOON:
data:
  scores[4]: 100,95,null,80
  tags[0]:

JSON:
{
  "data": {
    "scores": [100, 95, null, 80],
    "tags": []
  }
}

Now convert the following TOON to JSON. Output ONLY valid JSON. No extra text.
'''

# ----------------------------
# CACHED LLM CALL
# ----------------------------
def call_gemini_cached(prompt, max_tokens=4000, temperature=0.0, retries=3, delay=5):
    key_str = f"toon:{MODEL_NAME}:{max_tokens}:{temperature}:{prompt}"
    cache_key = hashlib.sha256(key_str.encode("utf-8")).hexdigest()

    # Check cache with sliding TTL
    compressed = r.get(cache_key)
    if compressed:
        r.expire(cache_key, REDIS_TTL)  # Refresh TTL
        cache_stats["hits"] += 1
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🗃️ CACHE HIT")
        return _decompress_cache_value(compressed)["text"]

    cache_stats["misses"] += 1
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🌐 CACHE MISS → calling LLM")

    for attempt in range(retries):
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.95,
                ),
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                }
            )
            result_text = response.text.strip()
            if result_text:
                # Use real token counts if available
                try:
                    usage = response.usage_metadata
                    input_tokens = usage.prompt_token_count
                    output_tokens = usage.candidates_token_count
                except:
                    input_tokens = len(prompt) // 4
                    output_tokens = len(result_text) // 4

                # Cache with compression
                cache_value = {"text": result_text, "input_tokens": input_tokens, "output_tokens": output_tokens}
                r.setex(cache_key, REDIS_TTL, _compress_cache_value(cache_value))
                return result_text

        except Exception as e:
            if attempt < retries - 1:
                time.sleep(delay)
    return ""

# ----------------------------
# TEST FUNCTION
# ----------------------------
def run_test_case(python_data, test_name="Test"):

    # Store initial cache stats
    initial_misses = cache_stats["misses"]

    print(f"\n{'='*90}")
    print(f"🧪 RUNNING: {test_name}")
    print('='*90)

    json_A_original = json.dumps(python_data, indent=2)
    toon_out_official = encode(python_data)

    # DECODING TEST
    print(">>> RUNNING DECODING TEST (TOON → JSON)")
    conv_prompt = toon_to_json_prompt_base + "\n" + toon_out_official
    json_B_from_llm = call_gemini_cached(conv_prompt, max_tokens=4000, temperature=0.0)
    json_B_from_llm = json_B_from_llm.replace("```json", "").replace("```", "").strip()

    decode_passed = False
    if json_B_from_llm:
        try:
            original_data = json.loads(json_A_original)
            llm_decoded_data = json.loads(json_B_from_llm)
            decode_passed = (original_data == llm_decoded_data)
        except:
            pass

    time.sleep(5)

    # ENCODING TEST
    print("\n>>> RUNNING ENCODING TEST (JSON → TOON)")
    encode_prompt = json_to_toon_prompt_base + "\n" + json_A_original
    toon_out_from_llm = call_gemini_cached(encode_prompt, max_tokens=4000, temperature=0.0)
    toon_out_from_llm = toon_out_from_llm.replace("```toon", "").replace("```", "").strip()

    encode_passed = False
    if toon_out_from_llm:
        try:
            encode_passed = (decode(toon_out_from_llm) == python_data)
        except:
            pass

    # Log
    json_bytes = len(json_A_original.encode('utf-8'))
    toon_bytes = len(toon_out_official.encode('utf-8'))
    reduction = (1 - toon_bytes / json_bytes) * 100 if json_bytes > 0 else 0

    log_lines = [
        f"\n{'='*90}",
        f"TEST CASE: {test_name}",
        '='*90,
        "\n📄 GROUND TRUTH JSON (Original):",
        "-" * 40,
        json_A_original,
        "\n📄 LLM-DECODED JSON (from Ground Truth TOON):",
        "-" * 40,
        json_B_from_llm,
        "\n📄 GROUND TRUTH TOON (from library):",
        "-" * 40,
        toon_out_official,
        "\n📄 LLM-ENCODED TOON (from Ground Truth JSON):",
        "-" * 40,
        toon_out_from_llm,
        f"\n📊 MEMORY COMPARISON (for this case)",
        f"  JSON size  : {json_bytes:,} bytes",
        f"  TOON size  : {toon_bytes:,} bytes",
        f"  Reduction  : {reduction:.1f}%",
        f"\n✅ RESULTS FOR: {test_name}",
        f"  DECODING (TOON → JSON) : {'PASS' if decode_passed else 'FAIL'}",
        f"  ENCODING (JSON → TOON) : {'PASS' if encode_passed else 'FAIL'}",
        "="*90,
    ]

    full_log = "\n".join(log_lines)
    print(full_log)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_log + "\n")

    # Calculate how many misses happened in THIS test
    misses_in_this_test = cache_stats["misses"] - initial_misses

    return decode_passed, encode_passed, json_bytes, toon_bytes, (misses_in_this_test > 0)

# ----------------------------
# TEST DATA (UNCHANGED)
# ----------------------------
test_data = {
    "Fitness App": {"app":"FitTrack","users":[{"id":201,"name":"Maya","age":None,"plan":"premium","goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"plan":"basic","goals":["running"]}]},
    "E-Commerce Order": {"order_id":"ORD-789","customer":{"id":501,"name":"Priya Mehta","email":"priya@example.com"},"items":[{"sku":"LAP-202","name":"Gaming Laptop","price":1200,"metadata":{"warranty":"2 years","category":"Electronics"}},{"sku":"MOUSE-55","name":"Wireless Mouse","price":25,"metadata":{"warranty":"1 year","category":"Accessories"}}],"status":"shipped"},
    "Analytics Data": {"metrics":[{"date":"2025-01-01","views":6890,"clicks":401,"conversions":23,"revenue":6015.59,"bounceRate":0.63},{"date":"2025-01-02","views":6940,"clicks":323,"conversions":37,"revenue":9086.44,"bounceRate":0.36}]},
    "CI/CD Pipeline": {"pipeline_name":"WebApp-Deploy","trigger_on":["push:main","pull_request:main"],"env":{},"stages":[{"name":"Build","jobs":[{"name":"Compile-App","runner":"ubuntu-latest","steps":[{"name":"Checkout","uses":"actions/checkout@v2"},{"name":"Build","run":"npm run build"}]}]},{"name":"Test","jobs":[{"name":"Unit-Tests","runner":"ubuntu-latest","steps":[{"name":"Run tests","run":"npm test"}]},{"name":"Linting","runner":"ubuntu-latest","steps":[{"name":"Run linter","run":"npm run lint"}]}]}]},
    "Empty and Mixed Lists": {"id":"user-123","preferences":{"notifications":True,"tags":[],"scores":[100,95,None,80],"history":None}},
    "Content Requiring Quoting": {"title":"TOON: A format review, part {2}","author":"John \"Johnny\" Doe","summary":"A simple line.\nAnother line after a newline.","valid":True},
    "Deeply Nested Structures": {"api_config":{"version":2,"endpoints":{"/users":{"methods":{"GET":{"auth_required":True,"permissions":["read:user","list:users"],"params":{}},"POST":{"auth_required":True,"permissions":["create:user"]}}}}}},
    "Top-Level Array": [{"event":"login","user_id":101,"success":True},{"event":"logout","user_id":101,"success":True}],
    "Heterogeneous Array of Objects": {"items":[{"type":"book","title":"The Hobbit","pages":310},{"type":"movie","title":"The Matrix","duration_mins":136},{"type":"audiobook","title":"Dune","narrator":"Scott Brick"}]},
    "Strings Mimicking TOON Syntax": {"id":"item-001","description":"This is a key: with a value","notes":"users[2]{id,name}: is a sample TOON line.","config":"  - indented: text"},
    "Ambiguous Data Types": {"product_id":"007","quantity":25,"is_active":"true","version":"1.0","null_value":"null"}
}

# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    start_time = datetime.now()
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"TOON Format Validation - Full Test Log\n")
        f.write(f"Run started at: {start_time}\n")
        f.write(f"Model: {MODEL_NAME} | Redis: {REDIS_HOST}:{REDIS_PORT}\n")
        f.write("="*90 + "\n\n")

    print(f"🚀 STARTING ROBUST TOON VALIDATION PIPELINE ({MODEL_NAME})")
    results = {}
    total_json_bytes = 0
    total_toon_bytes = 0

    for test_name, python_data in test_data.items():
        decode_passed, encode_passed, json_bytes, toon_bytes, had_cache_misses = run_test_case(python_data, test_name)
        results[test_name] = (decode_passed, encode_passed)
        total_json_bytes += json_bytes
        total_toon_bytes += toon_bytes
        
        # ONLY sleep if we had cache misses (actual LLM calls)
        if had_cache_misses:
            print(f"⏳ Had cache misses - sleeping 60 seconds to respect rate limits...")
            time.sleep(60)
        else:
            print(f"⚡ All cache hits - proceeding immediately to next test!")

    # Final metrics
    total_reduction = (1 - total_toon_bytes / total_json_bytes) * 100 if total_json_bytes > 0 else 0
    overall_passed = all(decode and encode for decode, encode in results.values())
    hit_rate = cache_stats["hits"] / (cache_stats["hits"] + cache_stats["misses"]) if (cache_stats["hits"] + cache_stats["misses"]) > 0 else 0

    summary_lines = [
        "\n" + "="*90,
        "🎯 FINAL SUMMARY",
        "="*90,
        f"| {'Test Case':<30} | {'DECODE':<10} | {'ENCODE':<10} |",
        "-"*55,
    ]
    for test_name, (decode_passed, encode_passed) in results.items():
        summary_lines.append(f"| {test_name:<30} | {'PASS' if decode_passed else 'FAIL':<10} | {'PASS' if encode_passed else 'FAIL':<10} |")

    summary_lines += [
        "\n" + "="*58,
        "📊 AGGREGATE MEMORY ANALYSIS (ALL TEST CASES)",
        f"| {'Format':<15} | {'Total Size (Bytes)':<20} | {'Reduction':<12} |",
        "-"*58,
        f"| {'JSON (Baseline)':<15} | {total_json_bytes:<20,} | {'-':<12} |",
        f"| {'TOON':<15} | {total_toon_bytes:<20,} | {f'{total_reduction:.1f}%':<12} |",
        f"\n📦 Cache Hit Rate: {hit_rate:.1%} ({cache_stats['hits']} hits / {cache_stats['misses']} misses)",
        f"\nOVERALL RESULT: {'ALL PASSED' if overall_passed else 'SOME FAILED'}",
        f"\nRun completed at: {datetime.now()}",
        f"Total duration: {datetime.now() - start_time}",
        "="*90,
    ]

    final_summary = "\n".join(summary_lines)
    print(final_summary)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(final_summary + "\n")

    print(f"\n✅ Full log saved to: {LOG_FILE}")