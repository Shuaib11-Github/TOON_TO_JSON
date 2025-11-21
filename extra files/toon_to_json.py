# import os
# import re
# import json
# from cerebras.cloud.sdk import Cerebras
# from toon_format import encode, decode
# from dotenv import load_dotenv

# # Load API key from .env file
# load_dotenv()
# api_key = os.getenv("CEREBRAS_API_KEY")

# # 🔑 CONFIG
# client = Cerebras(api_key=api_key)
# MODEL = "llama-3.3-70b"

# # ============================================================================
# # PROMPT: TOON → JSON CONVERSION (MODIFIED)
# # ============================================================================
# toon_to_json_prompt_base = '''You are an expert data converter. Convert TOON to valid JSON.

# RULES:
# - `key: value` → simple field (string/number/bool)
# - `key:` → object with indented sub-fields
# - `list[n]{...}:` → array of objects
# - Nested object: `field{sub1,sub2}:` → next line has values
# - Fields like 'goals', 'tags', 'hobbies' that have comma-separated values → convert to JSON array
# - **Empty values in data rows (e.g., `, ,`) → convert to `null` in JSON**
# - **A key on a line by itself (`key:`) with no indented content → convert to an empty object `{}`** <<< NEW RULE
# - Strings must be quoted; numbers/booleans unquoted
# - Output ONLY valid JSON. No extra text.

# EXAMPLES:

# Example 1:
# TOON:
# app: FitTrack
# users[2]{id,name}:
# 1,Alice
# 2,Bob

# JSON:
# {
#   "app": "FitTrack",
#   "users": [
#     { "id": 1, "name": "Alice" },
#     { "id": 2, "name": "Bob" }
#   ]
# }

# Example 2:
# TOON:
# users[3]{id,name,role}:
# 1,Sreeni,admin
# 2,Krishna,admin
# 3,Aaron,user

# JSON:
# {
#   "users": [
#     { "id": 1, "name": "Sreeni", "role": "admin" },
#     { "id": 2, "name": "Krishna", "role": "admin" },
#     { "id": 3, "name": "Aaron", "role": "user" }
#   ]
# }

# Example 3:
# TOON:
# project:
#   name: Apollo
#   team[1]{id,contact}:
#     101,contact{email}:
#       alice@ex.com

# JSON:
# {
#   "project": {
#     "name": "Apollo",
#     "team": [
#       {
#         "id": 101,
#         "contact": { "email": "alice@ex.com" }
#       }
#     ]
#   }
# }

# Example 4:
# TOON:
# config:
#   debug: true
#   tags: web,api,auth

# JSON:
# {
#   "config": {
#     "debug": true,
#     "tags": ["web", "api", "auth"]
#   }
# }

# Example 5:
# TOON:
# app: HealthApp
# users[2]{id,name,age}:
#   301,Alex,
#   302,Sam,29

# JSON:
# {
#   "app": "HealthApp",
#   "users": [
#     { "id": 301, "name": "Alex", "age": null },
#     { "id": 302, "name": "Sam", "age": 29 }
#   ]
# }

# Example 6 (Empty Object): <<< NEW EXAMPLE
# TOON:
# pipeline:
#   name: deploy-prod
#   config:
#   steps: 10

# JSON:
# {
#   "pipeline": {
#     "name": "deploy-prod",
#     "config": {},
#     "steps": 10
#   }
# }

# Example 7 (Preserving String Types): <<< NEW EXAMPLE
# TOON:
# config:
#   force_string: "true"
#   id_code: "009"
#   message: "null"
#   is_real: true

# JSON:
# {
#   "config": {
#     "force_string": "true",
#     "id_code": "009",
#     "message": "null",
#     "is_real": true
#   }
# }

# Now convert the following TOON to JSON. Output ONLY valid JSON. No extra text.
# '''

# # ============================================================================
# # VALIDATION PROMPT (Unchanged)
# # ============================================================================
# def make_validation_prompt(json_llm, json_original):
#     return f'''Compare these two JSON objects.

# JSON_LLM (decoded by the LLM):
# {json_llm}

# JSON_ORIGINAL (the original source data):
# {json_original}

# Rules:
# - All fields must match exactly in type and value. `null` in JSON is equivalent to Python's `None`.
# - Ignore key order and whitespace.

# Are they semantically equivalent?

# Answer ONLY the word "YES" or "NO". Do not add any other text.
# '''

# # ============================================================================
# # TEST FUNCTION (Unchanged)
# # ============================================================================
# def run_test_case(python_data, test_name="Test"):
#     print(f"\n{'='*90}")
#     print(f"🧪 RUNNING: {test_name}")
#     print('='*90)
#     json_A_original = json.dumps(python_data, indent=2)
#     toon_out_official = encode(python_data)
#     conv_prompt = toon_to_json_prompt_base + "\n" + toon_out_official
#     resp_json_b = client.chat.completions.create(
#         messages=[{"role": "user", "content": conv_prompt}],
#         model=MODEL, stream=False, max_completion_tokens=2000, temperature=0.0, top_p=0.95
#     )
#     json_B_from_llm = resp_json_b.choices[0].message.content.strip()
#     for m in ["```json", "```"]:
#         if json_B_from_llm.startswith(m):
#             json_B_from_llm = json_B_from_llm[len(m):].strip()
#             if json_B_from_llm.endswith("```"):
#                 json_B_from_llm = json_B_from_llm[:-3].strip()
#             break
#     print("\n" + "="*90)
#     print("📄 Original Data (as JSON):")
#     print(json_A_original)
#     print("\n" + "="*90)
#     print("📄 TOON (from toon_format.encode):")
#     print(toon_out_official)
#     print("\n" + "="*90)
#     print("📄 JSON (from LLM decoding TOON):")
#     print(json_B_from_llm)
#     json_bytes = len(json_A_original.encode('utf-8'))
#     toon_bytes = len(toon_out_official.encode('utf-8'))
#     print("\n" + "="*90)
#     print("📊 MEMORY COMPARISON")
#     print(f"| {'Format':<15} | {'Size (Bytes)':<15} | {'Reduction':<12} |")
#     print(f"|{'-'*17}|{'-'*17}|{'-'*14}|")
#     print(f"| {'JSON (Baseline)':<15} | {json_bytes:<15,} | {'-':<12} |")
#     if json_bytes > 0 and toon_bytes > 0:
#         reduction = (1 - toon_bytes / json_bytes) * 100
#         print(f"| {'TOON':<15} | {toon_bytes:<15,} | {f'{reduction:.1f}%':<12} |")
#     else:
#         print(f"| {'TOON':<15} | {toon_bytes:<15,} | {'N/A':<12} |")
#     val_prompt = make_validation_prompt(json_B_from_llm, json_A_original)
#     resp_val = client.chat.completions.create(
#         messages=[{"role": "user", "content": val_prompt}],
#         model=MODEL, stream=False, max_completion_tokens=20, temperature=0.0, top_p=0.95
#     )
#     raw_verdict = resp_val.choices[0].message.content.strip()
#     if re.search(r'\bYES\b', raw_verdict, re.IGNORECASE):
#         verdict = "YES"
#     else:
#         verdict = "NO"
#     print("\n" + "="*90)
#     print(f"✅ VALIDATION (LLM Decode vs. Original Data): {verdict}")
#     print("="*90)
#     return verdict == "YES"

# # ============================================================================
# # TEST CASES (All combined)
# # ============================================================================
# test_data = {
#     # Original tests...
#     "Fitness App": {"app":"FitTrack","users":[{"id":201,"name":"Maya","age":None,"plan":"premium","goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"plan":"basic","goals":["running"]}]},
#     "E-Commerce Order": {"order_id":"ORD-789","customer":{"id":501,"name":"Priya Mehta","email":"priya@example.com"},"items":[{"sku":"LAP-202","name":"Gaming Laptop","price":1200,"metadata":{"warranty":"2 years","category":"Electronics"}},{"sku":"MOUSE-55","name":"Wireless Mouse","price":25,"metadata":{"warranty":"1 year","category":"Accessories"}}],"status":"shipped"},
#     "Analytics Data": {"metrics":[{"date":"2025-01-01","views":6890,"clicks":401,"conversions":23,"revenue":6015.59,"bounceRate":0.63},{"date":"2025-01-02","views":6940,"clicks":323,"conversions":37,"revenue":9086.44,"bounceRate":0.36}]},
#     "CI/CD Pipeline": {"pipeline_name":"WebApp-Deploy","trigger_on":["push:main","pull_request:main"],"env":{},"stages":[{"name":"Build","jobs":[{"name":"Compile-App","runner":"ubuntu-latest","steps":[{"name":"Checkout","uses":"actions/checkout@v2"},{"name":"Build","run":"npm run build"}]}]},{"name":"Test","jobs":[{"name":"Unit-Tests","runner":"ubuntu-latest","steps":[{"name":"Run tests","run":"npm test"}]},{"name":"Linting","runner":"ubuntu-latest","steps":[{"name":"Run linter","run":"npm run lint"}]}]}]},
#     # Second batch of tests...
#     "Empty and Mixed Lists": {"id":"user-123","preferences":{"notifications":True,"tags":[],"scores":[100,95,None,80],"history":None}},
#     "Content Requiring Quoting": {"title":"TOON: A format review, part {2}","author":"John \"Johnny\" Doe","summary":"A simple line.\nAnother line after a newline.","valid":True},
#     "Deeply Nested Structures": {"api_config":{"version":2,"endpoints":{"/users":{"methods":{"GET":{"auth_required":True,"permissions":["read:user","list:users"],"params":{}},"POST":{"auth_required":True,"permissions":["create:user"]}}}}}},
#     "Top-Level Array": [{"event":"login","user_id":101,"success":True},{"event":"logout","user_id":101,"success":True}],
#     # Final stress tests...
#     "Heterogeneous Array of Objects": {"items":[{"type":"book","title":"The Hobbit","pages":310},{"type":"movie","title":"The Matrix","duration_mins":136},{"type":"audiobook","title":"Dune","narrator":"Scott Brick"}]},
#     "Strings Mimicking TOON Syntax": {"id":"item-001","description":"This is a key: with a value","notes":"users[2]{id,name}: is a sample TOON line.","config":"  - indented: text"},
#     "Ambiguous Data Types": {"product_id":"007","quantity":25,"is_active":"true","version":"1.0","null_value":"null"}
# }

# # ============================================================================
# # RUN
# # ============================================================================
# print("🚀 STARTING ROBUST TOON VALIDATION PIPELINE")
# results = {}
# for test_name, python_data in test_data.items():
#     results[test_name] = run_test_case(python_data, test_name)
# print("\n" + "="*90)
# print("🎯 FINAL SUMMARY:")
# all_passed = True
# for test_name, passed in results.items():
#     status = '✅ PASS' if passed else '❌ FAIL'
#     print(f"{test_name:<30} → {status}")
#     if not passed:
#         all_passed = False
# print("-" * 40)
# print(f"OVERALL RESULT: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
# print("="*90)

import os
import re
import json
from cerebras.cloud.sdk import Cerebras
from toon_format import encode, decode
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
api_key = os.getenv("CEREBRAS_API_KEY")

# 🔑 CONFIG
client = Cerebras(api_key=api_key)
MODEL = "llama-3.3-70b"

# ============================================================================
# PROMPT: TOON → JSON CONVERSION (FINAL, MOST ROBUST VERSION)
# ============================================================================
toon_to_json_prompt_base = '''You are an expert data converter. Convert TOON to valid JSON.

RULES:
- `key: value` → simple field (string/number/bool)
- `key:` → object with indented sub-fields
- `list[n]{...}:` → array of objects
- Nested object: `field{sub1,sub2}:` → next line has values
- Fields like 'goals', 'tags', 'hobbies' that have comma-separated values → convert to JSON array
- **Empty values in data rows (e.g., `, ,`) → convert to `null` in JSON**
- **A key on a line by itself (`key:`) with no indented content → convert to an empty object `{}`** <<< NEW RULE
- Strings must be quoted; numbers/booleans unquoted
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

Example 6 (Empty Object): <<< NEW EXAMPLE
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

Example 7 (Preserving String Types): <<< NEW EXAMPLE
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

Example 8 (Lists with Nulls and Exact Counts): <<< NEW EXAMPLE
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
# VALIDATION PROMPT (Unchanged)
# ============================================================================
def make_validation_prompt(json_llm, json_original):
    return f'''Compare these two JSON objects.

JSON_LLM (decoded by the LLM):
{json_llm}

JSON_ORIGINAL (the original source data):
{json_original}

Rules:
- All fields must match exactly in type and value. `null` in JSON is equivalent to Python's `None`.
- Ignore key order and whitespace.

Are they semantically equivalent?

Answer ONLY the word "YES" or "NO". Do not add any other text.
'''

# ============================================================================
# TEST FUNCTION (Unchanged)
# ============================================================================
def run_test_case(python_data, test_name="Test"):
    print(f"\n{'='*90}")
    print(f"🧪 RUNNING: {test_name}")
    print('='*90)
    json_A_original = json.dumps(python_data, indent=2)
    toon_out_official = encode(python_data)
    conv_prompt = toon_to_json_prompt_base + "\n" + toon_out_official
    resp_json_b = client.chat.completions.create(
        messages=[{"role": "user", "content": conv_prompt}],
        model=MODEL, stream=False, max_completion_tokens=2000, temperature=0.0, top_p=0.95
    )
    json_B_from_llm = resp_json_b.choices[0].message.content.strip()
    for m in ["```json", "```"]:
        if json_B_from_llm.startswith(m):
            json_B_from_llm = json_B_from_llm[len(m):].strip()
            if json_B_from_llm.endswith("```"):
                json_B_from_llm = json_B_from_llm[:-3].strip()
            break
    print("\n" + "="*90)
    print("📄 Original Data (as JSON):")
    print(json_A_original)
    print("\n" + "="*90)
    print("📄 TOON (from toon_format.encode):")
    print(toon_out_official)
    print("\n" + "="*90)
    print("📄 JSON (from LLM decoding TOON):")
    print(json_B_from_llm)
    json_bytes = len(json_A_original.encode('utf-8'))
    toon_bytes = len(toon_out_official.encode('utf-8'))
    print("\n" + "="*90)
    print("📊 MEMORY COMPARISON")
    print(f"| {'Format':<15} | {'Size (Bytes)':<15} | {'Reduction':<12} |")
    print(f"|{'-'*17}|{'-'*17}|{'-'*14}|")
    print(f"| {'JSON (Baseline)':<15} | {json_bytes:<15,} | {'-':<12} |")
    if json_bytes > 0 and toon_bytes > 0:
        reduction = (1 - toon_bytes / json_bytes) * 100
        print(f"| {'TOON':<15} | {toon_bytes:<15,} | {f'{reduction:.1f}%':<12} |")
    else:
        print(f"| {'TOON':<15} | {toon_bytes:<15,} | {'N/A':<12} |")
    val_prompt = make_validation_prompt(json_B_from_llm, json_A_original)
    resp_val = client.chat.completions.create(
        messages=[{"role": "user", "content": val_prompt}],
        model=MODEL, stream=False, max_completion_tokens=20, temperature=0.0, top_p=0.95
    )
    raw_verdict = resp_val.choices[0].message.content.strip()
    if re.search(r'\bYES\b', raw_verdict, re.IGNORECASE):
        verdict = "YES"
    else:
        verdict = "NO"
    print("\n" + "="*90)
    print(f"✅ VALIDATION (LLM Decode vs. Original Data): {verdict}")
    print("="*90)
    return verdict == "YES"

# ============================================================================
# TEST CASES (All combined)
# ============================================================================
test_data = {
    # Original tests...
    "Fitness App": {"app":"FitTrack","users":[{"id":201,"name":"Maya","age":None,"plan":"premium","goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"plan":"basic","goals":["running"]}]},
    "E-Commerce Order": {"order_id":"ORD-789","customer":{"id":501,"name":"Priya Mehta","email":"priya@example.com"},"items":[{"sku":"LAP-202","name":"Gaming Laptop","price":1200,"metadata":{"warranty":"2 years","category":"Electronics"}},{"sku":"MOUSE-55","name":"Wireless Mouse","price":25,"metadata":{"warranty":"1 year","category":"Accessories"}}],"status":"shipped"},
    "Analytics Data": {"metrics":[{"date":"2025-01-01","views":6890,"clicks":401,"conversions":23,"revenue":6015.59,"bounceRate":0.63},{"date":"2025-01-02","views":6940,"clicks":323,"conversions":37,"revenue":9086.44,"bounceRate":0.36}]},
    "CI/CD Pipeline": {"pipeline_name":"WebApp-Deploy","trigger_on":["push:main","pull_request:main"],"env":{},"stages":[{"name":"Build","jobs":[{"name":"Compile-App","runner":"ubuntu-latest","steps":[{"name":"Checkout","uses":"actions/checkout@v2"},{"name":"Build","run":"npm run build"}]}]},{"name":"Test","jobs":[{"name":"Unit-Tests","runner":"ubuntu-latest","steps":[{"name":"Run tests","run":"npm test"}]},{"name":"Linting","runner":"ubuntu-latest","steps":[{"name":"Run linter","run":"npm run lint"}]}]}]},
    # Second batch of tests...
    "Empty and Mixed Lists": {"id":"user-123","preferences":{"notifications":True,"tags":[],"scores":[100,95,None,80],"history":None}},
    "Content Requiring Quoting": {"title":"TOON: A format review, part {2}","author":"John \"Johnny\" Doe","summary":"A simple line.\nAnother line after a newline.","valid":True},
    "Deeply Nested Structures": {"api_config":{"version":2,"endpoints":{"/users":{"methods":{"GET":{"auth_required":True,"permissions":["read:user","list:users"],"params":{}},"POST":{"auth_required":True,"permissions":["create:user"]}}}}}},
    "Top-Level Array": [{"event":"login","user_id":101,"success":True},{"event":"logout","user_id":101,"success":True}],
    # Final stress tests...
    "Heterogeneous Array of Objects": {"items":[{"type":"book","title":"The Hobbit","pages":310},{"type":"movie","title":"The Matrix","duration_mins":136},{"type":"audiobook","title":"Dune","narrator":"Scott Brick"}]},
    "Strings Mimicking TOON Syntax": {"id":"item-001","description":"This is a key: with a value","notes":"users[2]{id,name}: is a sample TOON line.","config":"  - indented: text"},
    "Ambiguous Data Types": {"product_id":"007","quantity":25,"is_active":"true","version":"1.0","null_value":"null"}
}

# ============================================================================
# RUN
# ============================================================================
print("🚀 STARTING ROBUST TOON VALIDATION PIPELINE")
results = {}
for test_name, python_data in test_data.items():
    results[test_name] = run_test_case(python_data, test_name)
print("\n" + "="*90)
print("🎯 FINAL SUMMARY:")
all_passed = True
for test_name, passed in results.items():
    status = '✅ PASS' if passed else '❌ FAIL'
    print(f"{test_name:<30} → {status}")
    if not passed:
        all_passed = False
print("-" * 40)
print(f"OVERALL RESULT: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
print("="*90)