#!/bin/bash

echo "🚀 启动SoloVibe后端服务..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装，请先安装Python3.10+版本"
    exit 1
fi

# 安装依赖
echo "📦 安装Python依赖..."
pip install -r requirements.txt

# 检查环境变量
if [ ! -f ".env" ]; then
    echo "⚠️  .env文件不存在，使用环境变量示例"
    cp .env.example .env
    echo "请编辑.env文件配置您的Supabase连接信息"
fi

# 启动服务
echo "🌟 启动FastAPI服务..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
