import os
import re
import json
from cerebras.cloud.sdk import Cerebras

# 🔑 CONFIG
# Make sure to replace with your actual API key if needed
client = Cerebras(api_key="csk-kt9c5e52jch9htp4vdmepd3kr43ey95w53w6pj6mcx9x4e95") 
MODEL = "llama-3.3-70b"

# ============================================================================
# PROMPT 1: DATA → TOON GENERATION
# ============================================================================
toon_generation_prompt_base = '''You output ONLY in TOON format.

RULES:
- Simple value (string/number/bool): `key: value` → e.g., `app: FitTrack`
- Object: `key:` then indented fields
- Array of objects: `users[2]{id,name,profile}:`
- Nested object in row: `profile{age,goals}:` → next indented line has values
- List fields (e.g., goals, tags): output as comma-separated values on one line
- If a field value is NOT provided or is `null`, output it as EMPTY (e.g., use `, ,` in data rows)
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

Example 5 (missing optional field from null):
app: HealthApp
users[2]{id,name,age,goals}:
  301,Alex,,cardio
  302,Sam,29,running,yoga

Now convert this data to TOON. Output ONLY TOON.
'''

# ============================================================================
# PROMPT 2: TOON → JSON CONVERSION
# ============================================================================
toon_to_json_prompt_base = '''You are an expert data converter. Convert TOON to valid JSON.

RULES:
- `key: value` → simple field (string/number/bool)
- `key:` → object with indented sub-fields
- `list[n]{...}:` → array of objects
- Fields with comma-separated values → convert to JSON array
- Empty values in data rows (e.g., `, ,`) → convert to `null` in JSON
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

Example 6 (Top-level array):
TOON:
users[2]{id,name}:
1,Alice
2,Bob

JSON:
{
  "users": [
    { "id": 1, "name": "Alice" },
    { "id": 2, "name": "Bob" }
  ]
}

Now convert the following TOON to JSON. Output ONLY valid JSON. No extra text.
'''

# ============================================================================
# PROMPT 3: VALIDATION
# ============================================================================
def make_validation_prompt(json_a, json_b):
    return f'''Compare these two JSON objects.

JSON_A:
{json_a}

JSON_B:
{json_b}

Rules:
- All fields must match exactly in type and value.
- Ignore key order and whitespace.

Are they semantically equivalent? Answer ONLY the word "YES" or "NO".
'''

# ============================================================================
# TEST FUNCTION: For JSON -> TOON -> JSON workflow
# ============================================================================
def run_json_test_case(json_input_str, test_name="Test"):
    print(f"\n{'='*90}")
    print(f"🧪 RUNNING: {test_name} (JSON Input)")
    print('='*90)

    try:
        original_obj = json.loads(json_input_str)
        json_A = json.dumps(original_obj, separators=(',', ':'))
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid input JSON for test '{test_name}'. {e}")
        return False
    
    # Generate TOON from JSON
    toon_prompt = toon_generation_prompt_base + "\nJSON:\n" + json_A
    resp_toon = client.chat.completions.create(
        messages=[{"role": "user", "content": toon_prompt}],
        model=MODEL, stream=False, max_completion_tokens=2000, temperature=0.1
    )
    toon_out = resp_toon.choices[0].message.content.strip()

    # Convert TOON back to JSON
    conv_prompt = toon_to_json_prompt_base + "\n" + toon_out
    resp_json_b = client.chat.completions.create(
        messages=[{"role": "user", "content": conv_prompt}],
        model=MODEL, stream=False, max_completion_tokens=2000, temperature=0.0
    )
    json_B = resp_json_b.choices[0].message.content.strip()
    json_B = re.sub(r'^```json\s*|\s*```$', '', json_B, flags=re.MULTILINE).strip()

    # Display results
    print("📄 JSON_A (Original):")
    print(json_A)
    print("\n📄 TOON (Generated):")
    print(toon_out)
    print("\n📄 JSON_B (Round-trip):")
    print(json_B)

    # Memory comparison
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

    # Validation
    val_prompt = make_validation_prompt(json_A, json_B)
    resp_val = client.chat.completions.create(
        messages=[{"role": "user", "content": val_prompt}],
        model=MODEL, stream=False, max_completion_tokens=20, temperature=0.0
    )
    raw_verdict = resp_val.choices[0].message.content.strip()
    verdict = "YES" if re.search(r'\bYES\b', raw_verdict, re.IGNORECASE) else "NO"

    print("\n" + "="*90)
    print(f"✅ VALIDATION (JSON_A vs JSON_B): {verdict}")
    print("="*90)
    
    return verdict == "YES"

# ============================================================================
# FULL BATCH OF TEST CASES
# ============================================================================
test_cases = [
    {
        "name": "Simple Object",
        "json": '{"id":123,"name":"Ada","active":true,"salary":75000}'
    },
    {
        "name": "Fitness App (Complex)",
        "json": '{"app":"FitTrack","users":[{"id":201,"name":"Maya","age":null,"goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"goals":["running"]}]}'
    },
    {
        "name": "E-Commerce",
        "json": '{"order_id":"ORD-789","items":[{"sku":"LAP-202","name":"Laptop","price":1200}]}'
    },
    {
        "name": "Empty Array",
        "json": '{"users":[]}'
    },
    {
        "name": "Hikes Data",
        "json": json.dumps({
            "context": {
                "task": "Our favorite hikes together",
                "location": "Boulder",
                "season": "spring_2025"
            },
            "friends": ["ana", "luis", "sam"],
            "hikes": [
                {"id": 1, "name": "Blue Lake Trail", "distanceKm": 7.5, "elevationGain": 320, "companion": "ana", "wasSunny": True},
                {"id": 2, "name": "Ridge Overlook", "distanceKm": 9.2, "elevationGain": 540, "companion": "luis", "wasSunny": False},
                {"id": 3, "name": "Wildflower Loop", "distanceKm": 5.1, "elevationGain": 180, "companion": "sam", "wasSunny": True}
            ]
        }, separators=(',', ':'))
    },
    {
        "name": "Fitness App (Nested Profile)",
        "json": json.dumps({
            "app": "FitTrack", "users": [
                {"id": 201, "name": "Maya", "plan": "premium", "profile": {"age": None, "goals": ["weight_loss", "strength"]}},
                {"id": 202, "name": "Ravi", "plan": "basic", "profile": {"age": 35, "goals": ["running"]}}
            ]
        }, separators=(',', ':'))
    },
    {
        "name": "E-Commerce Order",
        "json": json.dumps({
            "order_id": "ORD-789",
            "customer": {"id": 501, "name": "Priya Mehta", "email": "priya@example.com"},
            "shipping_address": {"street": "123 Main St", "city": "Mumbai", "country": "India"},
            "items": [
                {"sku": "LAP-202", "name": "Gaming Laptop", "price": 1200, "metadata": {"warranty": "2 years", "category": "Electronics"}},
                {"sku": "MOUSE-55", "name": "Wireless Mouse", "price": 25, "metadata": {"warranty": "1 year", "category": "Accessories"}}
            ],
            "status": "shipped"
        }, separators=(',', ':'))
    },
    {
        "name": "Tabular Array",
        "json": json.dumps({
            "users": [
                {"id": 1, "name": "Alice", "role": "admin"},
                {"id": 2, "name": "Bob", "role": "user"}
            ]
        }, separators=(',', ':'))
    },
    {
        "name": "Analytics Data",
        "json": json.dumps({
            "metrics": [
                {"date": "2025-01-01", "views": 6890, "clicks": 401, "conversions": 23, "revenue": 6015.59, "bounceRate": 0.63},
                {"date": "2025-01-02", "views": 6940, "clicks": 323, "conversions": 37, "revenue": 9086.44, "bounceRate": 0.36}
            ]
        }, separators=(',', ':'))
    }
]

# ============================================================================
# RUN BATCH
# ============================================================================
if __name__ == "__main__":
    print("🚀 STARTING BATCH VALIDATION: JSON -> TOON -> JSON 🚀")
    results = []

    for case in test_cases:
        is_match = run_json_test_case(case["json"], case["name"])
        results.append((case["name"], is_match))

    # --- Final Summary ---
    print("\n" + "="*90)
    print("🎯 FINAL SUMMARY:")
    all_pass = True
    # Use a dictionary to avoid duplicate names in the summary
    summary = {name: passed for name, passed in results}
    for name, passed in summary.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:<40} → {status}")
        if not passed:
            all_pass = False

    print("="*90)
    print(f"OVERALL: {'✅ ALL PASS' if all_pass else '⚠️ SOME TESTS FAILED'}")