import os
import re
import json
from cerebras.cloud.sdk import Cerebras
from toon_format import decode  # Import the official decode function
from dotenv import load_dotenv
# Load API key
load_dotenv()
api_key = os.getenv("CEREBRAS_API_KEY")

# 🔑 CONFIG
client = Cerebras(api_key=api_key)
MODEL = "llama-3.3-70b"

# ============================================================================
# PROMPT 1: TOON GENERATION (with flat root + list rules)
# (This prompt remains unchanged)
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
# (This prompt remains unchanged)
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
# (This prompt is now used to compare the two JSON outputs)
# ============================================================================
def make_validation_prompt(json_llm, json_lib): # <<< MODIFIED: Renamed parameters for clarity
    return f'''Compare these two JSON objects.

JSON_LLM (decoded by the LLM):
{json_llm}

JSON_LIB (decoded by the official library):
{json_lib}

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

    # --- Generate JSON_A (Ground Truth from description) ---
    json_prompt = (
        "Output this as compact JSON only. Rules:\n"
        "- If any field is NOT mentioned in the data description, output it as `null`.\n"
        "- Never use default values like 0, false, or empty string.\n"
        "- Only output the JSON object. No extra text.\n\n"
        f"Data:\n{data_desc}"
    )
    resp_json = client.chat.completions.create(
        messages=[{"role": "user", "content": json_prompt}],
        model=MODEL, stream=False, max_completion_tokens=1000, temperature=0.3, top_p=0.95
    )
    json_A = resp_json.choices[0].message.content.strip()
    for m in ["```json", "```"]:
        if json_A.startswith(m):
            json_A = json_A[len(m):].strip()
            if json_A.endswith("```"):
                json_A = json_A[:-3].strip()
            break

    # --- Generate TOON from description ---
    toon_prompt = toon_generation_prompt_base + "\nData:\n" + data_desc
    resp_toon = client.chat.completions.create(
        messages=[{"role": "user", "content": toon_prompt}],
        model=MODEL, stream=False, max_completion_tokens=1000, temperature=0.3, top_p=0.95
    )
    toon_out = resp_toon.choices[0].message.content.strip()

    # --- Convert TOON → JSON_B (using LLM) ---
    conv_prompt = toon_to_json_prompt_base + "\n" + toon_out
    resp_json_b = client.chat.completions.create(
        messages=[{"role": "user", "content": conv_prompt}],
        model=MODEL, stream=False, max_completion_tokens=1000, temperature=0.0, top_p=0.95
    )
    json_B = resp_json_b.choices[0].message.content.strip()
    for m in ["```json", "```"]:
        if json_B.startswith(m):
            json_B = json_B[len(m):].strip()
            if json_B.endswith("```"):
                json_B = json_B[:-3].strip()
            break

    # <<< NEW: Convert TOON → JSON_C using the official toon_format library >>>
    json_C = ""
    try:
        # The decode function returns a Python dictionary. We format it as a JSON string for display and comparison.
        decoded_obj = decode(toon_out)
        json_C = json.dumps(decoded_obj, indent=2)
    except Exception as e:
        json_C = f"Error decoding TOON with 'toon_format' library: {e}"

    # === DISPLAY ===
    print("\n" + "="*90)
    print("📄 JSON_A (Ground Truth from Description):")
    print(json_A)
    print("\n" + "="*90)
    print("📄 TOON (Generated by LLM):")
    print(toon_out)
    print("\n" + "="*90)
    print("📄 JSON_B (TOON → JSON via LLM):")
    print(json_B)
    print("\n" + "="*90)
    print("📄 JSON_C (TOON → JSON via toon_format.decode()):")  # <<< NEW
    print(json_C)

    # --- Memory Comparison ---
    json_bytes = len(json_A.encode('utf-8'))
    toon_bytes = len(toon_out.encode('utf-8'))
    print("\n" + "="*90)
    print("📊 MEMORY COMPARISON")
    print(f"| {'Format':<15} | {'Size (Bytes)':<15} | {'Reduction':<12} |")
    print(f"|{'-'*17}|{'-'*17}|{'-'*14}|")
    print(f"| {'JSON (Baseline)':<15} | {json_bytes:<15,} | {'-':<12} |")
    if json_bytes > 0:
        reduction = (1 - toon_bytes / json_bytes) * 100
        print(f"| {'TOON':<15} | {toon_bytes:<15,} | {f'{reduction:.1f}%':<12} |")
    else:
        print(f"| {'TOON':<15} | {toon_bytes:<15,} | {'N/A':<12} |")

    # --- Validation ---
    # <<< MODIFIED: Compare the LLM's decoding (JSON_B) against the library's decoding (JSON_C) >>>
    verdict = "NO (Decode failed or comparison error)"
    if "Error" not in json_C:
        val_prompt = make_validation_prompt(json_B, json_C)
        resp_val = client.chat.completions.create(
            messages=[{"role": "user", "content": val_prompt}],
            model=MODEL, stream=False, max_completion_tokens=20, temperature=0.0, top_p=0.95
        )
        raw_verdict = resp_val.choices[0].message.content.strip()

        if re.search(r'\bYES\b', raw_verdict, re.IGNORECASE):
            verdict = "YES"
        elif re.search(r'\bNO\b', raw_verdict, re.IGNORECASE):
            verdict = "NO"
        else:
            verdict = "UNKNOWN (Invalid response)"

    print("\n" + "="*90)
    print(f"✅ VALIDATION (LLM Decode vs. Library Decode): {verdict}")  # <<< MODIFIED
    print("="*90)

    return verdict == "YES"

# ============================================================================
# TEST CASES - Using your Provided Data
# ============================================================================
test_data = {
    "Fitness App": {
        "app": "FitTrack",
        "users": [
            {"id": 201, "name": "Maya", "age": None, "plan": "premium", "goals": ["weight_loss", "strength"]},
            {"id": 202, "name": "Ravi", "age": 35, "plan": "basic", "goals": ["running"]}
        ]
    },
    "E-Commerce Order": {
        "order_id": "ORD-789",
        "customer": {"id": 501, "name": "Priya Mehta", "email": "priya@example.com"},
        "items": [
            {"sku": "LAP-202", "name": "Gaming Laptop", "price": 1200, "metadata": {"warranty": "2 years", "category": "Electronics"}},
            {"sku": "MOUSE-55", "name": "Wireless Mouse", "price": 25, "metadata": {"warranty": "1 year", "category": "Accessories"}}
        ],
        "status": "shipped"
    },
    "Analytics Data": {
        "metrics": [
            {"date": "2025-01-01", "views": 6890, "clicks": 401, "conversions": 23, "revenue": 6015.59, "bounceRate": 0.63},
            {"date": "2025-01-02", "views": 6940, "clicks": 323, "conversions": 37, "revenue": 9086.44, "bounceRate": 0.36}
        ]
    },
    "CI/CD Pipeline": {
        "pipeline_name": "WebApp-Deploy", "trigger_on": ["push:main", "pull_request:main"], "env": {},
        "stages": [
            {"name": "Build", "jobs": [{"name": "Compile-App", "runner": "ubuntu-latest", "steps": [{"name": "Checkout", "uses": "actions/checkout@v2"}, {"name": "Build", "run": "npm run build"}]}]},
            {"name": "Test", "jobs": [{"name": "Unit-Tests", "runner": "ubuntu-latest", "steps": [{"name": "Run tests", "run": "npm test"}]}, {"name": "Linting", "runner": "ubuntu-latest", "steps": [{"name": "Run linter", "run": "npm run lint"}]}]}
        ]
    }
}

# ============================================================================
# RUN - Modified to use test_data
# ============================================================================
print("🚀 STARTING ROBUST TOON VALIDATION PIPELINE")
all_tests_passed = True # Flag to track overall results
for test_name, json_data in test_data.items():
    # Generate a simple description from the JSON using json.dumps
    # You might want to customize this depending on the test data complexity
    data_description = json.dumps(json_data, indent=2)  # Generates a JSON string as a description
    # Run the test case
    test_passed = run_test_case(data_description, test_name)
    all_tests_passed = all_tests_passed and test_passed # Update overall result

print("\n" + "="*90)
print("🎯 FINAL SUMMARY:")
for test_name in test_data.keys():
    print(f"{test_name:<20} → {'✅ PASS' if (test_data[test_name] and test_passed) else '❌ FAIL'}")
print(f"OVERALL RESULT: {'✅ PASS' if all_tests_passed else '❌ FAIL'}") # Overall result
print("="*90)