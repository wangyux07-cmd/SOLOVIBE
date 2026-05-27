@echo off
echo 🚀 启动SoloVibe后端服务...

REM 检查Python环境
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python未安装，请先安装Python3.10+版本
    pause
    exit /b 1
)

REM 安装依赖
echo 📦 安装Python依赖...
pip install -r requirements.txt

REM 检查环境变量
if not exist ".env" (
    echo ⚠️  .env文件不存在，使用环境变量示例
    copy .env.example .env
    echo 请编辑.env文件配置您的Supabase连接信息
)

REM 启动服务
echo 🌟 启动FastAPI服务...
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
