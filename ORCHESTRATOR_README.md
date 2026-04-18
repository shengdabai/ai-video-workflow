# 视频编排系统快速启动

## 环境变量

```bash
export PIXVERSE_API_KEY="your-pixverse-api-key"
export ORCHESTRATOR_DB_PATH="orchestrator.db"   # 默认值
```

## 首次 YouTube 授权

将 Google Cloud OAuth2 client secrets 下载到：
`~/.config/pixelle/youtube_client_secrets.json`

首次发布时会自动打开浏览器完成授权，token 保存在：
`~/.config/pixelle/youtube_token.pickle`

## 启动

```bash
# 终端 1：FastAPI
uvicorn api.app:app --reload --port 8000

# 终端 2：Queue Worker
python -m orchestrator.worker

# 终端 3：Dashboard
cd dashboard && npm run dev
```

访问 http://localhost:3000

## 运行测试

```bash
python -m pytest tests/orchestrator/ tests/api/ -v
```

## 三阶段路线图

### 第一阶段（当前）
- Task Queue：视频任务 → 镜头任务，状态管理
- Assets：所有产出物独立管理
- Providers：PixVerse 官方 API（可扩展）
- Review：两级审核（视频级 + 镜头级）
- Publish：审核后半自动发布 YouTube

### 第二阶段（计划）
- 集成 MoneyPrinterTurbo 参数面板
- Web UI 参考体验优化

### 第三阶段（计划）
- 抖音/快手/B站多平台发布
- 标题/封面/描述模板
- 发布数据回流 → 下一轮选题
