import json
import os
import re
from cerebras.cloud.sdk import Cerebras
from toon_format import decode
from dotenv import load_dotenv

load_dotenv()

client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY"))
MODEL = "llama-3.3-70b"

# ==============================================================================
# TOON GENERATION PROMPT (JSON → TOON examples)
# ==============================================================================
toon_generation_prompt_base = '''You are an expert data serializer. Convert JSON to TOON format.

RULES:
- Output ONLY TOON. No extra text, no markdown, no explanations.
- Simple field: `key: value` (e.g., `id: 123`, `active: true`)
- String values with spaces or special chars: quote them (e.g., `message: "Hello, world!"`)
- Object: `key:` then indented fields on new lines
- Array of primitives: `tags[N]: a,b,c`
- Array of FLAT objects (only scalars): `users[N]{id,name}:` then comma rows
- Array of COMPLEX objects (with nesting or lists): `users[N]:` then `- field: value` blocks
- Null value: `null`
- NEVER invent, omit, or reorder fields.

EXAMPLES:

Example 1:
JSON:
{"id":123,"name":"Ada","active":true,"salary":75000.0}
TOON:
id: 123
name: Ada
active: true
salary: 75000.0

Example 2:
JSON:
{"tags":["web","api","auth"]}
TOON:
tags[3]: web,api,auth

Example 3:
JSON:
{"users":[{"id":1,"name":"Alice","role":"admin"},{"id":2,"name":"Bob","role":"user"}]}
TOON:
users[2]{id,name,role}:
  1,Alice,admin
  2,Bob,user

Example 4:
JSON:
{"project":{"name":"Apollo","status":"active","config":{"debug":false,"timeout":30.5}}}
TOON:
project:
  name: Apollo
  status: active
  config:
    debug: false
    timeout: 30.5

Example 5:
JSON:
{"users":[{"id":201,"name":"Maya","age":null,"plan":"premium","goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"plan":"basic","goals":["running"]}]}
TOON:
users[2]:
  - id: 201
    name: Maya
    age: null
    plan: premium
    goals[2]: weight_loss,strength
  - id: 202
    name: Ravi
    age: 35
    plan: basic
    goals[1]: running

Example 6:
JSON:
{"order":{"id":"ORD-789","customer":{"name":"Priya Mehta","emails":["priya@example.com","priya.work@org.in"]},"items":[{"sku":"LAP-202","name":"Gaming Laptop","price":1200,"metadata":{"warranty":"2 years","specs":{"cpu":"i9","ram_gb":32,"is_new":true}}}]}}
TOON:
order:
  id: ORD-789
  customer:
    name: Priya Mehta
    emails[2]: priya@example.com,priya.work@org.in
  items[1]:
    - sku: LAP-202
      name: Gaming Laptop
      price: 1200
      metadata:
        warranty: 2 years
        specs:
          cpu: i9
          ram_gb: 32
          is_new: true

Example 7:
JSON:
{"users":[]}
TOON:
users[0]:

Example 8:
JSON:
{"message":"Hello, 🌍! Café naïve résumé.","tags":["café","naïve","résumé","🚀"]}
TOON:
message: "Hello, 🌍! Café naïve résumé."
tags[4]: café,naïve,résumé,🚀

Now convert this JSON to TOON. Output ONLY TOON.
'''

def make_validation_prompt(json_a, json_b):
    return f'''Compare these two JSON objects.

JSON_A (direct from LLM):
{json_a}

JSON_B (from TOON conversion):
{json_b}

Rules:
- Fields like 'goals', 'tags', 'hobbies', 'items' may appear as:
    - JSON_A: ["a", "b"]
    - JSON_B: ["a", "b"]
  → If both are arrays, compare values.
- All other fields must match exactly in type and value.
- Ignore key order and whitespace.

Are they semantically equivalent?

Answer ONLY the word "YES" or "NO". Do not add any other text.
'''

def run_test_case(data_desc, test_name="Test"):
    print(f"\n{'='*90}")
    print(f"🧪 RUNNING: {test_name}")
    print('='*90)

    # --- LLM Call 1: Generate JSON_A from natural language ---
    json_prompt = (
        "Output this as compact JSON only. Rules:\n"
        "- If any field is NOT mentioned, output as `null`.\n"
        "- Never use default values.\n"
        "- Only output the JSON object. No extra text.\n\n"
        f"Data:\n{data_desc}"
    )
    resp_json = client.chat.completions.create(
        messages=[{"role": "user", "content": json_prompt}],
        model=MODEL,
        stream=False,
        max_completion_tokens=1000,
        temperature=0.3,
        top_p=0.95
    )
    json_A = resp_json.choices[0].message.content.strip()
    for m in ["```json", "```"]:
        if json_A.startswith(m):
            json_A = json_A[len(m):].strip()
            if json_A.endswith("```"):
                json_A = json_A[:-3].strip()
            break

    # --- LLM Call 2: Generate TOON from JSON_A ---
    toon_prompt = toon_generation_prompt_base + "\n" + json_A
    resp_toon = client.chat.completions.create(
        messages=[{"role": "user", "content": toon_prompt}],
        model=MODEL,
        stream=False,
        max_completion_tokens=1000,
        temperature=0.3,
        top_p=0.95
    )
    toon_out = resp_toon.choices[0].message.content.strip()

    # --- LOCAL: TOON → JSON_B via decode() ---
    try:
        decoded_obj = decode(toon_out)
        json_B = json.dumps(decoded_obj, separators=(',', ':'), ensure_ascii=False)
    except Exception as e:
        print(f"❌ DECODE FAILED: {e}")
        json_B = '{}'

    # === DISPLAY ===
    print("\n" + "="*90)
    print("📄 JSON_A (Direct from LLM):")
    print(json_A)
    print("\n" + "="*90)
    print("📄 TOON (from LLM):")
    print(toon_out)
    print("\n" + "="*90)
    print("📄 JSON_B (from toon_format.decode()):")
    print(json_B)

    # --- Memory ---
    json_bytes = len(json_A.encode('utf-8'))
    toon_bytes = len(toon_out.encode('utf-8'))
    print("\n" + "="*90)
    print("📊 MEMORY COMPARISON (UTF-8 Bytes):")
    print(f"JSON size  : {json_bytes:,} bytes")
    print(f"TOON size  : {toon_bytes:,} bytes")
    if json_bytes > 0:
        reduction = (1 - toon_bytes / json_bytes) * 100
        saved = json_bytes - toon_bytes
        print(f"Reduction  : {reduction:.1f}%")
        print(f"Saved      : {saved:,} bytes")

    # --- LLM Call 3: Validation ---
    val_prompt = make_validation_prompt(json_A, json_B)
    resp_val = client.chat.completions.create(
        messages=[{"role": "user", "content": val_prompt}],
        model=MODEL,
        stream=False,
        max_completion_tokens=20,
        temperature=0.0,
        top_p=0.95
    )
    raw_verdict = resp_val.choices[0].message.content.strip()
    verdict = "YES" if re.search(r'\bYES\b', raw_verdict, re.IGNORECASE) else "NO"

    print("\n" + "="*90)
    print(f"✅ VALIDATION (LLM): {verdict}")
    print("="*90)
    
    return verdict == "YES"

# ============================================================================
# TEST CASES
# ============================================================================
fitness_desc = (
    "TOP-LEVEL fields: "
    "app: 'FitTrack', "
    "users: array of 2 users. Each has id (int), name (str), plan (str), profile: { age (int), goals (list of str) }. "
    "User1: id=201, name='Maya', plan='premium', goals=['weight_loss','strength']. "
    "User2: id=202, name='Ravi', plan='basic', goals=['running']."
)

fitness_desc_1 = (
    "TOP-LEVEL fields: app='FitTrack', users array. "
    "Each user has: id (int), name (str), age? (optional int), plan (str), goals (list of str). "
    "User1: id=201, name='Maya', plan='premium', goals=['weight_loss','strength']  (age not provided). "
    "User2: id=202, name='Ravi', plan='basic', age=35, goals=['running']."
)

fitness_desc_2 = (
    "TOP-LEVEL fields: "
    "app: 'FitTrack', "
    "users: array of 2 users. Each has id (int), name (str), plan (str), profile: { age (int), goals (list of str) }. "
    "User1: id=201, name='Maya', plan='premium', age=28, goals=['weight_loss','strength']. "
    "User2: id=202, name='Ravi', plan='basic', age=35, goals=['running']."
)

ecommerce_desc = (
    "TOP-LEVEL fields: "
    "order_id: 'ORD-789', "
    "customer: { id: 501, name: 'Priya Mehta', email: 'priya@example.com' }, "
    "shipping_address: { street: '123 Main St', city: 'Mumbai', country: 'India' }, "
    "items: array of 2 products. Each has sku, name, price, metadata: { warranty, category }. "
    "Product1: sku='LAP-202', name='Gaming Laptop', price=1200, metadata={ warranty='2 years', category='Electronics' }. "
    "Product2: sku='MOUSE-55', name='Wireless Mouse', price=25, metadata={ warranty='1 year', category='Accessories' }. "
    "status: 'shipped'"
)

# ============================================================================
# ADDITIONAL TEST CASES
# ============================================================================

# Test 1: Simple Object with Boolean and Numbers
simple_obj_desc = (
    "TOP-LEVEL fields: "
    "id: 123 (int), "
    "name: 'Ada' (str), "
    "active: true (bool), "
    "salary: 75000 (number)"
)

# Test 2: Tabular Array (flat objects)
tabular_desc = (
    "TOP-LEVEL fields: "
    "users: array of 2 users. Each has id (int), name (str), role (str). "
    "User1: id=1, name='Alice', role='admin'. "
    "User2: id=2, name='Bob', role='user'."
)

# Test 3: Analytics Data with Mixed Numbers
analytics_desc = (
    "TOP-LEVEL fields: "
    "metrics: array of 2 daily records. Each has: "
    "date (str), views (int), clicks (int), conversions (int), revenue (float), bounceRate (float). "
    "Day1: date='2025-01-01', views=6890, clicks=401, conversions=23, revenue=6015.59, bounceRate=0.63. "
    "Day2: date='2025-01-02', views=6940, clicks=323, conversions=37, revenue=9086.44, bounceRate=0.36."
)

# ============================================================================
# RUN
# ============================================================================
print("🚀 STARTING ROBUST TOON VALIDATION PIPELINE")
result1 = run_test_case(fitness_desc, "Fitness App")
result2 = run_test_case(fitness_desc_1, "Fitness App")
result3 = run_test_case(fitness_desc_2, "Fitness App")
result4 = run_test_case(ecommerce_desc, "E-Commerce Order")
result5 = run_test_case(simple_obj_desc, "Simple Object")
result6 = run_test_case(tabular_desc, "Tabular Array")
result7 = run_test_case(analytics_desc, "Analytics Data")

print("\n" + "="*90)
print("🎯 FINAL SUMMARY:")
print(f"Fitness App        → {'✅ PASS' if result1 else '❌ FAIL'}")
print(f"Fitness App 1      → {'✅ PASS' if result2 else '❌ FAIL'}")
print(f"Fitness App 2      → {'✅ PASS' if result3 else '❌ FAIL'}")
print(f"E-Commerce         → {'✅ PASS' if result4 else '❌ FAIL'}")
print(f"Simple Object      → {'✅ PASS' if result5 else '❌ FAIL'}")
print(f"Tabular Array      → {'✅ PASS' if result6 else '❌ FAIL'}")
print(f"Analytics Data     → {'✅ PASS' if result7 else '❌ FAIL'}")
print("="*90)