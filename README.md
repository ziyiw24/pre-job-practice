# 上岗练

上岗练是面向现制饮品门店的 AI 培训验证小程序。店长粘贴自有 SOP、食安要求或服务标准，系统将其转换为有原文依据的岗位练习，并根据答题结果生成复训建议。

项目维护者：[ziyiw24](https://github.com/ziyiw24)

> AI 生成内容需管理者确认，以门店最新正式制度为准。在线结果不等同于实操上岗认证。

## 已实现

- 店长与员工身份分流：店长生成和管理题库，员工直接进入分配的答题任务

- 匿名粘贴 500～8000 字培训内容，生成 3 或 5 道题
- 异步生成任务、阶段进度、超时查询与幂等提交
- 每题包含解析、知识点和可回查的原文引用
- 数字、时效、配方和安全内容自动标记人工复核
- 服务端确定性判分，AI 只生成解释和复训建议
- 无模型密钥时自动使用明确标识的演示生成模式
- 题库、答案和进度保存在本地，页面间只传 `taskId`

- LangGraph 规则提取、规划、出题、确定性校验、Critic 和有界修订
- 20 份脱敏评测材料，mock 评测共 100 题
- PDF/DOCX 上传、magic bytes/大小/页数校验、页码证据和人工审核
- owner/manager/employee 权限、课程发布、员工任务与服务端判分
- Redis 任务状态、COS 私有文档和 MySQL 业务数据的生产适配器
- 生产配置校验、限流、请求体限制、readiness 和脱敏 Agent 日志

本地默认使用 mock 模型和内存适配器。生产模式会强制要求 Redis、COS、MySQL、安全 JWT 和精确 CORS。

## 本地运行

需要验证真实数据库和鉴权时，先启动 MySQL 与 Redis：

```bash
docker compose -f docker-compose.dev.yml up -d
```

随后在 `backend/.env` 设置 `PLATFORM_STORE=mysql`、`MYSQL_CONNECT_ON_START=true`；纯界面演示可继续使用默认内存适配器。H5 会使用仅限非生产环境的模拟登录，微信小程序使用 `wx.login`。

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev:h5
```

浏览器打开 `http://localhost:10086`。默认 API 为 `http://localhost:8000/api/v1`。微信端执行 `npm run build:weapp`，再在微信开发者工具中导入 `frontend/dist`。

需要真实 AI 时配置 `MODEL_PROVIDER=openai_compatible`、`MODEL_API_KEY`、`MODEL_BASE_URL`、`MODEL_NAME` 和 `DEMO_MODE=false`。普通单测不访问真实模型。

## 验证

```bash
cd backend && .venv/bin/python -m pytest -q tests
cd ../frontend && npx tsc --noEmit && npm run build:h5 && npm run build:weapp
cd .. && git diff --check
```

评测命令与 mock 指标见 [backend/evals/README.md](backend/evals/README.md)，仓库验收见 [实施验收报告](docs/实施验收报告.md)，部署前检查见 [生产交接清单](docs/生产交接清单.md)。

产品与技术设计见 [需求分析文档](docs/需求分析文档-上岗练.md) 和 [方案设计文档](docs/方案设计文档-上岗练.md)。

## 许可证

本项目采用 MIT 许可证，完整法律文本见 [LICENSE](LICENSE)。
