#!/usr/bin/env python3
import requests
import json

def test():
    url = "http://localhost:8000/api/chat"

    # Step 1: Send message
    print("Step 1: Send feeling")
    res1 = requests.post(url, json={"message": "心情不好 想喝酒"}, timeout=30)
    print(f"Status: {res1.status_code}")
    print(f"Response snippet: {str(res1.json())[:300]}")

    tid = res1.json().get("thread_id")
    print(f"Thread ID: {tid}\n")

    # Step 2: Send address
    print("Step 2: Send address 上海大学站")
    res2 = requests.post(url, json={
        "message": "上海大学站",
        "thread_id": tid
    }, timeout=30)
    print(f"Status: {res2.status_code}")

    result = res2.json()
    print(f"Response: {json.dumps(result, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    test()
