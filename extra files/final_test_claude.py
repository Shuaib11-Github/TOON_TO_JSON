import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic

# ----------------------------
# CONFIG
# ----------------------------
load_dotenv()
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise ValueError("❌ Missing ANTHROPIC_API_KEY in .env")

client = Anthropic(api_key=api_key)
MODEL_NAME = "claude-3-5-sonnet-20241022"

# Pricing (per 1M tokens)
INPUT_CACHED_PRICE = 0.30      # $0.30 / 1M cached input tokens
INPUT_UNCACHED_PRICE = 3.00    # $3.00 / 1M uncached input tokens
OUTPUT_PRICE = 15.00           # $15.00 / 1M output tokens

# PROMPTS (same as before)
json_to_toon_prompt_base = '''You are an expert data converter. You convert JSON to the TOON format...

[Your full prompt here – keep it identical to your original]
'''

toon_to_json_prompt_base = '''You are an expert data converter. Convert TOON to valid JSON...

[Your full prompt here]
'''

def estimate_cost(cached_input_tokens, uncached_input_tokens, output_tokens):
    return (
        (cached_input_tokens / 1_000_000) * INPUT_CACHED_PRICE +
        (uncached_input_tokens / 1_000_000) * INPUT_UNCACHED_PRICE +
        (output_tokens / 1_000_000) * OUTPUT_PRICE
    )

def call_claude_cached(user_content, system_prompt, max_tokens=4000):
    """
    Call Claude with prompt caching enabled on the system prompt.
    """
    message = client.messages.create(
        model=MODEL_NAME,
        max_tokens=max_tokens,
        temperature=0.0,
        system=[
            {
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"}  # ← THIS ENABLES CACHING
            }
        ],
        messages=[{"role": "user", "content": user_content}]
    )

    # Extract token usage
    usage = message.usage
    return {
        "text": message.content[0].text.strip(),
        "cached_input_tokens": getattr(usage, 'cache_read_input_tokens', 0),
        "uncached_input_tokens": usage.input_tokens - getattr(usage, 'cache_read_input_tokens', 0),
        "output_tokens": usage.output_tokens,
    }

# Example usage in your pipeline
def json_to_toon_claude(json_str):
    return call_claude_cached(
        user_content=json_str,
        system_prompt=json_to_toon_prompt_base,
        max_tokens=2000
    )

def toon_to_json_claude(toon_str):
    return call_claude_cached(
        user_content=toon_str,
        system_prompt=toon_to_json_prompt_base,
        max_tokens=2000
    )

# ----------------------------
# SIMPLE BENCHMARK
# ----------------------------
test_cases = [
    ('{"name": "Alice", "age": 30}',),
    ('{"score": null, "id": "007"}',),
    ("User A", '{"name": "Alice", "age": 30}'),
    ("User B", '{"name": "Bob", "score": null}'),
    ("Nested Structures", json.dumps({
        "Heterogeneous Array of Objects": {
            "items": [
                {"type": "book", "title": "The Hobbit", "pages": 310},
                {"type": "movie", "title": "The Matrix", "duration_mins": 136},
                {"type": "audiobook", "title": "Dune", "narrator": "Scott Brick"}
            ]
        }
    }))
]

total_cached_input = 0
total_uncached_input = 0
total_output = 0

print("🚀 Running Claude with Prompt Caching")
for i, (json_input,) in enumerate(test_cases):
    print(f"\n🧪 Test {i+1}: {json_input[:50]}...")

    # First call: instruction is cached
    res = json_to_toon_claude(json_input)
    print(f"  TOON: {res['text'][:60]}...")

    total_cached_input += res["cached_input_tokens"]
    total_uncached_input += res["uncached_input_tokens"]
    total_output += res["output_tokens"]

    time.sleep(1)  # Rate limit

cost = estimate_cost(total_cached_input, total_uncached_input, total_output)
print(f"\n📊 Total tokens → Cached input: {total_cached_input}, Uncached: {total_uncached_input}, Output: {total_output}")
print(f"💰 Estimated cost: ${cost:.6f}")