# import json
# import re
# import os
# from dotenv import load_dotenv
# from cerebras.cloud.sdk import Cerebras
# from toon_format import decode

# # Load API key
# load_dotenv()
# api_key = os.getenv("CEREBRAS_API_KEY")
# if not api_key:
#     raise ValueError("❌ Missing CEREBRAS_API_KEY in .env file")

# client = Cerebras(api_key=api_key)
# MODEL = "llama-3.3-70b"

# # ==============================================================================
# # TOON GENERATION PROMPT (JSON → TOON)
# # ==============================================================================
# TOON_PROMPT = '''You are an expert data serializer. Convert JSON to TOON format.

# RULES:
# - Output ONLY TOON. No extra text, no markdown, no explanations.
# - Simple field: `key: value` (e.g., `id: 123`, `active: true`)
# - String values with spaces or special chars: quote them (e.g., `message: "Hello, world!"`)
# - Object: `key:` then indented fields on new lines
# - Array of primitives: `tags[N]: a,b,c`
# - Array of FLAT objects (only scalars): `users[N]{id,name}:` then comma rows
# - Array of COMPLEX objects (with nesting or lists): `users[N]:` then `- field: value` blocks
# - Null value: `null`
# - NEVER invent, omit, or reorder fields.

# EXAMPLES:

# Example 1:
# JSON:
# {"id":123,"name":"Ada","active":true,"salary":75000.0}
# TOON:
# id: 123
# name: Ada
# active: true
# salary: 75000.0

# Example 2:
# JSON:
# {"tags":["web","api","auth"]}
# TOON:
# tags[3]: web,api,auth

# Example 3:
# JSON:
# {"users":[{"id":1,"name":"Alice","role":"admin"},{"id":2,"name":"Bob","role":"user"}]}
# TOON:
# users[2]{id,name,role}:
#   1,Alice,admin
#   2,Bob,user

# Example 4:
# JSON:
# {"project":{"name":"Apollo","status":"active","config":{"debug":false,"timeout":30.5}}}
# TOON:
# project:
#   name: Apollo
#   status: active
#   config:
#     debug: false
#     timeout: 30.5

# Example 5:
# JSON:
# {"users":[{"id":201,"name":"Maya","age":null,"plan":"premium","goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"plan":"basic","goals":["running"]}]}
# TOON:
# users[2]:
#   - id: 201
#     name: Maya
#     age: null
#     plan: premium
#     goals[2]: weight_loss,strength
#   - id: 202
#     name: Ravi
#     age: 35
#     plan: basic
#     goals[1]: running

# Example 6:
# JSON:
# {"order":{"id":"ORD-789","customer":{"name":"Priya Mehta","emails":["priya@example.com","priya.work@org.in"]},"items":[{"sku":"LAP-202","name":"Gaming Laptop","price":1200,"metadata":{"warranty":"2 years","specs":{"cpu":"i9","ram_gb":32,"is_new":true}}}]}}
# TOON:
# order:
#   id: ORD-789
#   customer:
#     name: Priya Mehta
#     emails[2]: priya@example.com,priya.work@org.in
#   items[1]:
#     - sku: LAP-202
#       name: Gaming Laptop
#       price: 1200
#       metadata:
#         warranty: 2 years
#         specs:
#           cpu: i9
#           ram_gb: 32
#           is_new: true

# Example 7:
# JSON:
# {"users":[]}
# TOON:
# users[0]:

# Example 8:
# JSON:
# {"message":"Hello, 🌍! Café naïve résumé.","tags":["café","naïve","résumé","🚀"]}
# TOON:
# message: "Hello, 🌍! Café naïve résumé."
# tags[4]: café,naïve,résumé,🚀

# Now convert this JSON to TOON. Output ONLY TOON.

# JSON:
# {user_json}
# '''

# def fix_truncated_json(s):
#     """Repair common LLM truncation errors."""
#     s = s.strip()
#     s = re.sub(r',\s*([}\]])', r'\1', s)  # Remove trailing commas
#     open_braces = s.count('{')
#     close_braces = s.count('}')
#     open_brackets = s.count('[')
#     close_brackets = s.count(']')
#     s += '}' * (open_braces - close_braces)
#     s += ']' * (open_brackets - close_brackets)
#     return s

# def validate_json_to_toon(user_json_str):
#     try:
#         # Parse user input
#         original_obj = json.loads(user_json_str)
#     except json.JSONDecodeError as e:
#         print(f"❌ Invalid input JSON: {e}")
#         return

#     # Prepare LLM prompt
#     prompt = TOON_PROMPT + "\n" + user_json_str

#     # Call LLM to generate TOON
#     response = client.chat.completions.create(
#         messages=[{"role": "user", "content": prompt}],
#         model=MODEL,
#         stream=False,
#         max_completion_tokens=2000,
#         temperature=0.0,
#         top_p=0.95
#     )
#     toon_output = response.choices[0].message.content.strip()

#     # Decode TOON locally
#     try:
#         decoded_obj = decode(toon_output)
#     except Exception as e:
#         print(f"❌ TOON decode failed: {e}")
#         print("📄 TOON output:")
#         print(toon_output)
#         return

#     # Compare
#     is_equal = original_obj == decoded_obj

#     # Memory stats
#     json_bytes = len(user_json_str.encode('utf-8'))
#     toon_bytes = len(toon_output.encode('utf-8'))
#     reduction = (1 - toon_bytes / json_bytes) * 100 if json_bytes > 0 else 0
#     saved = json_bytes - toon_bytes

#     # Output
#     print("\n" + "="*80)
#     print("✅ VALIDATION RESULT")
#     print("="*80)
#     print(f"Match: {'YES' if is_equal else 'NO'}")
#     print(f"\n📊 MEMORY COMPARISON (UTF-8 Bytes):")
#     print(f"  JSON size : {json_bytes:,} bytes")
#     print(f"  TOON size : {toon_bytes:,} bytes")
#     print(f"  Reduction : {reduction:.1f}%")
#     print(f"  Saved     : {saved:,} bytes")
#     print("\n📄 TOON OUTPUT:")
#     print(toon_output)
#     print("="*80)

# # ==============================================================================
# # MAIN
# # ==============================================================================
# if __name__ == "__main__":
#     # Example: You can replace this with input() for interactive use
#     user_json = '''
#     {
#       "app": "FitTrack",
#       "users": [
#         {
#           "id": 201,
#           "name": "Maya",
#           "age": null,
#           "goals": ["weight_loss", "strength"]
#         },
#         {
#           "id": 202,
#           "name": "Ravi",
#           "age": 35,
#           "goals": ["running"]
#         }
#       ]
#     }
#     '''

#     # Remove whitespace for compactness (optional)
#     user_json = json.dumps(json.loads(user_json), separators=(',', ':'))

#     print("📤 Sending JSON to LLM for TOON conversion...")
#     validate_json_to_toon(user_json)

import json
import os
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras
from toon_format import decode

# Load API key
load_dotenv()
api_key = os.getenv("CEREBRAS_API_KEY")
if not api_key:
    raise ValueError("❌ Missing CEREBRAS_API_KEY in .env file")

client = Cerebras(api_key=api_key)
MODEL = "llama-3.3-70b"

# ==============================================================================
# FULL TOON PROMPT (your exact version)
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

def process_single_json(json_str, case_name="Test"):
    print(f"\n{'='*80}")
    print(f"🧪 PROCESSING: {case_name}")
    print('='*80)
    
    try:
        original = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return False

    # Send to LLM
    prompt = toon_generation_prompt_base + "\n" + json_str
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL,
            stream=False,
            max_completion_tokens=2000,
            temperature=0.0,
            top_p=0.95
        )
        toon_out = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        return False

    # Decode TOON
    try:
        decoded = decode(toon_out)
    except Exception as e:
        print(f"❌ TOON decode failed: {e}")
        print("📄 TOON output:")
        print(toon_out)
        return False

    # Compare
    match = original == decoded

    # Memory stats
    json_bytes = len(json_str.encode('utf-8'))
    toon_bytes = len(toon_out.encode('utf-8'))
    reduction = (1 - toon_bytes / json_bytes) * 100 if json_bytes > 0 else 0
    saved = json_bytes - toon_bytes

    # Output
    print(f"✅ Match: {'YES' if match else 'NO'}")
    print(f"📊 JSON: {json_bytes:,} bytes | TOON: {toon_bytes:,} bytes | Saved: {saved:,} bytes ({reduction:.1f}%)")
    print("\n📄 TOON:")
    print(toon_out)

    return match

# ==============================================================================
# DEFINE MULTIPLE JSON INPUTS
# ==============================================================================
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
                {
                    "id": 1,
                    "name": "Blue Lake Trail",
                    "distanceKm": 7.5,
                    "elevationGain": 320,
                    "companion": "ana",
                    "wasSunny": True
                },
                {
                    "id": 2,
                    "name": "Ridge Overlook",
                    "distanceKm": 9.2,
                    "elevationGain": 540,
                    "companion": "luis",
                    "wasSunny": False
                },
                {
                    "id": 3,
                    "name": "Wildflower Loop",
                    "distanceKm": 5.1,
                    "elevationGain": 180,
                    "companion": "sam",
                    "wasSunny": True
                }
            ]
        }, separators=(',', ':'))
    },
    {
        "name": "Fitness App (Nested Profile)",
        "json": json.dumps({
            "app": "FitTrack",
            "users": [
                {
                    "id": 201,
                    "name": "Maya",
                    "plan": "premium",
                    "profile": {
                        "age": None,
                        "goals": ["weight_loss", "strength"]
                    }
                },
                {
                    "id": 202,
                    "name": "Ravi",
                    "plan": "basic",
                    "profile": {
                        "age": None,
                        "goals": ["running"]
                    }
                }
            ]
        }, separators=(',', ':'))
    },
    {
        "name": "Fitness App (Flat with Optional Age)",
        "json": json.dumps({
            "app": "FitTrack",
            "users": [
                {
                    "id": 201,
                    "name": "Maya",
                    "age": None,
                    "plan": "premium",
                    "goals": ["weight_loss", "strength"]
                },
                {
                    "id": 202,
                    "name": "Ravi",
                    "age": 35,
                    "plan": "basic",
                    "goals": ["running"]
                }
            ]
        }, separators=(',', ':'))
    },
    {
        "name": "Fitness App (Full Nested Profile)",
        "json": json.dumps({
            "app": "FitTrack",
            "users": [
                {
                    "id": 201,
                    "name": "Maya",
                    "plan": "premium",
                    "profile": {
                        "age": 28,
                        "goals": ["weight_loss", "strength"]
                    }
                },
                {
                    "id": 202,
                    "name": "Ravi",
                    "plan": "basic",
                    "profile": {
                        "age": 35,
                        "goals": ["running"]
                    }
                }
            ]
        }, separators=(',', ':'))
    },
    {
        "name": "E-Commerce Order",
        "json": json.dumps({
            "order_id": "ORD-789",
            "customer": {
                "id": 501,
                "name": "Priya Mehta",
                "email": "priya@example.com"
            },
            "shipping_address": {
                "street": "123 Main St",
                "city": "Mumbai",
                "country": "India"
            },
            "items": [
                {
                    "sku": "LAP-202",
                    "name": "Gaming Laptop",
                    "price": 1200,
                    "metadata": {
                        "warranty": "2 years",
                        "category": "Electronics"
                    }
                },
                {
                    "sku": "MOUSE-55",
                    "name": "Wireless Mouse",
                    "price": 25,
                    "metadata": {
                        "warranty": "1 year",
                        "category": "Accessories"
                    }
                }
            ],
            "status": "shipped"
        }, separators=(',', ':'))
    },
    {
        "name": "Simple Object",
        "json": json.dumps({
            "id": 123,
            "name": "Ada",
            "active": True,
            "salary": 75000
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
                {
                    "date": "2025-01-01",
                    "views": 6890,
                    "clicks": 401,
                    "conversions": 23,
                    "revenue": 6015.59,
                    "bounceRate": 0.63
                },
                {
                    "date": "2025-01-02",
                    "views": 6940,
                    "clicks": 323,
                    "conversions": 37,
                    "revenue": 9086.44,
                    "bounceRate": 0.36
                }
            ]
        }, separators=(',', ':'))
    }
]

# ==============================================================================
# RUN BATCH
# ==============================================================================
if __name__ == "__main__":
    print("🚀 BATCH JSON → TOON VALIDATION")
    results = []
    
    for case in test_cases:
        is_match = process_single_json(case["json"], case["name"])
        results.append((case["name"], is_match))
    
    # Final summary
    print("\n" + "="*80)
    print("🎯 FINAL SUMMARY")
    print("="*80)
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:<50} → {status}")
        if not passed:
            all_pass = False
    
    print("="*80)
    print(f"OVERALL: {'✅ ALL PASS' if all_pass else '⚠️  SOME FAILED'}")