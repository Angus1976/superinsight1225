# Oracle 数据库支持配置指南

SuperInsight 平台支持 Oracle 数据库作为数据源之一。本文档说明如何配置 Oracle 支持。

## 前提条件

Oracle 数据库连接需要 Oracle Instant Client 库。由于许可和大小原因，这些库不包含在默认安装中。

## 本地开发环境配置

### 1. 下载 Oracle Instant Client

访问 Oracle 官方网站下载适合您系统的 Instant Client：
https://www.oracle.com/database/technologies/instant-client/downloads.html

推荐下载 **Basic Lite** 版本（约 40-80MB），它包含了基本的连接功能。

### 2. 安装 Instant Client

#### macOS
```bash
# 解压下载的文件
unzip instantclient-basiclite-macos.x64-*.zip

# 移动到标准位置
sudo mv instantclient_* /usr/local/lib/instantclient

# 设置环境变量（添加到 ~/.zshrc 或 ~/.bash_profile）
export ORACLE_HOME=/usr/local/lib/instantclient
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH
export DYLD_LIBRARY_PATH=$ORACLE_HOME:$DYLD_LIBRARY_PATH
```

#### Linux
```bash
# 解压下载的文件
unzip instantclient-basiclite-linux.x64-*.zip

# 移动到标准位置
sudo mv instantclient_* /opt/oracle/instantclient

# 设置环境变量（添加到 ~/.bashrc）
export ORACLE_HOME=/opt/oracle/instantclient
export LD_LIBRARY_PATH=$ORACLE_HOME:$LD_LIBRARY_PATH

# 更新动态链接器缓存
sudo sh -c "echo /opt/oracle/instantclient > /etc/ld.so.conf.d/oracle-instantclient.conf"
sudo ldconfig
```

#### Windows
```powershell
# 解压到 C:\oracle\instantclient
# 添加到系统 PATH 环境变量
setx PATH "%PATH%;C:\oracle\instantclient"
```

### 3. 安装 Python 依赖

```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装 Oracle 支持
pip install -r requirements-oracle.txt
```

### 4. 验证安装

```python
import cx_Oracle

# 测试连接
dsn = cx_Oracle.makedsn('hostname', 1521, service_name='service_name')
connection = cx_Oracle.connect(user='username', password='password', dsn=dsn)
print("Oracle 连接成功！")
connection.close()
```

## Docker 环境配置

### 方法 1：使用预构建的 Oracle Instant Client 镜像

修改 `Dockerfile.dev`：

```dockerfile
FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc g++ libpq-dev curl wget unzip libaio1 \
    && rm -rf /var/lib/apt/lists/*

# 下载并安装 Oracle Instant Client
RUN mkdir -p /opt/oracle && \
    cd /opt/oracle && \
    wget https://download.oracle.com/otn_software/linux/instantclient/2340000/instantclient-basiclite-linux.x64-23.4.0.24.05.zip && \
    unzip instantclient-basiclite-linux.x64-23.4.0.24.05.zip && \
    rm instantclient-basiclite-linux.x64-23.4.0.24.05.zip

# 设置环境变量
ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_23_4:$LD_LIBRARY_PATH
ENV ORACLE_HOME=/opt/oracle/instantclient_23_4

WORKDIR /app

# 复制并安装依赖（包括 Oracle）
COPY requirements.txt requirements-oracle.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -r requirements-oracle.txt

# ... 其余配置
```

### 方法 2：挂载本地 Instant Client

在 `docker-compose.yml` 中添加卷挂载：

```yaml
services:
  superinsight-api:
    # ... 其他配置
    volumes:
      - .:/app
      - /usr/local/lib/instantclient:/opt/oracle/instantclient:ro
    environment:
      - LD_LIBRARY_PATH=/opt/oracle/instantclient
      - ORACLE_HOME=/opt/oracle/instantclient
```

然后在容器内安装 cx-Oracle：

```bash
docker-compose exec superinsight-api pip install cx-Oracle>=8.3.0
```

## 配置数据源

在 `.env` 文件中添加 Oracle 数据源配置：

```env
# Oracle 数据源配置
ORACLE_HOST=your-oracle-host
ORACLE_PORT=1521
ORACLE_SERVICE_NAME=your-service-name
ORACLE_USER=your-username
ORACLE_PASSWORD=your-password

# 或使用完整的连接字符串
ORACLE_DSN=username/password@hostname:1521/service_name
```

## 使用示例

```python
from src.extractors.oracle_extractor import OracleExtractor

# 创建 Oracle 提取器
extractor = OracleExtractor(
    host="your-oracle-host",
    port=1521,
    service_name="your-service-name",
    user="your-username",
    password="your-password"
)

# 提取数据
data = extractor.extract_table("your_table_name")
```

## 故障排除

### 问题 1: "DPI-1047: Cannot locate a 64-bit Oracle Client library"

**原因**: 找不到 Oracle Instant Client 库

**解决方案**:
1. 确认已正确安装 Instant Client
2. 检查环境变量 `LD_LIBRARY_PATH` 或 `DYLD_LIBRARY_PATH` 是否正确设置
3. 在 Linux 上运行 `sudo ldconfig` 更新动态链接器缓存

### 问题 2: "ImportError: No module named 'cx_Oracle'"

**原因**: cx-Oracle 包未安装

**解决方案**:
```bash
pip install cx-Oracle>=8.3.0
```

### 问题 3: Docker 容器中连接失败

**原因**: 容器内缺少 Instant Client 或环境变量未设置

**解决方案**:
1. 确认 Dockerfile 中已添加 Instant Client 安装步骤
2. 检查 docker-compose.yml 中的环境变量配置
3. 重新构建镜像: `docker-compose build superinsight-api`

## 性能优化建议

1. **连接池**: 使用 SQLAlchemy 的连接池功能
2. **批量操作**: 对于大量数据，使用批量插入/更新
3. **索引**: 确保 Oracle 表有适当的索引
4. **分区**: 对于大表，考虑使用 Oracle 分区功能

## 安全注意事项

1. **凭证管理**: 不要在代码中硬编码数据库凭证，使用环境变量或密钥管理服务
2. **只读权限**: 数据提取应使用只读账户
3. **网络隔离**: 在生产环境中，确保数据库网络访问受到适当限制
4. **审计日志**: 启用 Oracle 审计日志以跟踪数据访问

## 参考资源

- [Oracle Instant Client 下载](https://www.oracle.com/database/technologies/instant-client/downloads.html)
- [cx_Oracle 文档](https://cx-oracle.readthedocs.io/)
- [SQLAlchemy Oracle 方言](https://docs.sqlalchemy.org/en/14/dialects/oracle.html)
