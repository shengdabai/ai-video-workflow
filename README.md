# 🎬 AI Video Workflow

<p align="center"><b>English</b> | <a href="#中文">中文</a></p>

<p align="center">
  <a href="https://github.com/shengdabai/ai-video-workflow/commits/main"><img src="https://img.shields.io/github/last-commit/shengdabai/ai-video-workflow?color=blue" alt="Last commit"></a>
  <a href="https://github.com/shengdabai/ai-video-workflow/stargazers"><img src="https://img.shields.io/github/stars/shengdabai/ai-video-workflow?style=social" alt="Stars"></a>
  <a href="https://github.com/shengdabai"><img src="https://img.shields.io/github/followers/shengdabai?label=Follow%20%40shengdabai&style=social" alt="Follow"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/shengdabai/ai-video-workflow?color=green" alt="License"></a>
</p>

> **Turn one topic into a published video — script, shots, review, and YouTube upload, on autopilot.**

An end-to-end AI video automation system that orchestrates the full pipeline: **script → shot generation → human review → YouTube publish**. It wraps an AI-driven video generator with a durable task queue, two-level review gates, and a one-click publisher — so a single topic becomes a finished, reviewed, uploaded video.

## 💡 Why

Generating one AI clip is easy. Running a *repeatable production line* — many shots per video, retries on failure, a human checkpoint before anything goes public, and a hands-off upload — is the hard part. This project is the orchestration layer that makes AI video creation reliable and unattended, built and run in public by a Chinese-language teacher who needs to ship educational video at volume.

## ✨ What it does

A topic enters one end; a reviewed, published video comes out the other. Each stage is a real, code-backed component:

- **📝 Script & shot planning** — a topic/script is turned into ordered shot tasks, each with its own prompt, duration, and aspect ratio.
- **🎨 Shot generation** — shots are generated through a pluggable provider interface (PixVerse API today), plus the Pixelle-Video engine for AI image/video, TTS narration, and background music.
- **✅ Two-level review** — a human approves at both the **video** level and the individual **shot** level; rejected shots can be re-prompted and regenerated without restarting the job.
- **🎬 Compose** — approved clips are stitched with `ffmpeg` and optional BGM into a final cut.
- **🚀 YouTube publish** — the final video is uploaded via the YouTube Data API with OAuth2 (title, description, tags, privacy, thumbnail).

## 🧱 Pipeline & architecture

```
topic / script
      │
      ▼
┌────────────────┐   FastAPI + SQLite task queue (VideoTask → ShotTask → Asset)
│  Orchestrator  │   • durable state machine  • concurrency cap  • auto-retry
└────────────────┘
      │
      ▼
┌────────────────┐   pluggable VideoProvider (PixVerse) + Pixelle-Video engine
│ Shot generation│   • AI image/video  • TTS  • BGM
└────────────────┘
      │
      ▼
┌────────────────┐   two-level review gate (video + shot)
│     Review     │   • approve / reject / re-prompt  • asset replacement
└────────────────┘
      │
      ▼
┌────────────────┐   ffmpeg compose → YouTube Data API (OAuth2)
│Compose & Publish│
└────────────────┘
```

- **Worker loop** (`orchestrator/worker.py`): polls pending shots, submits to the provider (max 3 concurrent), downloads finished clips, retries up to 3× on failure, and moves shots into `review_pending`.
- **State machine**: `pending → generating → review_pending → approved → published` (with `failed` / `rejected` branches).
- **Assets**: every artifact (clip, image, audio, subtitle, cover, export) is tracked independently in SQLite.

## 🛠️ Tech stack

| Layer | Stack |
|------|-------|
| Backend / API | Python 3.11+, FastAPI, Uvicorn, Pydantic |
| Orchestration | Async worker, SQLite (`aiosqlite`), httpx |
| Generation | PixVerse API, ComfyUI / RunningHub workflows, `edge-tts`, OpenAI-compatible LLM |
| Media | `ffmpeg` / `moviepy`, Pillow |
| Web UIs | Streamlit (Pixelle-Video) + Next.js / TypeScript dashboard |
| Publishing | YouTube Data API (`google-api-python-client`, OAuth2) |
| Ops | Docker / docker-compose, pytest |

## 🚀 Quick start

> Requires Python 3.11+, `ffmpeg`, and Node.js (for the dashboard).

```bash
git clone https://github.com/shengdabai/ai-video-workflow.git
cd ai-video-workflow

# 1. Install (pip or uv)
python -m venv .venv && source .venv/bin/activate
pip install -e .            # or: uv sync

# 2. Configure secrets (placeholders only — never commit real keys)
cp .env.example .env
#   PIXVERSE_API_KEY=your-pixverse-api-key-here
#   YOUTUBE_CLIENT_SECRET=your-youtube-client-secret-here
#   ORCHESTRATOR_DB_PATH=orchestrator.db
cp config.example.yaml config.yaml     # set LLM / ComfyUI options

# 3. Run the three processes
uvicorn api.app:app --reload --port 8000   # terminal 1: API
python -m orchestrator.worker              # terminal 2: queue worker
cd dashboard && npm install && npm run dev # terminal 3: dashboard
```

Open **http://localhost:3000** for the dashboard (API docs at **http://localhost:8000/docs**).

**First YouTube authorization:** place your Google Cloud OAuth2 client secrets at `~/.config/pixelle/youtube_client_secrets.json`. The first publish opens a browser to authorize; the token is cached at `~/.config/pixelle/youtube_token.pickle`.

```bash
# Run tests
python -m pytest tests/orchestrator/ tests/api/ -v
```

## 📖 How the pipeline works

1. **Create a video task** — POST a title + script to `/orchestrator`; it becomes a `VideoTask`.
2. **Generate shots** — shots are enqueued as `ShotTask`s and picked up by the worker, which submits them to the provider and downloads finished clips.
3. **Review** — approve the video and/or individual shots in the dashboard; reject + re-prompt any shot to regenerate it.
4. **Compose** — approved clips are concatenated (with optional BGM) into the final export.
5. **Publish** — the composed video is uploaded to YouTube and recorded as a `PublishRecord`.

## 🗺️ Status

Actively developed and run in public. **Phase 1 (current):** task queue, asset management, PixVerse provider, two-level review, semi-automatic YouTube publish. **Roadmap:** richer generation parameter panels, multi-platform publishing (Douyin / Kuaishou / Bilibili), and publish-analytics feeding the next round of topic selection. Provider and platform interfaces are intentionally pluggable.

This project builds an orchestration + dashboard layer on top of, and is inspired by, the open-source [Pixelle-Video](https://github.com/AIDC-AI/Pixelle-Video) generation engine.

## 🤝 Connect & about

Built by **[@shengdabai](https://github.com/shengdabai)** — a Chinese-language teacher (6000+ students) building AI + Chinese-teaching tools in public.

If this is useful, please **⭐ star the repo** and **follow [@shengdabai](https://github.com/shengdabai)** to follow along.

Related projects:
- **[content-creator-hub](https://github.com/shengdabai/content-creator-hub)** — content creation tooling
- **[ai-video-generator](https://github.com/shengdabai/ai-video-generator)** — AI video generation
- **[chinese-teaching-video-system](https://github.com/shengdabai/chinese-teaching-video-system)** — Chinese-teaching video system

## License

Apache-2.0 — see [LICENSE](LICENSE).

---

<a name="中文"></a>

# 🎬 AI Video Workflow

<p align="center"><a href="#-ai-video-workflow">English</a> | <b>中文</b></p>

> **一个主题，自动产出一条已发布的视频 —— 文案、分镜、审核、YouTube 上传全程托管。**

端到端的 AI 视频自动化编排系统，串起完整流水线：**脚本 → 分镜生成 → 人工审核 → YouTube 发布**。它在 AI 视频生成引擎之上，叠加了一个可恢复的任务队列、双层审核闸门与一键发布器 —— 让一个主题变成一条已审核、已上传的成品视频。

## 💡 为什么做这个

生成单条 AI 片段很容易；难的是跑一条**可复用的生产线** —— 一条视频多个分镜、失败自动重试、公开前有人工卡点、上传无人值守。本项目就是让 AI 视频创作变得可靠、可托管的编排层，由一位需要批量产出教学视频的中文老师在公开构建。

## ✨ 它能做什么

主题从一端进入，审核并发布后的视频从另一端产出。每个阶段都有真实的代码组件支撑：

- **📝 文案与分镜规划** —— 把主题/脚本拆成有序的分镜任务，每个分镜带自己的提示词、时长与画幅。
- **🎨 分镜生成** —— 通过可插拔的 Provider 接口生成（当前为 PixVerse API），并结合 Pixelle-Video 引擎完成 AI 配图/视频、TTS 语音解说与背景音乐。
- **✅ 双层审核** —— 人工在**视频级**与单个**分镜级**两层审批；被拒绝的分镜可重写提示词并重新生成，无需重启整个任务。
- **🎬 合成** —— 审核通过的片段用 `ffmpeg` 拼接，可叠加 BGM，输出成片。
- **🚀 YouTube 发布** —— 成片经 YouTube Data API + OAuth2 上传（标题、描述、标签、隐私、封面）。

## 🧱 流水线与架构

```
主题 / 脚本
      │
      ▼
┌────────────────┐   FastAPI + SQLite 任务队列（VideoTask → ShotTask → Asset）
│    编排层      │   • 可恢复状态机  • 并发上限  • 自动重试
└────────────────┘
      │
      ▼
┌────────────────┐   可插拔 VideoProvider（PixVerse）+ Pixelle-Video 引擎
│   分镜生成     │   • AI 配图/视频  • TTS  • BGM
└────────────────┘
      │
      ▼
┌────────────────┐   双层审核闸门（视频级 + 分镜级）
│     审核       │   • 通过 / 拒绝 / 重写提示词  • 素材替换
└────────────────┘
      │
      ▼
┌────────────────┐   ffmpeg 合成 → YouTube Data API（OAuth2）
│   合成与发布   │
└────────────────┘
```

- **Worker 循环**（`orchestrator/worker.py`）：轮询待处理分镜，提交给 Provider（最多 3 并发），下载完成片段，失败最多重试 3 次，并把分镜推入 `review_pending`。
- **状态机**：`pending → generating → review_pending → approved → published`（含 `failed` / `rejected` 分支）。
- **素材管理**：所有产出物（片段、图片、音频、字幕、封面、导出文件）在 SQLite 中独立追踪。

## 🛠️ 技术栈

| 层 | 技术 |
|------|-------|
| 后端 / API | Python 3.11+、FastAPI、Uvicorn、Pydantic |
| 编排 | 异步 Worker、SQLite（`aiosqlite`）、httpx |
| 生成 | PixVerse API、ComfyUI / RunningHub 工作流、`edge-tts`、OpenAI 兼容 LLM |
| 媒体 | `ffmpeg` / `moviepy`、Pillow |
| Web 界面 | Streamlit（Pixelle-Video）+ Next.js / TypeScript 控制台 |
| 发布 | YouTube Data API（`google-api-python-client`、OAuth2） |
| 运维 | Docker / docker-compose、pytest |

## 🚀 快速开始

> 需要 Python 3.11+、`ffmpeg`，以及 Node.js（控制台用）。

```bash
git clone https://github.com/shengdabai/ai-video-workflow.git
cd ai-video-workflow

# 1. 安装（pip 或 uv）
python -m venv .venv && source .venv/bin/activate
pip install -e .            # 或：uv sync

# 2. 配置密钥（仅占位符 —— 切勿提交真实 key）
cp .env.example .env
#   PIXVERSE_API_KEY=your-pixverse-api-key-here
#   YOUTUBE_CLIENT_SECRET=your-youtube-client-secret-here
#   ORCHESTRATOR_DB_PATH=orchestrator.db
cp config.example.yaml config.yaml     # 设置 LLM / ComfyUI 选项

# 3. 启动三个进程
uvicorn api.app:app --reload --port 8000   # 终端 1：API
python -m orchestrator.worker              # 终端 2：队列 Worker
cd dashboard && npm install && npm run dev # 终端 3：控制台
```

打开 **http://localhost:3000** 进入控制台（API 文档在 **http://localhost:8000/docs**）。

**首次 YouTube 授权：** 把 Google Cloud OAuth2 client secrets 放到 `~/.config/pixelle/youtube_client_secrets.json`。首次发布会打开浏览器完成授权，token 缓存在 `~/.config/pixelle/youtube_token.pickle`。

```bash
# 运行测试
python -m pytest tests/orchestrator/ tests/api/ -v
```

## 📖 流水线如何运转

1. **创建视频任务** —— 向 `/orchestrator` 提交标题 + 脚本，生成一个 `VideoTask`。
2. **生成分镜** —— 分镜作为 `ShotTask` 入队，Worker 取出并提交给 Provider，下载完成片段。
3. **审核** —— 在控制台审批视频和/或单个分镜；拒绝并重写提示词可重新生成任意分镜。
4. **合成** —— 审核通过的片段拼接（可选 BGM）为最终导出。
5. **发布** —— 成片上传 YouTube，并记录为一条 `PublishRecord`。

## 🗺️ 状态

公开持续开发中。**第一阶段（当前）：** 任务队列、素材管理、PixVerse Provider、双层审核、半自动 YouTube 发布。**路线图：** 更丰富的生成参数面板、多平台发布（抖音 / 快手 / B 站）、发布数据回流以驱动下一轮选题。Provider 与平台接口均有意做成可插拔。

本项目在开源生成引擎 [Pixelle-Video](https://github.com/AIDC-AI/Pixelle-Video) 之上构建编排层与控制台，并受其启发。

## 🤝 关于与联系

由 **[@shengdabai](https://github.com/shengdabai)** 构建 —— 一位中文老师（6000+ 学员），在公开构建 AI + 中文教学工具。

如果对你有用，欢迎 **⭐ Star 本仓库** 并 **关注 [@shengdabai](https://github.com/shengdabai)**。

相关项目：
- **[content-creator-hub](https://github.com/shengdabai/content-creator-hub)** —— 内容创作工具集
- **[ai-video-generator](https://github.com/shengdabai/ai-video-generator)** —— AI 视频生成
- **[chinese-teaching-video-system](https://github.com/shengdabai/chinese-teaching-video-system)** —— 中文教学视频系统

## 许可证

Apache-2.0 —— 见 [LICENSE](LICENSE)。
