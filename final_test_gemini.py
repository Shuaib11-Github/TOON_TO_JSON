import os
import re
import json
import time
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from toon_format import encode, decode
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ Missing GEMINI_API_KEY in .env file")

# 🔑 CONFIG: Gemini setup
genai.configure(api_key=api_key)
MODEL_NAME = "gemini-2.5-flash"  # or "gemini-2.5-flash"

# Sanitize model name for use in filenames
def sanitize_filename(name):
    # Replace forbidden characters in Windows filenames: \ / : * ? " < > |
    return re.sub(r'[\\/*?:"<>|]', "_", name)

safe_model_name = sanitize_filename(MODEL_NAME)
LOG_FILE = f"full_test_run_log_openrouter_{safe_model_name}.txt"

# Create model instance
model = genai.GenerativeModel(MODEL_NAME)

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

# ============================================================================
# PROMPT 3: VALIDATION
# ============================================================================
def make_validation_prompt(json_llm, json_original):
    return f'''Compare these two JSON objects. JSON_LLM (decoded by the LLM):\n{json_llm}\n\nJSON_ORIGINAL (the original source data):\n{json_original}\n\nRules:\n- All fields must match exactly in type and value. `null` in JSON is equivalent to Python's `None`.\n- Ignore key order and whitespace.\n\nAre they semantically equivalent?\n\nAnswer ONLY the word "YES" or "NO". Do not add any other text.'''

# ============================================================================
# GEMINI HELPER FUNCTION (with retry mechanism)
# ============================================================================
def call_gemini(prompt, max_tokens=4000, temperature=0.0, retries=3, delay=5):
    """
    Call Gemini model with a retry mechanism.

    Args:
        prompt (str): The prompt to send to the model.
        max_tokens (int): The maximum number of tokens to generate.
        temperature (float): The sampling temperature.
        retries (int): The number of times to retry on failure.
        delay (int): The number of seconds to wait between retries.

    Returns:
        str: The model's response text, or an empty string if all retries fail.
    """
    # Define safety settings to be permissive for this testing script
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    for attempt in range(retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                    top_p=0.95,
                ),
                safety_settings=safety_settings
            )
            
            # Check if the response has text
            result_text = response.text.strip()
            
            # SUCCESS CONDITION: If we get non-empty text, return it immediately.
            if result_text:
                return result_text

            # If we get here, the response was empty but there was no error.
            # We'll treat this as a failure and retry.
            print(f"❗️ API call successful but returned empty content on attempt {attempt + 1} of {retries}.")

        except ValueError:
            # This catches cases where response.text is invalid due to safety filters, etc.
            print(f"❗️ API call failed with a ValueError on attempt {attempt + 1} of {retries}.")
        except Exception as e:
            # Catch any other unexpected errors (e.g., network issues)
            print(f"❗️ An unexpected error occurred on attempt {attempt + 1} of {retries}: {e}")

        # If this isn't the last attempt, wait before retrying.
        if attempt < retries - 1:
            print(f"   Retrying in {delay} seconds...")
            time.sleep(delay)

    # If the loop completes without a successful return, all retries have failed.
    print(f"❌ All {retries} retry attempts failed for the prompt.")
    return "" # Return empty string as the final failure signal

# ============================================================================
# MODIFIED TEST FUNCTION (uses programmatic validation and rate-limit delays)
# ============================================================================
def run_test_case(python_data, test_name="Test"):
    print(f"\n{'='*90}")
    print(f"🧪 RUNNING: {test_name}")
    print('='*90)

    # --- Ground Truth Generation ---
    json_A_original = json.dumps(python_data, indent=2)
    toon_out_official = encode(python_data)

    # ===========================================================
    # PART 1: DECODING TEST (TOON → JSON)
    # ===========================================================
    print(">>> RUNNING DECODING TEST (TOON → JSON)")
    conv_prompt = toon_to_json_prompt_base + "\n" + toon_out_official
    json_B_from_llm = call_gemini(conv_prompt, max_tokens=4000, temperature=0.0)
    # Clean markdown
    json_B_from_llm = json_B_from_llm.replace("```json", "").replace("```", "").strip()

    decode_passed = False
    if not json_B_from_llm:
        print("   [ERROR] LLM returned an empty string for JSON decoding.")
        decode_passed = False
    else:
        try:
            # Programmatic validation: Parse both JSONs and compare the Python objects
            original_data = json.loads(json_A_original)
            llm_decoded_data = json.loads(json_B_from_llm)
            if original_data == llm_decoded_data:
                decode_passed = True
        except json.JSONDecodeError:
            print("   [ERROR] LLM produced invalid JSON that could not be parsed.")
            decode_passed = False
        except Exception as e:
            print(f"   [ERROR] An unexpected error occurred during JSON validation: {e}")
            decode_passed = False

    # === ADD A SMALL DELAY TO RESPECT RATE LIMITS ===
    print("   ...waiting 5s before next API call...")
    time.sleep(5)

    # ===========================================================
    # PART 2: ENCODING TEST (JSON → TOON)
    # ===========================================================
    print("\n>>> RUNNING ENCODING TEST (JSON → TOON)")
    encode_prompt = json_to_toon_prompt_base + "\n" + json_A_original
    toon_out_from_llm = call_gemini(encode_prompt, max_tokens=4000, temperature=0.0)
    toon_out_from_llm = toon_out_from_llm.replace("```toon", "").replace("```", "").strip()

    encode_passed = False
    if not toon_out_from_llm:
        print("   [ERROR] LLM returned an empty string for TOON encoding.")
        encode_passed = False
    else:
        try:
            decoded_llm_toon = decode(toon_out_from_llm)
            if decoded_llm_toon == python_data:
                encode_passed = True
        except Exception as e:
            print(f"   [ERROR] LLM-generated TOON was invalid and could not be decoded: {e}")
            encode_passed = False

    # The rest of your logging code remains the same...
    # Memory stats
    json_bytes = len(json_A_original.encode('utf-8'))
    toon_bytes = len(toon_out_official.encode('utf-8'))
    reduction = (1 - toon_bytes / json_bytes) * 100 if json_bytes > 0 else 0

    # === LOG EVERYTHING TO FILE ===
    log_lines = []
    log_lines.append(f"\n{'='*90}")
    log_lines.append(f"TEST CASE: {test_name}")
    log_lines.append('='*90)
    log_lines.append("\n📄 GROUND TRUTH JSON (Original):")
    log_lines.append("-" * 40)
    log_lines.append(json_A_original)
    log_lines.append("\n📄 LLM-DECODED JSON (from Ground Truth TOON):")
    log_lines.append("-" * 40)
    log_lines.append(json_B_from_llm)
    log_lines.append("\n📄 GROUND TRUTH TOON (from library):")
    log_lines.append("-" * 40)
    log_lines.append(toon_out_official)
    log_lines.append("\n📄 LLM-ENCODED TOON (from Ground Truth JSON):")
    log_lines.append("-" * 40)
    log_lines.append(toon_out_from_llm)
    
    # Add metrics to log
    log_lines.append(f"\n📊 MEMORY COMPARISON (for this case)")
    log_lines.append(f"  JSON size  : {json_bytes:,} bytes")
    log_lines.append(f"  TOON size  : {toon_bytes:,} bytes")
    log_lines.append(f"  Reduction  : {reduction:.1f}%")
    
    log_lines.append(f"\n✅ RESULTS FOR: {test_name}")
    log_lines.append(f"  DECODING (TOON → JSON) : {'PASS' if decode_passed else 'FAIL'}")
    log_lines.append(f"  ENCODING (JSON → TOON) : {'PASS' if encode_passed else 'FAIL'}")
    log_lines.append("="*90)

    full_log = "\n".join(log_lines)
    print(full_log)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(full_log + "\n")

    return decode_passed, encode_passed, json_bytes, toon_bytes

# ============================================================================
# TEST CASES (Unchanged)
# ============================================================================
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

# ============================================================================
# RUNNER WITH FULL METRICS LOGGING
# ============================================================================
import datetime
start_time = datetime.datetime.now()
with open(LOG_FILE, "w", encoding="utf-8") as f:
    f.write(f"TOON Format Validation - Full Test Log\n")
    f.write(f"Run started at: {start_time}\n")
    f.write(f"Model: {MODEL_NAME}\n")
    f.write("="*90 + "\n\n")

print(f"🚀 STARTING ROBUST TOON VALIDATION PIPELINE ({MODEL_NAME})")
results = {}
total_json_bytes = 0
total_toon_bytes = 0

for test_name, python_data in test_data.items():
    decode_passed, encode_passed, json_bytes, toon_bytes = run_test_case(python_data, test_name)
    results[test_name] = (decode_passed, encode_passed)
    total_json_bytes += json_bytes
    total_toon_bytes += toon_bytes

    # ADDED DELAY TO AVOID RATE LIMITING
    print("\n⏳ Waiting 60 seconds to respect API rate limits (2 RPM)...")
    time.sleep(60)

# Final metrics
total_reduction = (1 - total_toon_bytes / total_json_bytes) * 100 if total_json_bytes > 0 else 0
overall_passed = all(decode and encode for decode, encode in results.values())

# Build final summary for log
summary_lines = []
summary_lines.append("\n" + "="*90)
summary_lines.append("🎯 FINAL SUMMARY")
summary_lines.append("="*90)
summary_lines.append(f"| {'Test Case':<30} | {'DECODE':<10} | {'ENCODE':<10} |")
summary_lines.append("-"*55)
for test_name, (decode_passed, encode_passed) in results.items():
    decode_status = 'PASS' if decode_passed else 'FAIL'
    encode_status = 'PASS' if encode_passed else 'FAIL'
    summary_lines.append(f"| {test_name:<30} | {decode_status:<10} | {encode_status:<10} |")

summary_lines.append("\n" + "="*58)
summary_lines.append("📊 AGGREGATE MEMORY ANALYSIS (ALL TEST CASES)")
summary_lines.append(f"| {'Format':<15} | {'Total Size (Bytes)':<20} | {'Reduction':<12} |")
summary_lines.append("-"*58)
summary_lines.append(f"| {'JSON (Baseline)':<15} | {total_json_bytes:<20,} | {'-':<12} |")
summary_lines.append(f"| {'TOON':<15} | {total_toon_bytes:<20,} | {f'{total_reduction:.1f}%':<12} |")

summary_lines.append(f"\nOVERALL RESULT: {'ALL PASSED' if overall_passed else 'SOME FAILED'}")
end_time = datetime.datetime.now()
summary_lines.append(f"\nRun completed at: {end_time}")
summary_lines.append(f"Total duration: {end_time - start_time}")
summary_lines.append("="*90)

final_summary = "\n".join(summary_lines)
print(final_summary)

# Append final summary to log file
with open(LOG_FILE, "a", encoding="utf-8") as f:
    f.write(final_summary + "\n")

print(f"\n✅ Full log (including all metrics) saved to: {LOG_FILE}")