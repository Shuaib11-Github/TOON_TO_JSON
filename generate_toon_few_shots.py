from toon_format import encode, decode
import json

# ============================================================================
# TEST CASES: From simple to complex + edge cases
# ============================================================================
test_cases = [
    # 1. Simple flat object
    {
        "name": "test_simple",
        "data": {
            "id": 123,
            "name": "Ada",
            "active": True,
            "salary": 75000.0
        }
    },
    # 2. Top-level list (primitive)
    {
        "name": "test_top_list",
        "data": {
            "tags": ["web", "api", "auth"]
        }
    },
    # 3. Array of flat objects
    {
        "name": "test_flat_array",
        "data": {
            "users": [
                {"id": 1, "name": "Alice", "role": "admin"},
                {"id": 2, "name": "Bob", "role": "user"}
            ]
        }
    },
    # 4. Nested object (no array)
    {
        "name": "test_nested_obj",
        "data": {
            "project": {
                "name": "Apollo",
                "status": "active",
                "config": {
                    "debug": False,
                    "timeout": 30.5
                }
            }
        }
    },
    # 5. Array with nested object + list field
    {
        "name": "test_array_nested_list",
        "data": {
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
        }
    },
    # 6. Deep nesting + mixed types
    {
        "name": "test_deep_complex",
        "data": {
            "order": {
                "id": "ORD-789",
                "customer": {
                    "name": "Priya Mehta",
                    "emails": ["priya@example.com", "priya.work@org.in"]
                },
                "items": [
                    {
                        "sku": "LAP-202",
                        "name": "Gaming Laptop",
                        "price": 1200,
                        "metadata": {
                            "warranty": "2 years",
                            "specs": {
                                "cpu": "i9",
                                "ram_gb": 32,
                                "is_new": True
                            }
                        }
                    }
                ]
            }
        }
    },
    # 7. Edge: empty array
    {
        "name": "test_empty_array",
        "data": {
            "users": []
        }
    },
    # 8. Edge: all null fields
    {
        "name": "test_all_null",
        "data": {
            "profile": {
                "age": None,
                "name": None,
                "goals": None
            }
        }
    },
    # 9. Edge: unicode + special chars
    {
        "name": "test_unicode",
        "data": {
            "message": "Hello, 🌍! Café naïve résumé.",
            "tags": ["café", "naïve", "résumé", "🚀"]
        }
    },
    # 10. Edge: mixed numbers (int, float, scientific)
    {
        "name": "test_numbers",
        "data": {
            "metrics": [
                {"count": 100, "rate": 0.95, "pi_approx": 3.14159},
                {"count": 0, "rate": 0.0, "pi_approx": -1e-5}
            ]
        }
    },
    # 11. Edge: single-item arrays
    {
        "name": "test_single_item",
        "data": {
            "config": {
                "flags": ["enable_new_ui"]
            },
            "admins": [
                {"id": 1, "name": "Admin"}
            ]
        }
    },
    {   
        "name": "test_empty_array",
        "data": {
        "app": "HealthApp",
        "users": [
            {
            "id": 301,
            "name": "Alex",
            "age": None,
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
    }
]

# ============================================================================
# Generate & Validate
# ============================================================================
def generate_fewshots():
    json_to_toon_examples = []
    toon_to_json_examples = []

    print("="*100)
    print("🔍 GENERATING FEWSHOT EXAMPLES FOR TOON FORMAT")
    print("="*100)

    for case in test_cases:
        name = case["name"]
        original = case["data"]

        try:
            # Encode to TOON
            toon_str = encode(original)
            # Decode back
            recovered = decode(toon_str)

            # Validate round-trip
            assert json.dumps(original, sort_keys=True, ensure_ascii=False) == \
                   json.dumps(recovered, sort_keys=True, ensure_ascii=False), \
                   f"Round-trip failed for {name}"

            # Compact JSON for prompt
            compact_json = json.dumps(original, separators=(',', ':'), ensure_ascii=False)

            # Store for prompts
            json_to_toon_examples.append({
                "json": compact_json,
                "toon": toon_str
            })
            toon_to_json_examples.append({
                "toon": toon_str,
                "json": compact_json
            })

            print(f"\n✅ {name}")
            print("JSON →")
            print(compact_json)
            print("TOON →")
            print(toon_str)
            print("-" * 80)

        except Exception as e:
            print(f"\n❌ FAILED: {name} → {e}")

    return json_to_toon_examples, toon_to_json_examples

# ============================================================================
# Format for LLM Prompts
# ============================================================================
def format_json_to_toon_prompt(examples):
    prompt_parts = ["You output ONLY in TOON format.\n\nRULES:"]
    prompt_parts.append("- Simple value: `key: value`")
    prompt_parts.append("- Object: `key:` then indented fields")
    prompt_parts.append("- Array of objects: `items[N]{field1,field2}:`")
    prompt_parts.append("- Nested object in row: `metadata{warranty,category}:` → next indented line has values")
    prompt_parts.append("- List fields: output as comma-separated values (e.g., `goals: a,b`)")
    prompt_parts.append("- Missing field → leave empty (e.g., `, ,`)")
    prompt_parts.append("- NEVER invent values or add extra text")
    prompt_parts.append("- Output ONLY TOON\n\nEXAMPLES:")

    for i, ex in enumerate(examples, 1):
        prompt_parts.append(f"\nExample {i}:")
        prompt_parts.append(f"JSON:\n{ex['json']}")
        prompt_parts.append(f"TOON:\n{ex['toon']}")

    return "\n".join(prompt_parts)

def format_toon_to_json_prompt(examples):
    prompt_parts = ["You are an expert data converter. Convert TOON to valid JSON.\n\nRULES:"]
    prompt_parts.append("- `key: value` → simple field")
    prompt_parts.append("- `key:` → object with indented sub-fields")
    prompt_parts.append("- `list[n]{...}:` → array of objects")
    prompt_parts.append("- Nested object: `field{sub1,sub2}:` → next line has values")
    prompt_parts.append("- Comma-separated list fields → JSON array")
    prompt_parts.append("- Empty values (e.g., `, ,`) → `null`")
    prompt_parts.append("- Output ONLY valid JSON. No extra text.\n\nEXAMPLES:")

    for i, ex in enumerate(examples, 1):
        prompt_parts.append(f"\nExample {i}:")
        prompt_parts.append(f"TOON:\n{ex['toon']}")
        prompt_parts.append(f"JSON:\n{ex['json']}")

    return "\n".join(prompt_parts)

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    json2toon, toon2json = generate_fewshots()

    print("\n" + "="*100)
    print("📋 COPY-PASTE READY PROMPTS")
    print("="*100)

    print("\n\n🔷 JSON → TOON PROMPT (for TOON generation):")
    print("="*60)
    print(format_json_to_toon_prompt(json2toon))

    print("\n\n🔷 TOON → JSON PROMPT (for conversion):")
    print("="*60)
    print(format_toon_to_json_prompt(toon2json))