# EthosGate · 善治

内部试点版 LLM 部署伦理评估工具：FastAPI 后端、Vite React 前端、PostgreSQL/Docker Compose 主配置、SQLite 本地回退、OpenAI Responses API 辅助评审、被部署模型 OpenAI 兼容接口实测。

## 默认账号

- 邮箱：`admin@example.com`
- 密码：`admin123456`

## 后端运行

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=你的OpenAI密钥
python3 -m uvicorn app.main:app --reload --port 8000
```

没有 `DATABASE_URL` 时自动使用 `backend/data/app.db`。LLM 辅助功能必须配置 `OPENAI_API_KEY`，否则相关接口会返回明确错误。

生产或准生产环境至少设置：

```bash
export APP_ENV=production
export JWT_SECRET=一段强随机密钥
export ALLOW_DEFAULT_ADMIN_PASSWORD=false
```

## PostgreSQL 可选配置

```bash
docker compose up -d postgres
export DATABASE_URL=postgresql+psycopg://ethics:ethics@localhost:5432/ethics_dashboard
```

当前项目保留 SQLite 回退，因此没有 Docker 也可以本地验证。

## 前端运行

```bash
cd frontend
npm install
npm run dev
```

前端默认连接 `http://localhost:8000`。可设置 `VITE_API_BASE_URL` 覆盖。

## 一键开发

```bash
npm install
npm run dev
```

## 主要功能

- 项目设置：模型信息、部署边界、决策影响、人类复核、退出/申诉、责任主体。
- 预测模块：风险问卷、证据链、风险公式、雷达图和热力图。
- 模型实测：配置被部署模型 Base URL、模型名和运行时 API Key，执行教育辅导 LLM 红队测试套件。
- 测试复核：自动规则只做初筛，LLM judge 只生成草稿，正式报告只采纳人工 `accepted` 或 `revised` 的实测证据。
- 证据中心：统一展示模型实测、人工复核和报告可引用证据。
- 反思模块：价值预设问卷、设计预设声明、人工确认。
- 包容模块：利益相关者矩阵、参与闭环记录。
- 响应模块：监控指标、复审时间线、事故响应。
- 法规映射：规范要求、证据状态、审查备注。
- LLM 审计：OpenAI 输出默认草稿，人工确认后才进入正式结论。
- 伦理门禁：`READY`、`READY_WITH_CONDITIONS`、`NEEDS_REVIEW`、`BLOCKED`。
- 报告导出：Markdown 和 HTML。

## 项目文档

课程/项目提交文档见：[docs/项目文档.md](docs/项目文档.md)。文档包含项目背景、系统需求设计、详细设计、系统使用说明和开源仓库链接。

## 模型实测说明

当前内部试点优先支持 OpenAI 兼容 `/v1/chat/completions` 接口。配置示例：

- Base URL：`https://api.openai.com/v1` 或你的模型网关 `/v1`
- Request Style：`openai_chat`
- Auth Header：`Authorization`
- Auth Scheme：`Bearer`
- API Key：只在运行测试时提交，不以明文保存到数据库；系统仅保存脱敏提示。

内置“教育辅导LLM伦理红队测试”覆盖偏见、公平性、未成年人隐私、安全绕过、钓鱼滥用、过度拒答、申诉、幻觉、提示注入和教师复核边界。未逐条人工复核的测试结果只进入待复核附件，不进入正式结论。

## API 文档

启动后访问：

- Swagger：`http://localhost:8000/docs`
- 健康检查：`http://localhost:8000/api/health`
- 就绪检查：`http://localhost:8000/api/ready`
