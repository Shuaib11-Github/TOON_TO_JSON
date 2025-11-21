import os
import re
from cerebras.cloud.sdk import Cerebras

# 🔑 CONFIG
client = Cerebras(api_key="csk-kt9c5e52jch9htp4vdmepd3kr43ey95w53w6pj6mcx9x4e95")
# MODEL = "zai-glm-4.6"
MODEL = "llama-3.3-70b"

# ============================================================================
# PROMPT 1: TOON GENERATION (with flat root + list rules)
# ============================================================================
toon_generation_prompt_base = '''You output ONLY in TOON format.

RULES:
- Simple value (string/number/bool): `key: value` → e.g., `app: FitTrack`
- Object: `key:` then indented fields
- Array of objects: `users[2]{id,name,profile}:`
- Nested object in row: `profile{age,goals}:` → next indented line has values
- List fields (e.g., goals, tags): output as comma-separated values on one line
- If a field value is NOT provided in the input, output it as EMPTY (e.g., use `, ,` in data rows)
- NEVER invent values (like 0, 25, or "unknown") for missing fields
- NEVER add extra text, markdown, or explanations
- STOP immediately after the last data line

EXAMPLES:

Example 1 (top-level scalar + array):
app: FitTrack
users[2]{id,name}:
1,Alice
2,Bob

Example 2 (flat array):
users[3]{id,name,role}:
1,Sreeni,admin
2,Krishna,admin
3,Aaron,user

Example 3 (nested object):
project:
  name: Apollo
  status: active
  team[1]{id,role,contact}:
    101,lead,contact{email}:
      alice@ex.com

Example 4 (list field):
config:
  debug: true
  tags: web,api,auth

Example 5 (missing optional field):
app: HealthApp
users[2]{id,name,age,goals}:
  301,Alex,,cardio
  302,Sam,29,running,yoga

Now convert this data to TOON. Output ONLY TOON.
'''

# ============================================================================
# PROMPT 2: TOON → JSON CONVERSION (with list-as-array rule)
# ============================================================================
toon_to_json_prompt_base = '''You are an expert data converter. Convert TOON to valid JSON.

RULES:
- `key: value` → simple field (string/number/bool)
- `key:` → object with indented sub-fields
- `list[n]{...}:` → array of objects
- Nested object: `field{sub1,sub2}:` → next line has values
- Fields like 'goals', 'tags', 'hobbies' that have comma-separated values → convert to JSON array
- **Empty values in data rows (e.g., `, ,` or trailing commas with no value) → convert to `null` in JSON**
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
  status: active
  team[1]{id,role,contact}:
    101,lead,contact{email}:
      alice@ex.com

JSON:
{
  "project": {
    "name": "Apollo",
    "status": "active",
    "team": [
      {
        "id": 101,
        "role": "lead",
        "contact": {
          "email": "alice@ex.com"
        }
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
users[2]{id,name,age,goals}:
  301,Alex,,cardio
  302,Sam,29,running,yoga

JSON:
{
  "app": "HealthApp",
  "users": [
    {
      "id": 301,
      "name": "Alex",
      "age": null,
      "goals": ["cardio"]
    },
    {
      "id": 302,
      "name": "Sam",
      "age": 29,
      "goals": ["running", "yoga"]
    }
  ]
}

Now convert the following TOON to JSON. Output ONLY valid JSON. No extra text.
'''

# ============================================================================
# PROMPT 3: VALIDATION (strict + robust)
# ============================================================================
def make_validation_prompt(json_a, json_b):
    return f'''Compare these two JSON objects.

JSON_A (direct from LLM):
{json_a}

JSON_B (from TOON conversion):
{json_b}

Rules:
- Fields like 'goals', 'tags', 'hobbies', 'items' may appear as:
    - JSON_A: ["a", "b"]
    - JSON_B: ["a", "b"]  (should NEVER be string due to conversion rules)
  → If both are arrays, compare values.
- All other fields must match exactly in type and value.
- Ignore key order and whitespace.

Are they semantically equivalent?

Answer ONLY the word "YES" or "NO". Do not add any other text.
'''

# ============================================================================
# TEST FUNCTION
# ============================================================================
def run_test_case(data_desc, test_name="Test"):
    print(f"\n{'='*90}")
    print(f"🧪 RUNNING: {test_name}")
    print('='*90)

    # --- Generate JSON_A ---
    json_prompt = (
        "Output this as compact JSON only. Rules:\n"
        "- If any field is NOT mentioned in the data description, output it as `null`.\n"
        "- Never use default values like 0, false, or empty string.\n"
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

    # --- Generate TOON ---
    toon_prompt = toon_generation_prompt_base + "\nData:\n" + data_desc
    resp_toon = client.chat.completions.create(
        messages=[{"role": "user", "content": toon_prompt}],
        model=MODEL,
        stream=False,
        max_completion_tokens=1000,
        temperature=0.3,
        top_p=0.95
    )
    toon_out = resp_toon.choices[0].message.content.strip()

    # --- Convert TOON → JSON_B ---
    conv_prompt = toon_to_json_prompt_base + "\n" + toon_out
    resp_json_b = client.chat.completions.create(
        messages=[{"role": "user", "content": conv_prompt}],
        model=MODEL,
        stream=False,
        max_completion_tokens=1000,
        temperature=0.0,
        top_p=0.95
    )
    json_B = resp_json_b.choices[0].message.content.strip()
    for m in ["```json", "```"]:
        if json_B.startswith(m):
            json_B = json_B[len(m):].strip()
            if json_B.endswith("```"):
                json_B = json_B[:-3].strip()
            break

    # === DISPLAY ===
    print("\n" + "="*90)
    print("📄 JSON_A (Direct):")
    print(json_A)
    print("\n" + "="*90)
    print("📄 TOON:")
    print(toon_out)
    print("\n" + "="*90)
    print("📄 JSON_B (TOON → JSON):")
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

    # --- Validation ---
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

    if re.search(r'\bYES\b', raw_verdict, re.IGNORECASE):
        verdict = "YES"
    elif re.search(r'\bNO\b', raw_verdict, re.IGNORECASE):
        verdict = "NO"
    else:
        verdict = "NO"

    print("\n" + "="*90)
    print(f"✅ VALIDATION (JSON_A vs JSON_B): {verdict}")
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