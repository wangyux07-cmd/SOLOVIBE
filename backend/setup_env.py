#!/usr/bin/env python3
"""
环境变量配置助手 - 帮助学生快速设置SoloVibe后端环境
"""

import os
import sys
from pathlib import Path

def print_colored(text, color_code):
    """打印彩色文本"""
    print(f"\033[{color_code}m{text}\033[0m")

def print_step(step_num, title):
    """打印步骤标题"""
    print_colored(f"\n📋 步骤 {step_num}: {title}", "1;36m")

def print_success(text):
    """打印成功信息"""
    print_colored(f"✅ {text}", "1;32m")

def print_warning(text):
    """打印警告信息"""
    print_colored(f"⚠️  {text}", "1;33m")

def print_error(text):
    """打印错误信息"""
    print_colored(f"❌ {text}", "1;31m")

def print_info(text):
    """打印信息"""
    print_colored(f"ℹ️  {text}", "1;34m")

def check_or_create_env_file():
    """检查或创建.env文件"""
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    if env_path.exists():
        print_success(".env文件已存在")
        return True
    
    if not example_path.exists():
        print_error("找不到.env.example模板文件")
        return False
    
    print_warning(".env文件不存在，正在从模板创建...")
    try:
        env_path.write_text(example_path.read_text())
        print_success("已创建.env文件，请编辑填写您的密钥")
        return False  # 刚创建的文件还需要配置
    except Exception as e:
        print_error(f"创建.env文件失败: {e}")
        return False

def validate_env_variables():
    """验证环境变量完整性"""
    print_step(2, "验证环境变量配置")
    
    required_basic_vars = [
        'SUPABASE_URL',
        'SUPABASE_KEY'
    ]
    
    # 至少需要一个搜索API
    search_api_vars = [
        'TAVILY_API_KEY',
        'SERPER_API_KEY'
    ]
    
    missing_basic = []
    for var in required_basic_vars:
        if not os.getenv(var) or os.getenv(var).startswith('your-'):
            missing_basic.append(var)
    
    has_search_api = any(
        os.getenv(var) and not os.getenv(var).startswith('your-') 
        for var in search_api_vars
    )
    
    if missing_basic:
        print_error("以下基础配置缺失或需要更新:")
        for var in missing_basic:
            print(f"   • {var}: {os.getenv(var, '未设置')}")
        
        print_warning("请先配置Supabase数据库连接")
        print_info("📚 配置指南: https://supabase.com/docs/guides/with-python")
    
    if not has_search_api:
        print_warning("未配置Web搜索API")
        print_info("💡 建议配置Tavily API (https://tavily.com)")
        print_info("💡 或使用Serper API (https://serper.dev)")
    
    if not missing_basic and has_search_api:
        print_success("基础环境变量配置完整！")
        return True
    
    return False

def check_gitignore():
    """检查.gitignore是否包含敏感文件"""
    print_step(3, "检查Git安全配置")
    
    gitignore_path = Path(".gitignore")
    if not gitignore_path.exists():
        print_warning(".gitignore文件不存在")
        return
    
    content = gitignore_path.read_text()
    if ".env" in content:
        print_success(".gitignore已正确配置，.env文件不会被提交")
    else:
        print_warning(".env文件可能被提交到Git")
        print_info("建议添加以下内容到.gitignore:")
        print("   .env")
        print("   *.key")
        print("   *.pem")

def suggest_api_setup():
    """提供API设置建议"""
    print_step(4, "API快速设置建议")
    
    print_info("🎯 新架构要求 - 职能分离")
    print("   • Tavily: 专用于情感疗愈内容检索")
    print("   • 高德: 专用于POI搜索+路径规划")
    print("")
    
    print_info("优先推荐方案 (免费额度充足):")
    print("\n   🌐  Tavily API (情感内容专用):")
    print("      1. 访问 https://tavily.com")
    print("      2. 用邮箱注册")
    print("      3. 在Dashboard获取API Key")
    print("      4. 复制到.env文件的 TAVILY_API_KEY")
    
    print("\n   🗺️  高德地图API (地理服务统一平台):")
    print("      1. 访问 https://lbs.amap.com")
    print("      2. 注册账号")
    print("      3. 创建应用获取Key")
    print("      4. 复制到.env文件的 AMAP_API_KEY")
    print("      📋 注意: 每天50000次免费额度，需实名认证")
    
    print("\n⚠️  已移除的API服务:")
    print("   • 美团API (餐厅预订) - 已迁移到高德POI搜索")
    print("   • 滴滴API (打车出行) - 已迁移到高德路径规划")
    
    print("\n💡 开发阶段可以使用 MOCK_EXTERNAL_APIS=true 避免API调用")

def show_next_steps():
    """显示后续步骤"""
    print_step(5, "后续步骤")
    
    print("\n📝 接下来你需要:")
    print("\n   1. 编辑.env文件，填入真实的API密钥")
    print("      nano .env  # 或使用你的编辑器")
    
    print("\n   2. 安装依赖库:")
    print("      cd backend")
    print("      pip install -r requirements.txt")
    
    print("\n   3. 验证配置:")
    print("      python setup_env.py")
    
    print("\n   4. 启动后端服务:")
    print("      python main.py")
    
    print("\n🎉 完成！访问 http://localhost:8000/docs 查看API文档")

def main():
    """主函数"""
    print_colored("🚀 SoloVibe 后端环境配置助手", "1;35m")
    print("=" * 50)
    
    print_info("本工具将帮助你快速配置SoloVibe后端环境")
    print_info("请确保当前目录是 backend/ 文件夹")
    
    current_dir = Path.cwd()
    if current_dir.name != "backend":
        print_warning(f"当前目录: {current_dir}")
        print_warning("建议在 backend/ 目录下运行此脚本")
        if input("是否继续? (y/N): ").lower() != 'y':
            return
    
    # 步骤1: 检查.env文件
    print_step(1, "检查环境配置文件")
    env_ready = check_or_create_env_file()
    
    # 检查gitignore
    check_gitignore()
    
    # 步骤2: 验证环境变量
    config_valid = validate_env_variables() 
    
    # 步骤3: 提供设置建议
    suggest_api_setup()
    
    # 步骤4: 显示后续步骤
    show_next_steps()
    
    print("\n" + "=" * 50)
    if config_valid:
        print_success("✅ 环境配置检查完成，可以直接启动应用！")
    else:
        print_warning("⚠️  需要完善配置才能正常运行")
        print_info("📖 详细配置指南: ENVIRONMENT_SETUP.md")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        print_error(f"程序执行错误: {e}")
        sys.exit(1)