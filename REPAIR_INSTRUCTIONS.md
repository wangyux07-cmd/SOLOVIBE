# SOLOVIBE 前端项目修复指南

## 项目背景
您的项目在 Vercel 部署时遇到 `Command "npm install && vite build" exited with 126` 错误，原因是根目录 `package.json` 文件严重残缺，缺少核心配置。

## 已修复内容
1. **根目录 package.json**：已补全标准配置，包含必要的 scripts 字段
2. **frontend/package.json**：已优化 scripts 配置，适配 Vite 6.x 和 Windows PowerShell

## 系统要求
- **Node.js 版本**: >= 20.19.0 (Vite 6.0.0 要求)
- **包管理器**: npm (推荐) 或 yarn

## PowerShell 修复命令

### 1. 清理本地环境
```powershell
# 切换到项目根目录
cd D:\SOLOVIBE

# 强力清理 frontend 的依赖和构建产物
Remove-Item -Recurse -Force frontend\node_modules -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force frontend\dist -ErrorAction SilentlyContinue
Remove-Item frontend\package-lock.json -ErrorAction SilentlyContinue
Remove-Item frontend\.npmrc -ErrorAction SilentlyContinue

# 强力清理根目录的依赖
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
Remove-Item package-lock.json -ErrorAction SilentlyContinue
```

### 2. 验证 Node.js 版本
```powershell
# 检查 Node.js 版本
node --version
# 应该输出 v20.19.x 或更高版本

# 如果版本过低，请升级 Node.js 到 20.19.0+ 或 22.12.0+
```

### 3. 重新安装依赖
```powershell
# 先安装根目录依赖
npm install --legacy-peer-deps

# 再安装 frontend 依赖
cd frontend
npm install --legacy-peer-deps
cd ..
```

### 4. 本地构建测试
```powershell
# 测试开发服务器
npm run dev

# 在另一个终端窗口测试构建
npm run build

# 测试预览
npm run preview
```

### 5. Vercel 部署配置
在 Vercel 项目设置中配置：
- **Framework Preset**: Vite
- **Build Command**: `npm run build`
- **Output Directory**: `frontend/dist`
- **Install Command**: `npm install --legacy-peer-deps`
- **Root Directory**: `/`

## 常见问题解决

### Node.js 版本不兼容
如果遇到版本错误，请升级 Node.js：
```powershell
# 使用 nvm-windows (推荐)
nvm install 20.19.0
nvm use 20.19.0

# 或者下载安装最新版 Node.js
```

### 权限问题
如果在 Windows 上遇到权限问题：
```powershell
# 以管理员身份运行 PowerShell
# 或者尝试清除 npm 缓存
npm cache clean --force
```

### 构建失败
如果构建失败，尝试：
```powershell
# 清理并重新安装
npm run clean
rmdir /s /q node_modules
npm install --legacy-peer-deps --force
```

## 项目结构说明
```
SOLOVIBE/
├── package.json              # 根目录配置，统一管理前后端
├── frontend/
│   ├── package.json          # 前端专用配置
│   ├── src/                  # React + TypeScript 源码
│   ├── dist/                 # 构建输出目录
│   └── vite.config.ts        # Vite 配置
└── backend/                  # Python 后端代码
```

## 验证修复成功
1. 开发服务器能正常启动 `npm run dev`
2. 构建命令能成功执行 `npm run build`
3. 生成 dist 目录且包含 index.html 和 assets
4. Vercel 部署不再报错

如有任何问题，请检查错误日志并提供详细信息以便进一步诊断。