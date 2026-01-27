# 下一步操作清单

**当前状态**: ✅ 配置已更新，准备重启验证

---

## 🚀 立即执行（3 个命令）

### 1️⃣ 重启后端容器

```bash
docker compose restart app
```

**预期输出**:
```
[+] Restarting 1/1
 ✔ Container superinsight-app  Started
```

**等待时间**: 10-30 秒

---

### 2️⃣ 验证配置

```bash
./VERIFY_FIX.sh
```

**预期输出**:
```
✓ JWT 配置已正确注释
✓ API Token 已配置
✓ 后端容器正在运行
✓ Label Studio 可访问
✓ API Token 认证成功
```

**如果出现错误**: 查看脚本输出的具体错误信息和建议

---

### 3️⃣ 测试标注按钮

**打开浏览器**:
```
http://localhost:5173
```

**测试步骤**:
1. 进入任务列表页面
2. 点击任意任务进入详情页
3. 点击 **"开始标注"** 按钮
   - ✅ 应该跳转到标注页面
   - ✅ 应该显示 Label Studio iframe
4. 点击 **"在新窗口打开"** 按钮
   - ✅ 应该在新窗口打开 Label Studio
   - ✅ 应该显示正确的语言（中文/英文）

---

## 📋 验证清单

完成以下所有项目：

- [ ] 后端容器已重启
- [ ] 验证脚本全部通过
- [ ] "开始标注" 按钮正常工作
- [ ] "在新窗口打开" 按钮正常工作
- [ ] 语言切换功能正常
- [ ] 没有 401/404 错误

---

## 🔍 如果遇到问题

### 问题 1: 验证脚本失败

**查看详细日志**:
```bash
docker compose logs app | grep -i "label studio"
```

**常见错误**:
- `401 Unauthorized` → Token 无效，需要重新生成
- `404 Not Found` → Label Studio 未运行
- `Connection refused` → 服务未启动

### 问题 2: 按钮仍然不工作

**检查步骤**:
```bash
# 1. 确认 .env 已更新
cat .env | grep LABEL_STUDIO_API_TOKEN

# 2. 确认容器已重启
docker compose ps | grep app

# 3. 查看后端日志
docker compose logs app --tail=50

# 4. 测试 API
curl http://localhost:8000/health
```

### 问题 3: Token 认证失败

**重新生成 Token**:
1. 访问 http://localhost:8080
2. 登录: admin@example.com / admin
3. Account & Settings → Legacy Tokens
4. 生成新 Token
5. 更新 .env 文件:
   ```bash
   LABEL_STUDIO_API_TOKEN=<新Token>
   ```
6. 重启后端:
   ```bash
   docker compose restart app
   ```

---

## 📚 参考文档

| 文档 | 用途 |
|------|------|
| `QUICK_FIX_REFERENCE.md` | 快速参考卡 |
| `FIX_ANNOTATION_BUTTONS_GUIDE.md` | 详细操作指南 |
| `FIX_COMPLETED_REPORT.md` | 修复完成报告 |
| `LABEL_STUDIO_AUTH_SOLUTION.md` | 技术分析 |
| `LABEL_STUDIO_AUTH_FLOW.md` | 认证流程图 |
| `VERIFY_FIX.sh` | 验证脚本 |

---

## ⏱️ 预计时间

- **重启容器**: 30 秒
- **运行验证**: 1 分钟
- **测试按钮**: 2 分钟
- **总计**: 约 5 分钟

---

## ✅ 成功标准

修复成功的标志：

1. ✅ 验证脚本全部通过
2. ✅ 后端日志显示: `Using api_token authentication`
3. ✅ 标注按钮可以点击并正常工作
4. ✅ 没有认证错误（401/404）
5. ✅ Label Studio 可以正常打开

---

## 🎯 开始执行

**准备好了吗？** 复制并执行以下命令：

```bash
# 步骤 1: 重启后端
docker compose restart app

# 步骤 2: 等待 10 秒让容器完全启动
sleep 10

# 步骤 3: 验证配置
./VERIFY_FIX.sh

# 步骤 4: 打开浏览器测试
echo "请打开浏览器访问: http://localhost:5173"
echo "测试标注按钮功能"
```

---

**祝你修复顺利！** 🚀

如果遇到任何问题，请查看 `FIX_ANNOTATION_BUTTONS_GUIDE.md` 中的故障排查部分。
