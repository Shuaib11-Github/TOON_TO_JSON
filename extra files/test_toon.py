from toon_format import encode, decode
import sys
import json

# ==============================================================================
# TEST CASES
# ==============================================================================

# A comprehensive list of test cases, including simple, nested, and complex data.
test_cases = [
    # --- Simple Cases ---
    {
        "name": "Simple Object", 
        "json": '{"name":"Alice","age":30,"active":true,"salary":75000}'
    },
    {
        "name": "Empty Array", 
        "json": '{"users":[]}'
    },
    
    # --- Previously Defined Cases ---
    {
        "name": "Fitness App", 
        "json": '{"app":"FitTrack","users":[{"id":201,"name":"Maya","age":null,"plan":"premium","goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"plan":"basic","goals":["running"]}]}'
    },
    {
        "name": "Tabular User Data", 
        "json": json.dumps({
            "users": [
                { "id": 1, "name": "Sreeni", "role": "admin" },
                { "id": 2, "name": "Krishna", "role": "admin" },
                { "id": 3, "name": "Aaron", "role": "user" }
            ]
        })
    },
    {
        "name": "Hikes Data", 
        "json": json.dumps({
            "context":{"task":"Our favorite hikes together","location":"Boulder","season":"spring_2025"},
            "friends":["ana","luis","sam"],
            "hikes":[
                {"id":1,"name":"Blue Lake Trail","distanceKm":7.5,"elevationGain":320,"companion":"ana","wasSunny":True},
                {"id":2,"name":"Ridge Overlook","distanceKm":9.2,"elevationGain":540,"companion":"luis","wasSunny":False},
                {"id":3,"name":"Wildflower Loop","distanceKm":5.1,"elevationGain":180,"companion":"sam","wasSunny":True}
            ]
        })
    },
    
    # --- NEW COMPLEX TEST CASE 1: Advanced E-Commerce Product ---
    # This tests nested objects (`details`), list of objects (`reviews`), 
    # and a complex list of objects with nested attributes and lists (`variants`).
    {
        "name": "Advanced E-Commerce Product",
        "json": json.dumps({
            "product_id": "HW-GTR-09B",
            "name": "Quantum Guitar",
            "is_active": True,
            "details": {"description": "A guitar that plays all possible solos at once.", "rating": 4.9},
            "tags": ["music", "tech", "quantum"],
            "reviews": [
                {"user": "Alice", "rating": 5, "comment": "Amazing!"},
                {"user": "Bob", "rating": 4, "comment": "A bit loud."}
            ],
            "variants": [
                {"sku": "QG-RD-01", "stock": 10, "attributes": {"color": "Red", "material": "Vibranium"}, "image_urls": ["url1.jpg", "url2.jpg"]},
                {"sku": "QG-BL-02", "stock": 5, "attributes": {"color": "Blue", "material": "Adamantium"}, "image_urls": ["url3.jpg"]},
                {"sku": "QG-BK-03", "stock": 0, "attributes": {"color": "Black", "material": None}, "image_urls": []}
            ]
        })
    },

    # --- NEW COMPLEX TEST CASE 2: CI/CD Pipeline Config ---
    # This tests deeply nested arrays of objects (stages -> jobs -> steps).
    {
        "name": "CI/CD Pipeline Config",
        "json": json.dumps({
            "pipeline_name": "WebApp-Deploy",
            "trigger_on": ["push:main", "pull_request:main"],
            "env": {},
            "stages": [
                {
                    "name": "Build",
                    "jobs": [
                        {"name": "Compile-App", "runner": "ubuntu-latest", "steps": [
                            {"name": "Checkout", "uses": "actions/checkout@v2"},
                            {"name": "Build", "run": "npm run build"}
                        ]}
                    ]
                },
                {
                    "name": "Test",
                    "jobs": [
                        {"name": "Unit-Tests", "runner": "ubuntu-latest", "steps": [
                            {"name": "Run tests", "run": "npm test"}
                        ]},
                        {"name": "Linting", "runner": "ubuntu-latest", "steps": [
                            {"name": "Run linter", "run": "npm run lint"}
                        ]}
                    ]
                }
            ]
        })
    }
]

# ==============================================================================
# HELPER FUNCTION
# ==============================================================================

def perform_memory_comparison(json_str, toon_str, case_name):
    """Calculates and prints the size comparison between JSON and TOON strings."""
    json_bytes = len(json_str.encode('utf-8'))
    toon_bytes = len(toon_str.encode('utf-8'))

    print("\n" + "="*50)
    print(f"📊 MEMORY COMPARISON for '{case_name}' (UTF-8 Bytes):")
    print(f"  JSON size  : {json_bytes:,} bytes")
    print(f"  TOON size  : {toon_bytes:,} bytes")

    if json_bytes > 0:
        reduction = (1 - toon_bytes / json_bytes) * 100
        saved = json_bytes - toon_bytes
        print(f"  Reduction  : {reduction:.1f}%")
        print(f"  Saved      : {saved:,} bytes")
    else:
        print("  (Cannot calculate reduction for empty JSON)")
    print("="*50)

# ==============================================================================
# MAIN EXECUTION LOOP
# ==============================================================================

# Loop through each test case, encode, decode, and compare sizes.
for i, case in enumerate(test_cases):
    case_name = case['name']
    original_json_str = case['json']
    
    print("\n" + "#"*80)
    print(f"##  Running Test Case {i+1}: {case_name}")
    print("#"*80)

    # 1. Parse the original JSON string into a Python object
    try:
        original_data = json.loads(original_json_str)
        print("\n--- Original Python Object ---")
        # Pretty-print the JSON for readability
        print(json.dumps(original_data, indent=2))
    except json.JSONDecodeError as e:
        print(f"Error: Could not parse JSON for case '{case_name}'. Skipping. Details: {e}")
        continue

    # 2. Encode the Python object to TOON format
    print("\n--- Encoded TOON String ---")
    encoded_toon_str = encode(original_data)
    print(encoded_toon_str)

    # 3. Decode the TOON string back to a Python object
    print("\n--- Decoded Python Object ---")
    decoded_data = decode(encoded_toon_str)
    print(json.dumps(decoded_data, indent=2))

    # 4. Perform and print the memory comparison
    perform_memory_comparison(original_json_str, encoded_toon_str, case_name)

    # 5. Verify that the decoded data matches the original data
    print("\n--- Verification ---")
    if original_data == decoded_data:
        print("✅ Success: Decoded data matches original data.")
    else:
        print("❌ Error: Decoded data DOES NOT match original data.")