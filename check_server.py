import requests
try:
    r = requests.get("http://127.0.0.1:8000", timeout=2)
    print(f"Server响应: {r.status_code}")
except Exception as e:
    print(f"连接失败: {e}")