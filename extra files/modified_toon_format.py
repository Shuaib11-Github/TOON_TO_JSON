# import json

# # ==============================================================================
# # CUSTOM FUNCTION TO GENERATE THE COMPACT TOON FORMAT
# # This function programmatically implements the rules from your successful prompt.
# # ==============================================================================
# def json_to_compact_toon(data, indent_level=0):
#     """
#     Converts a Python object (from JSON) to the compact TOON format.
#     """
#     lines = []
#     indent = '  ' * indent_level

#     # Helper to format scalar values according to TOON rules
#     def format_value(v):
#         if v is None:
#             return ''
#         if isinstance(v, bool):
#             return str(v).lower()
#         return str(v)

#     if not isinstance(data, dict):
#         raise TypeError("Top-level data must be a dictionary.")

#     for key, value in data.items():
#         if isinstance(value, dict):
#             lines.append(f"{indent}{key}:")
#             lines.append(json_to_compact_toon(value, indent_level + 1))
        
#         elif isinstance(value, list):
#             if not value: # Empty list
#                 lines.append(f"{indent}{key}[0]:")
#                 continue

#             # Check if it's a list of objects (for tabular format)
#             if all(isinstance(item, dict) for item in value):
#                 headers = list(value[0].keys())
#                 header_str = ','.join(headers)
#                 lines.append(f"{indent}{key}[{len(value)}]{{{header_str}}}:")
                
#                 for item_dict in value:
#                     row_values = []
#                     for header in headers:
#                         cell_val = item_dict.get(header)
#                         # If a cell value is itself a list, comma-separate it
#                         if isinstance(cell_val, list):
#                             row_values.append(','.join(map(format_value, cell_val)))
#                         else:
#                             row_values.append(format_value(cell_val))
#                     lines.append(f"{indent}  " + ','.join(row_values))
            
#             # It's a list of primitives
#             else:
#                 list_str = ','.join(map(format_value, value))
#                 lines.append(f"{indent}{key}[{len(value)}]: {list_str}")

#         # It's a scalar value
#         else:
#             lines.append(f"{indent}{key}: {format_value(value)}")
            
#     return '\n'.join(lines)


# def evaluate_custom_formatter(json_str, case_name="Test"):
#     print(f"\n{'='*80}")
#     print(f"🧪 PROCESSING: {case_name} (with Custom Function)")
#     print('='*80)
    
#     try:
#         original_obj = json.loads(json_str)
#     except json.JSONDecodeError as e:
#         print(f"❌ Invalid JSON: {e}")
#         return

#     # Generate TOON using our local, custom function
#     toon_out = json_to_compact_toon(original_obj)

#     # Memory stats
#     json_bytes = len(json_str.encode('utf-8'))
#     toon_bytes = len(toon_out.encode('utf-8'))
#     reduction = (1 - toon_bytes / json_bytes) * 100 if json_bytes > 0 else 0
#     saved = json_bytes - toon_bytes

#     # Output
#     print(f"📊 JSON: {json_bytes:,} bytes | TOON: {toon_bytes:,} bytes | Saved: {saved:,} bytes ({reduction:.1f}%)")
#     print("\n📄 TOON:")
#     print(toon_out)


# # ==============================================================================
# # DEFINE MULTIPLE JSON INPUTS (UNCHANGED)
# # ==============================================================================
# test_cases = [
#     {
#         "name": "Simple Object",
#         "json": '{"id":123,"name":"Ada","active":true,"salary":75000}'
#     },
#     {
#         "name": "Fitness App (Complex)",
#         "json": '{"app":"FitTrack","users":[{"id":201,"name":"Maya","age":null,"goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"goals":["running"]}]}'
#     },
#     {
#         "name": "E-Commerce",
#         "json": '{"order_id":"ORD-789","items":[{"sku":"LAP-202","name":"Laptop","price":1200}]}'
#     },
#     {
#         "name": "Empty Array",
#         "json": '{"users":[]}'
#     },
#     {
#         "name": "Hikes Data",
#         "json": json.dumps({
#             "context": { "task": "Our favorite hikes together", "location": "Boulder", "season": "spring_2025" },
#             "friends": ["ana", "luis", "sam"],
#             "hikes": [
#                 { "id": 1, "name": "Blue Lake Trail", "distanceKm": 7.5, "elevationGain": 320, "companion": "ana", "wasSunny": True },
#                 { "id": 2, "name": "Ridge Overlook", "distanceKm": 9.2, "elevationGain": 540, "companion": "luis", "wasSunny": False },
#                 { "id": 3, "name": "Wildflower Loop", "distanceKm": 5.1, "elevationGain": 180, "companion": "sam", "wasSunny": True }
#             ]
#         }, separators=(',', ':'))
#     },
#     {
#         "name": "Fitness App (Nested Profile)",
#         "json": json.dumps({
#             "app": "FitTrack",
#             "users": [
#                 { "id": 201, "name": "Maya", "plan": "premium", "profile": { "age": None, "goals": ["weight_loss", "strength"] } },
#                 { "id": 202, "name": "Ravi", "plan": "basic", "profile": { "age": 35, "goals": ["running"] } }
#             ]
#         }, separators=(',', ':'))
#     },
#     {
#         "name": "E-Commerce Order",
#         "json": json.dumps({
#             "order_id": "ORD-789",
#             "customer": { "id": 501, "name": "Priya Mehta", "email": "priya@example.com" },
#             "shipping_address": { "street": "123 Main St", "city": "Mumbai", "country": "India" },
#             "items": [
#                 { "sku": "LAP-202", "name": "Gaming Laptop", "price": 1200, "metadata": { "warranty": "2 years", "category": "Electronics" } },
#                 { "sku": "MOUSE-55", "name": "Wireless Mouse", "price": 25, "metadata": { "warranty": "1 year", "category": "Accessories" } }
#             ],
#             "status": "shipped"
#         }, separators=(',', ':'))
#     },
#     {
#         "name": "Tabular Array",
#         "json": json.dumps({
#             "users": [
#                 {"id": 1, "name": "Alice", "role": "admin"},
#                 {"id": 2, "name": "Bob", "role": "user"}
#             ]
#         }, separators=(',', ':'))
#     },
#     {
#         "name": "Analytics Data",
#         "json": json.dumps({
#             "metrics": [
#                 { "date": "2025-01-01", "views": 6890, "clicks": 401, "conversions": 23, "revenue": 6015.59, "bounceRate": 0.63 },
#                 { "date": "2025-01-02", "views": 6940, "clicks": 323, "conversions": 37, "revenue": 9086.44, "bounceRate": 0.36 }
#             ]
#         }, separators=(',', ':'))
#     }
# ]

# # ==============================================================================
# # RUN BATCH
# # ==============================================================================
# if __name__ == "__main__":
#     print("🚀 Evaluating Custom TOON Formatter")
    
#     for case in test_cases:
#         evaluate_custom_formatter(case["json"], case["name"])
    
#     print("\n" + "="*80)
#     print("✅ All test cases processed.")
#     print("="*80)



import json
import re

# ==============================================================================
# PART 1: GENERATOR with Unambiguous Syntax
# ==============================================================================
def json_to_compact_toon(data, indent_level=0):
    lines = []
    indent_str = '  ' * indent_level

    def format_value(v):
        if v is None: return ''
        if isinstance(v, bool): return str(v).lower()
        if isinstance(v, list): return f"[{','.join(map(str, v))}]" # RULE 1: Lists are bracketed
        return str(v)

    if not isinstance(data, dict):
        raise TypeError("Top-level data must be a dictionary.")

    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{indent_str}{key}:")
            lines.append(json_to_compact_toon(value, indent_level + 1))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{indent_str}{key}[0]:")
                continue

            if all(isinstance(item, dict) for item in value):
                # RULE 2: Flatten nested objects using dot notation for headers
                flat_headers = set()
                for item in value:
                    for k, v in item.items():
                        if isinstance(v, dict):
                            for sub_k in v.keys():
                                flat_headers.add(f"{k}.{sub_k}")
                        else:
                            flat_headers.add(k)
                
                sorted_headers = sorted(list(flat_headers))
                lines.append(f"{indent_str}{key}[{len(value)}]{{{','.join(sorted_headers)}}}:")

                for item_dict in value:
                    row_values = []
                    for header in sorted_headers:
                        if '.' in header:
                            main_key, sub_key = header.split('.', 1)
                            cell_val = item_dict.get(main_key, {}).get(sub_key)
                        else:
                            cell_val = item_dict.get(header)
                        row_values.append(format_value(cell_val))
                    lines.append(f"{indent_str}  " + ','.join(row_values))
            else: # List of primitives
                list_str = ','.join(map(format_value, value))
                lines.append(f"{indent_str}{key}[{len(value)}]: {list_str}")
        else: # Scalar
            lines.append(f"{indent_str}{key}: {format_value(value)}")
            
    return '\n'.join(lines)

# ==============================================================================
# PART 2: PARSER for Unambiguous Syntax
# ==============================================================================
def _coerce_type(value_str):
    s = value_str.strip()
    if not s: return None
    if s == 'true': return True
    if s == 'false': return False
    # RULE 1 PARSING: Check for bracketed list
    if s.startswith('[') and s.endswith(']'):
        content = s[1:-1]
        if not content: return []
        return [_coerce_type(v) for v in content.split(',')]
    try: return int(s)
    except ValueError:
        try: return float(s)
        except ValueError: return s

def toon_to_json(toon_string):
    lines = [line for line in toon_string.strip().split('\n') if line.strip()]
    obj, _ = _parse_block(lines, 0)
    return obj

def _parse_block(lines, start_index):
    result = {}
    i = start_index
    if i >= len(lines): return result, i
    base_indent = len(lines[i]) - len(lines[i].lstrip(' '))

    while i < len(lines):
        line = lines[i]
        indent = len(line) - len(line.lstrip(' '))
        if indent < base_indent: return result, i

        line = line.strip()

        match_scalar = re.match(r'^([\w_]+):\s*(.*)$', line)
        if match_scalar:
            key, value_str = match_scalar.groups()
            result[key] = _coerce_type(value_str)
            i += 1
            continue

        match_object = re.match(r'^([\w_]+):$', line)
        if match_object:
            key = match_object.groups()[0]
            result[key], i = _parse_block(lines, i + 1)
            continue
            
        match_prim_list = re.match(r'^([\w_]+)\[\d*\]:\s*(.*)$', line)
        if match_prim_list:
            key, values_str = match_prim_list.groups()
            result[key] = [_coerce_type(v) for v in values_str.split(',')] if values_str else []
            i += 1
            continue

        match_table = re.match(r'^([\w_]+)\[(\d+)\]\{(.*)\}:$', line)
        if match_table:
            key, count_str, headers_str = match_table.groups()
            count = int(count_str)
            headers = headers_str.split(',')
            table_data = []
            
            data_rows_start = i + 1
            for j in range(count):
                row_line = lines[data_rows_start + j].strip()
                values = row_line.split(',')
                
                row_obj = {}
                for h, v_str in zip(headers, values):
                    val = _coerce_type(v_str)
                    # RULE 2 PARSING: Unflatten dot notation
                    if '.' in h:
                        main_key, sub_key = h.split('.', 1)
                        if main_key not in row_obj: row_obj[main_key] = {}
                        row_obj[main_key][sub_key] = val
                    else:
                        row_obj[h] = val
                table_data.append(row_obj)
            
            result[key] = table_data
            i = data_rows_start + count
            continue
        i += 1
    return result, i

# ==============================================================================
# PART 3: EVALUATION AND COMPARISON LOGIC (Unchanged)
# ==============================================================================
def evaluate_and_compare(json_str, case_name="Test"):
    print(f"\n{'='*90}")
    print(f"🧪 RUNNING: {case_name}")
    print('='*90)
    
    original_obj = json.loads(json_str)
    compact_json_str = json.dumps(original_obj, separators=(',', ':'))
    print("📄 ORIGINAL JSON:")
    print(compact_json_str)

    toon_out = json_to_compact_toon(original_obj)
    print("\n" + "="*90)
    print("📄 GENERATED TOON:")
    print(toon_out)

    decoded_obj = {}
    error_msg = None
    try:
        decoded_obj = toon_to_json(toon_out)
    except Exception as e:
        error_msg = f"Decode failed: {e}"

    is_match = original_obj == decoded_obj
    
    print("\n" + "="*90)
    print("📊 COMPARISON & MEMORY:")
    if error_msg:
        print(f"❌ VALIDATION: {error_msg}")
    else:
        print(f"✅ VALIDATION (Original vs Decoded): {'MATCH' if is_match else 'MISMATCH'}")

    json_bytes = len(compact_json_str.encode('utf-8'))
    toon_bytes = len(toon_out.encode('utf-8'))
    print(f"JSON size  : {json_bytes:,} bytes")
    print(f"TOON size  : {toon_bytes:,} bytes")

    if json_bytes > 0:
        reduction = (1 - toon_bytes / json_bytes) * 100
        saved = json_bytes - toon_bytes
        print(f"Reduction  : {reduction:.1f}%")
        print(f"Saved      : {saved:,} bytes")
    print("="*90)
    return is_match

# ==============================================================================
# TEST CASES (Same as before)
# ==============================================================================
test_cases = [
    # ... (Your full list of test cases goes here) ...
    {
        "name": "Simple Object",
        "json": '{"id":123,"name":"Ada","active":true,"salary":75000}'
    },
    {
        "name": "Fitness App (Complex)",
        "json": '{"app":"FitTrack","users":[{"id":201,"name":"Maya","age":null,"goals":["weight_loss","strength"]},{"id":202,"name":"Ravi","age":35,"goals":["running"]}]}'
    },
    {
        "name": "E-Commerce (Simple)",
        "json": '{"order_id":"ORD-789","items":[{"sku":"LAP-202","name":"Laptop","price":1200}]}'
    },
    {
        "name": "Empty Array",
        "json": '{"users":[]}'
    },
    {
        "name": "Hikes Data",
        "json": json.dumps({
            "context": { "task": "Our favorite hikes together", "location": "Boulder", "season": "spring_2025" },
            "friends": ["ana", "luis", "sam"],
            "hikes": [
                { "id": 1, "name": "Blue Lake Trail", "distanceKm": 7.5, "elevationGain": 320, "companion": "ana", "wasSunny": True },
                { "id": 2, "name": "Ridge Overlook", "distanceKm": 9.2, "elevationGain": 540, "companion": "luis", "wasSunny": False },
                { "id": 3, "name": "Wildflower Loop", "distanceKm": 5.1, "elevationGain": 180, "companion": "sam", "wasSunny": True }
            ]
        })
    },
    {
        "name": "E-Commerce Order (Complex)",
        "json": json.dumps({
            "order_id": "ORD-789",
            "customer": { "id": 501, "name": "Priya Mehta", "email": "priya@example.com" },
            "shipping_address": { "street": "123 Main St", "city": "Mumbai", "country": "India" },
            "items": [
                { "sku": "LAP-202", "name": "Gaming Laptop", "price": 1200, "metadata": { "warranty": "2 years", "category": "Electronics" } },
                { "sku": "MOUSE-55", "name": "Wireless Mouse", "price": 25, "metadata": { "warranty": "1 year", "category": "Accessories" } }
            ],
            "status": "shipped"
        })
    },
    {
        "name": "Tabular Array",
        "json": json.dumps({
            "users": [
                {"id": 1, "name": "Alice", "role": "admin"},
                {"id": 2, "name": "Bob", "role": "user"}
            ]
        })
    },
    {
        "name": "Analytics Data",
        "json": json.dumps({
            "metrics": [
                { "date": "2025-01-01", "views": 6890, "clicks": 401, "conversions": 23, "revenue": 6015.59, "bounceRate": 0.63 },
                { "date": "2025-01-02", "views": 6940, "clicks": 323, "conversions": 37, "revenue": 9086.44, "bounceRate": 0.36 }
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
# RUN BATCH
# ==============================================================================
if __name__ == "__main__":
    print("🚀 Full Round-Trip Validation with Custom Formatter 🚀")
    results = []
    
    for case in test_cases:
        is_match = evaluate_and_compare(case["json"], case["name"])
        results.append((case["name"], is_match))
    
    # Final summary
    print("\n" + "="*90)
    print("🎯 FINAL SUMMARY:")
    all_pass = True
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:<30} → {status}")
        if not passed:
            all_pass = False
    
    print("="*90)
    print(f"OVERALL: {'✅ ALL PASS' if all_pass else '⚠️ SOME TESTS FAILED'}")