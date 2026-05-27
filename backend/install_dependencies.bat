@echo off

echo ======================================
echo  SoloVibe 后端依赖安装脚本
echo ======================================
echo.

:: 检查Python版本
echo 检查Python版本...
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到Python，请安装Python 3.8+ 并添加到PATH
    echo 下载链接: https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo.

:: 检查pip
echo 检查pip包管理器...
pip --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] pip未安装，请确保pip已正确安装
    pause
    exit /b 1
)

echo.

:: 创建并激活虚拟环境
echo 创建Python虚拟环境...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 创建虚拟环境失败
    pause
    exit /b 1
)

echo 激活虚拟环境...
call venv\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 激活虚拟环境失败
    pause
    exit /b 1
)

echo.

:: 升级pip
echo 升级pip到最新版本...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo [警告] pip升级失败，继续使用当前版本
)

echo.

:: 安装依赖
echo 安装Python依赖库...
echo 这可能需要几分钟时间，请耐心等待...
echo.

pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 依赖安装失败，请检查网络连接和requirements.txt文件
    pause
    exit /b 1
)

echo.
echo ======================================
echo ✓ 依赖安装完成！
echo ======================================
echo.
echo 接下来你需要:
echo  1. 复制 .env.example 为 .env 并填写API密钥:
     copy .env.example .env
     echo 编辑.env文件填写你的API密钥

echo  2. 运行配置检查:
     python setup_env.py

echo  3. 启动后端服务:
     python main.py

echo.
echo 📋 详细配置指南: ENVIRONMENT_SETUP.md
echo ======================================
echo.
pause