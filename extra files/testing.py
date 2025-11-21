from toon_format import encode, decode
import sys
import json

def get_object_size(obj):
    """Get size of object in bytes"""
    return sys.getsizeof(obj)

def compare_sizes(original, encoded, decoded, label):
    """Compare sizes of original, encoded and decoded data"""
    original_json = json.dumps(original, separators=(',', ':'))
    decoded_json = json.dumps(decoded, separators=(',', ':'))
    # Assure encoding is binary for "size"
    original_size = len(original_json.encode('utf-8'))
    encoded_size = len(encoded)
    decoded_size = len(decoded_json.encode('utf-8'))
    print(f"\n{label} Size Analysis:")
    print(f"  Original (JSON): {original_size} bytes")
    print(f"  Encoded: {encoded_size} bytes")
    print(f"  Decoded (JSON): {decoded_size} bytes")
    print(f"  Compression ratio: {original_size/encoded_size:.2f}x")

# Test cases for size measurement
test_cases = [
    ("Data 1", {"name": "Alice", "age": 30}),
    ("Data 2", {
      "users": [
        { "id": 1, "name": "Sreeni", "role": "admin" },
        { "id": 2, "name": "Krishna", "role": "admin" },
        { "id": 3, "name": "Aaron", "role": "user" }
      ]
    }),
    ("Data 3", {
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
    }),
    ("Fitness App", {
        "app": "FitTrack",
        "users": [
            {"id": 201, "name": "Maya", "age": None, "plan": "premium", "goals": ["weight_loss", "strength"]},
            {"id": 202, "name": "Ravi", "age": 35, "plan": "basic", "goals": ["running"]}
        ]
    }),
    ("E-Commerce Order", {
        "order_id": "ORD-789",
        "customer": {"id": 501, "name": "Priya Mehta", "email": "priya@example.com"},
        "items": [
            {"sku": "LAP-202", "name": "Gaming Laptop", "price": 1200, "metadata": {"warranty": "2 years", "category": "Electronics"}},
            {"sku": "MOUSE-55", "name": "Wireless Mouse", "price": 25, "metadata": {"warranty": "1 year", "category": "Accessories"}}
        ],
        "status": "shipped"
    }),
    ("Analytics Data", {
        "metrics": [
            {"date": "2025-01-01", "views": 6890, "clicks": 401, "conversions": 23, "revenue": 6015.59, "bounceRate": 0.63},
            {"date": "2025-01-02", "views": 6940, "clicks": 323, "conversions": 37, "revenue": 9086.44, "bounceRate": 0.36}
        ]
    }),
    ("CI/CD Pipeline", {
        "pipeline_name": "WebApp-Deploy", "trigger_on": ["push:main", "pull_request:main"], "env": {},
        "stages": [
            {"name": "Build", "jobs": [{"name": "Compile-App", "runner": "ubuntu-latest", "steps": [{"name": "Checkout", "uses": "actions/checkout@v2"}, {"name": "Build", "run": "npm run build"}]}]},
            {"name": "Test", "jobs": [{"name": "Unit-Tests", "runner": "ubuntu-latest", "steps": [{"name": "Run tests", "run": "npm test"}]}, {"name": "Linting", "runner": "ubuntu-latest", "steps": [{"name": "Run linter", "run": "npm run lint"}]}]}
        ]
    }),
]

print("="*60)
print("Toon Format Encoding/Decoding and Size Analysis:")
print("="*60)
for label, data in test_cases:
    encoded = encode(data)
    decoded = decode(encoded)
    print(f"\n--- {label} ---")
    print("Encoded:", encoded)
    print("Decoded:", decoded)
    compare_sizes(data, encoded, decoded, label)
    print("-"*60)