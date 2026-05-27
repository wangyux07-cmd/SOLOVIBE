#!/bin/bash

# SoloVibe 后端依赖安装脚本 (macOS/Linux)

echo "======================================"
echo "SoloVibe 后端依赖安装脚本"
echo "======================================"
echo

# 检查Python版本
echo "检查Python版本..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3，请安装Python 3.8+ 并添加到PATH"
    echo "下载链接: https://www.python.org/downloads/"
    exit 1
fi

python3 --version
echo

# 检查pip
echo "检查pip包管理器..."
if ! command -v pip3 &> /dev/null; then
    echo "[错误] pip3未安装，请确保pip已正确安装"
    exit 1
fi

echo

# 创建虚拟环境
echo "创建Python虚拟环境..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "[错误] 创建虚拟环境失败"
    exit 1
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "[错误] 激活虚拟环境失败"
    exit 1
fi

echo "当前Python: $(which python)"
echo

# 升级pip
echo "升级pip到最新版本..."
python -m pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "[警告] pip升级失败，继续使用当前版本"
fi

echo

# 安装依赖
echo "安装Python依赖库..."
echo "这可能需要几分钟时间，请耐心等待..."
echo

pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[错误] 依赖安装失败，请检查网络连接和requirements.txt文件"
    exit 1
fi

echo
echo "======================================"
echo "✓ 依赖安装完成！"
echo "======================================"
echo
echo "接下来你需要:"
echo " 1. 复制 .env.example 为 .env 并填写API密钥:"
echo "     cp .env.example .env"
echo "     echo '编辑.env文件填写你的API密钥'"
echo
echo " 2. 运行配置检查:"
echo "     python setup_env.py"
echo
echo " 3. 启动后端服务:"
echo "     python main.py"
echo
echo "📋 详细配置指南: ENVIRONMENT_SETUP.md"
echo "======================================"
echo