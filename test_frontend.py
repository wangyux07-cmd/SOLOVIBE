import requests
import json

def test_frontend():
    print("\n🌐 测试前端服务状态...")
    
    # 测试前端主要端口
    ports = [3000, 3001, 5173, 5174]  # Vite常见的端口
    
    for port in ports:
        try:
            print(f"\n   测试端口 {port}...")
            response = requests.get(f'http://localhost:{port}', timeout=3)
            print(f"   ✅ 端口 {port}: {response.status_code}")
            return port
        except Exception as e:
            print(f"   ❌ 端口 {port}: {e}")
            continue
    
    print("\n❌ 前端服务未在常见端口上运行")
    return None

def test_frontend_api_proxy():
    print("\n🔗 测试前端API代理...")
    
    # 测试Vite代理设置
    frontend_port = test_frontend()
    if frontend_port:
        try:
            response = requests.get(f'http://localhost:{frontend_port}/api/health', timeout=5)
            print(f"   ✅ 前端API代理: {response.status_code}")
        except Exception as e:
            print(f"   ⚠️  前端API代理未配置或错误: {e}")

if __name__ == '__main__':
    test_frontend_api_proxy()