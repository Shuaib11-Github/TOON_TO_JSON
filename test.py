from toon_format import encode, decode
import sys
import json

a = encode({
    "app": "FitTrack", 
    "users": [
        {"id": 201, "name": "Maya", "age": None, "plan": "premium", "goals": ["weight_loss", "strength"]}, 
        {"id": 202, "name": "Ravi", "age": 35, "plan": "basic", "goals": ["running"]}
        ]
})

b = encode({
    'app': 'FitTrack', 
    'users': [
        {'id': 201, 'name': 'Maya', 'age': None, 'plan': 'premium', 'goals': ['weight_loss', 'strength']}, 
        {'id': 202, 'name': 'Ravi', 'age': 35, 'plan': 'basic', 'goals': ['running']}
        ]
})
print(a)

print("-"*50)
print(decode(a))


def get_object_size(obj):
    """Get size of object in bytes"""
    return sys.getsizeof(obj)

def compare_sizes(original, encoded, decoded, label):
    """Compare sizes of original, encoded and decoded data"""
    original_size = get_object_size(str(original).encode('utf-8'))  # Approximate JSON size
    encoded_size = get_object_size(encoded)
    decoded_size = get_object_size(str(decoded).encode('utf-8'))
    
    print(f"\n{label} Size Analysis:")
    print(f"  Original (approx): {original_size} bytes")
    print(f"  Encoded: {encoded_size} bytes")
    print(f"  Decoded (approx): {decoded_size} bytes")
    print(f"  Compression ratio: {original_size/encoded_size:.2f}x")

# Data 1
data1 = {"name": "Alice", "age": 30}
a = encode(data1)
print(a)
print("-"*50)

# Data 2
data2 = {
  "users": [
    { "id": 1, "name": "Sreeni", "role": "admin" },
    { "id": 2, "name": "Krishna", "role": "admin" },
    { "id": 3, "name": "Aaron", "role": "user" }
  ]
}
b = encode(data2)
print(b)
print("-"*50)

# Data 3
data3 = {
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
}
c = encode(data3)
print(c)
print("-"*50)

### Decoding the above encoded strings back to original data structures
print("Decoding the encoded strings back to original data structures")
x = decode(a)
y = decode(b)
z = decode(c)

print(x)
print("-"*50)
print(y)
print("-"*50)
print(z)
print("-"*50)

# Size comparison
compare_sizes(data1, a, x, "Data 1")
compare_sizes(data2, b, y, "Data 2")
compare_sizes(data3, c, z, "Data 3")