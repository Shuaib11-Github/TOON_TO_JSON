import os
from dotenv import load_dotenv
import requests

load_dotenv()

API_KEY = os.getenv("EURI_API_KEY")

def generate_completion():
    url = "https://api.euron.one/api/v1/euri/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "messages": [
            {
                "role": "user",
                "content": "Write a poem about artificial intelligence"
            }
        ],
        "model": "gpt-4.1-nano",
        "max_tokens": 1000,
        "temperature": 0.7
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()
    print(data)
    print(data['choices'][0]['message']['content'])

generate_completion()