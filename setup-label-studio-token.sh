#!/bin/bash

# Label Studio API Token 配置脚本
# Label Studio API Token Setup Script

set -e

echo "=========================================="
echo "Label Studio API Token 配置向导"
echo "Label Studio API Token Setup Wizard"
echo "=========================================="
echo ""

# 检查 .env 文件是否存在
if [ ! -f .env ]; then
    echo "❌ 错误: .env 文件不存在"
    echo "❌ Error: .env file not found"
    echo ""
    echo "请先运行: cp .env.example .env"
    echo "Please run: cp .env.example .env"
    exit 1
fi

echo "📋 步骤 1: 访问 Label Studio"
echo "📋 Step 1: Access Label Studio"
echo ""
echo "请在浏览器中打开: http://localhost:8080"
echo "Please open in browser: http://localhost:8080"
echo ""
echo "登录凭据 / Login credentials:"
echo "  Email: admin@example.com"
echo "  Password: admin"
echo ""

# 检查 Label Studio 是否运行
echo "🔍 检查 Label Studio 容器状态..."
echo "🔍 Checking Label Studio container status..."
if /Applications/Docker.app/Contents/Resources/bin/docker compose ps label-studio | grep -q "Up"; then
    echo "✅ Label Studio 容器正在运行"
    echo "✅ Label Studio container is running"
else
    echo "⚠️  Label Studio 容器未运行，正在启动..."
    echo "⚠️  Label Studio container not running, starting..."
    /Applications/Docker.app/Contents/Resources/bin/docker compose up -d label-studio
    echo "⏳ 等待 Label Studio 启动 (10秒)..."
    echo "⏳ Waiting for Label Studio to start (10 seconds)..."
    sleep 10
fi

echo ""
echo "📋 步骤 2: 获取 API Token"
echo "📋 Step 2: Get API Token"
echo ""
echo "在 Label Studio 中:"
echo "In Label Studio:"
echo "  1. 点击右上角头像 / Click profile icon (top right)"
echo "  2. 选择 'Account & Settings'"
echo "  3. 进入 'Access Token' 部分 / Go to 'Access Token' section"
echo "  4. 复制现有 token 或创建新的 / Copy existing token or create new one"
echo ""

# 提示用户输入 token
read -p "请粘贴您的 API Token / Please paste your API Token: " api_token

if [ -z "$api_token" ]; then
    echo ""
    echo "❌ 错误: Token 不能为空"
    echo "❌ Error: Token cannot be empty"
    exit 1
fi

echo ""
echo "📝 步骤 3: 更新 .env 文件"
echo "📝 Step 3: Update .env file"

# 检查 .env 文件中是否已有 LABEL_STUDIO_API_TOKEN
if grep -q "^LABEL_STUDIO_API_TOKEN=" .env; then
    # 更新现有的 token
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|^LABEL_STUDIO_API_TOKEN=.*|LABEL_STUDIO_API_TOKEN=$api_token|" .env
    else
        # Linux
        sed -i "s|^LABEL_STUDIO_API_TOKEN=.*|LABEL_STUDIO_API_TOKEN=$api_token|" .env
    fi
    echo "✅ 已更新 .env 文件中的 API Token"
    echo "✅ Updated API Token in .env file"
else
    # 添加新的 token
    echo "LABEL_STUDIO_API_TOKEN=$api_token" >> .env
    echo "✅ 已添加 API Token 到 .env 文件"
    echo "✅ Added API Token to .env file"
fi

echo ""
echo "📋 步骤 4: 重启后端容器"
echo "📋 Step 4: Restart backend container"
echo ""

/Applications/Docker.app/Contents/Resources/bin/docker compose restart app

echo ""
echo "⏳ 等待容器重启 (5秒)..."
echo "⏳ Waiting for container restart (5 seconds)..."
sleep 5

echo ""
echo "📋 步骤 5: 验证配置"
echo "📋 Step 5: Verify configuration"
echo ""

# 检查环境变量是否设置
if /Applications/Docker.app/Contents/Resources/bin/docker compose exec app printenv | grep -q "LABEL_STUDIO_API_TOKEN=$api_token"; then
    echo "✅ API Token 已成功配置"
    echo "✅ API Token configured successfully"
else
    echo "⚠️  警告: 无法验证 API Token 配置"
    echo "⚠️  Warning: Could not verify API Token configuration"
fi

echo ""
echo "=========================================="
echo "✅ 配置完成！"
echo "✅ Configuration Complete!"
echo "=========================================="
echo ""
echo "现在您可以使用以下功能:"
echo "Now you can use the following features:"
echo "  • 开始标注 (Start Annotation) 按钮"
echo "  • 在新窗口中打开 (Open in New Window) 按钮"
echo ""
echo "如需测试连接，请运行:"
echo "To test the connection, run:"
echo "  /Applications/Docker.app/Contents/Resources/bin/docker compose exec app python3 -c \\"
echo "    \"from src.label_studio.integration import LabelStudioIntegration; \\"
echo "    import asyncio; \\"
echo "    asyncio.run(LabelStudioIntegration().test_connection())\""
echo ""
