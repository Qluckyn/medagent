# MedAgent

糖尿病诊疗多 Agent 辅助系统。输入患者完整临床信息后，系统会协同完成诊断分型、血糖评估、胰岛素功能分析、并发症评估，并生成结构化治疗建议。

项目的核心思路是：让大模型负责医学推理与文本组织，让确定性工具负责计算、规则判断和药物知识检索，尽量降低“模型心算”和药物幻觉风险。

> 本项目仅用于临床辅助决策与研究演示，不能替代执业医师诊断。

---

## 目录

- [项目概览](#项目概览)
- [系统架构](#系统架构)
- [工作流](#工作流)
- [Agent 分工](#agent-分工)
- [工具与知识库](#工具与知识库)
- [药物知识库迁移到 MySQL](#药物知识库迁移到-mysql)
- [快速开始](#快速开始)
- [API 接口](#api-接口)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [测试](#测试)
- [已知限制](#已知限制)

---

## 项目概览

MedAgent 目前包含 7 个专科 Agent：

- `intake`：采集和校验患者信息
- `diagnosis`：完成糖尿病分型与病情分析
- `blood_sugar`：完成血糖达标与波动分析
- `insulin_function`：完成胰岛素分泌与抵抗评估
- `complication`：完成并发症与异常指标评估
- `treatment`：生成治疗与随诊建议
- `report`：汇总为结构化报告

系统支持两种输入方式：

- 结构化 JSON 输入
- 对话式逐步采集输入

系统输出为 Pydantic 约束的 `MedicalReport`，便于 API 集成、前端展示与后续存档。

---

## 系统架构

```text
Streamlit Frontend
  ├─ 结构化录入
  ├─ 对话式采集
  └─ 报告查看
          │
          ▼
FastAPI Service
  ├─ POST /api/analyze
  ├─ POST /api/chat
  ├─ GET  /api/report/{id}
  ├─ GET  /api/schema
  └─ GET  /api/health
  ├─ GET  /api/drugs
  ├─ GET  /api/drugs/{id}
  ├─ POST /api/drugs
  ├─ PUT  /api/drugs/{id}
  └─ DELETE /api/drugs/{id}
          │
          ▼
LangGraph Workflow
  ├─ intake
  ├─ diagnosis
  ├─ blood_sugar
  ├─ insulin_function
  ├─ complication
  ├─ treatment
  └─ report
          │
          ▼
Deterministic Tools
  ├─ calculators.py
  ├─ guidelines.py
  ├─ lab_interpreter.py
  └─ drug_db.py
          │
          └─ 优先查 MySQL 药物知识库，失败时回退内置药物知识库
```

技术栈：

- `Python`
- `LangGraph`
- `LangChain`
- `FastAPI`
- `Streamlit`
- `Pydantic`
- `SQLAlchemy`
- `PyMySQL`

当前 LLM 接入方式支持：

- `OpenAI`
- `Qwen / DashScope OpenAI-compatible`
- `Anthropic`

状态存储：

- 多轮对话会话存储在 Redis
- 已生成报告存储在 Redis
- 默认 TTL 为 24 小时，可通过环境变量调整

---

## 工作流

```text
START
  │
  ▼
intake
  ├─ 校验 30 项必填字段
  ├─ 缺失则返回 missing_fields
  └─ 通过后继续
          │
          ▼
并行执行
  ├─ diagnosis
  ├─ blood_sugar
  └─ insulin_function
          │
          ▼
complication
          │
          ▼
treatment
          │
          ▼
report
          │
          ▼
END
```

并行关系说明：

- `diagnosis`、`blood_sugar`、`insulin_function` 彼此独立，可并行运行
- `complication` 依赖前序评估结果
- `treatment` 依赖全部评估结果
- `report` 负责汇总并再次做输出完整性校验

---

## Agent 分工

| Agent | 主要职责 | 典型工具 | 输出 |
|---|---|---|---|
| `intake` | 信息采集、结构化提取、必填校验 | `calc_bmi`, `calc_waist_hip_ratio` | `PatientData` |
| `diagnosis` | 糖尿病分型、急慢性病情分析 | `get_drug_info` | `DiagnosisResult` |
| `blood_sugar` | TIR/TAR/TBR、空腹/餐后血糖、HbA1c 评估 | `calc_tir`, `get_glucose_target` | `BloodSugarAssessment` |
| `insulin_function` | HOMA-IR、HOMA-β、分泌功能分析 | `calc_homa_ir`, `calc_homa_beta` | `InsulinFunctionAssessment` |
| `complication` | 微血管/大血管并发症、检验与体格异常分析 | `calc_egfr`, `classify_ckd_stage`, `classify_dr_stage`, `interpret_lab` | `ComplicationAssessment` |
| `treatment` | 降糖方案、禁忌症核查、相互作用、随诊建议 | `check_contraindications`, `check_drug_interactions`, `get_lipid_target` | `TreatmentPlan` |
| `report` | 汇总各模块输出并生成最终报告 | 无直接工具依赖 | `MedicalReport` |

Prompt 文件独立维护在 [`medagent/prompts`](./medagent/prompts)。

---

## 工具与知识库

### 1. 临床计算器 `medagent/tools/calculators.py`

- `calc_bmi`
- `calc_waist_hip_ratio`
- `calc_homa_ir`
- `calc_homa_beta`
- `calc_egfr`
- `calc_tir`

这些工具负责可复现的医学计算，避免让 LLM 自行估算。

### 2. 指南规则引擎 `medagent/tools/guidelines.py`

- `get_glucose_target`
- `get_bp_target`
- `get_lipid_target`
- `classify_ckd_stage`
- `classify_dr_stage`

### 3. 检验值解释器 `medagent/tools/lab_interpreter.py`

- `interpret_lab`

用于对血糖、HbA1c、血脂、肝肾功能、尿酸、UACR 等结果做规则化解释。

### 4. 药物知识库 `medagent/tools/drug_db.py`

当前内置约 21 种糖尿病及相关常用药物信息，支持：

- `get_drug_info`
- `check_contraindications`
- `check_drug_interactions`

药物工具现在已经接入 MySQL 药物知识库，会优先查 MySQL；如果数据库不可用、未配置或查询未命中，则自动回退到代码内置药物知识库。

---

## 药物知识库迁移到 MySQL

这是当前项目中最重要的新增改动之一。

### 设计目标

- 让药物数据从代码常量迁移到 MySQL 药物知识库，便于后续扩充和维护
- 保留代码内置药物知识库作为兜底，避免数据库异常时系统完全不可用
- 保持 `drug_db.py` 的工具接口不变，减少对 Agent 层的影响

### 当前实现

相关文件：

- [`medagent/storage/database.py`](./medagent/storage/database.py)：MySQL 连接与引擎缓存
- [`medagent/storage/drug_repository.py`](./medagent/storage/drug_repository.py)：药物查询与相互作用查询
- [`scripts/schema_mysql.sql`](./scripts/schema_mysql.sql)：MySQL 表结构
- [`scripts/init_drug_mysql.py`](./scripts/init_drug_mysql.py)：建表并导入内置药物数据
- [`medagent/tools/drug_db.py`](./medagent/tools/drug_db.py)：工具层，负责“MySQL 优先，内置回退”

### 查询策略

`medagent/tools/drug_db.py` 的行为是：

1. 优先从 MySQL 药物知识库查询药物信息或相互作用
2. 如果数据库未启用、配置缺失、连接失败、依赖缺失或查询异常，则回退到内置 `DRUG_DATABASE`
3. 对于药物名称列表，优先返回 MySQL 中的名称；若数据库不可用，则返回内置药名列表

这意味着：

- 开发环境可以不配置 MySQL，系统仍然可运行
- 生产或演示环境可以启用 MySQL 药物知识库，获得更可维护的药物数据来源

### MySQL 表结构

初始化脚本会创建以下表：

- `drugs`
- `drug_aliases`
- `drug_indications`
- `drug_contraindications`
- `drug_side_effects`
- `drug_interactions`

其中：

- `drugs` 存药物主记录
- `drug_aliases` 预留别名匹配能力
- `drug_indications`、`drug_contraindications`、`drug_side_effects` 负责拆分多值字段
- `drug_interactions` 存储药物间交互规则

### 初始化方式

先在 MySQL 中创建数据库，例如：

```sql
CREATE DATABASE drug_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

然后配置 `.env` 中的 MySQL 连接信息，再执行：

```bash
python scripts/init_drug_mysql.py
```

该脚本会：

- 按 `schema_mysql.sql` 建表
- 将代码中的内置药物数据导入 MySQL
- 清空并重建相互作用数据
- 以幂等方式更新已有药物主记录

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 复制环境变量模板

Linux / macOS:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

### 3. 配置 LLM

至少配置一组可用模型：

- OpenAI 兼容接口
- Qwen / DashScope
- Anthropic

最小示例：

```bash
LLM_PROVIDER=qwen
QWEN_MODEL=qwen-plus
QWEN_API_KEY=your-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_ENABLE_THINKING=false
```

### 4. 可选：启用 MySQL 药物知识库

如果你希望启用 MySQL 药物知识库，在 `.env` 中配置：

```bash
MYSQL_DRUG_DB_ENABLED=true
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=drug_db
MYSQL_CHARSET=utf8mb4
```

初始化数据库：

```bash
python scripts/init_drug_mysql.py
```

如果不配置 MySQL，系统会自动回退到内置药物知识库。

### 5. 配置 Redis

多轮对话会话和生成后的报告默认存储到 Redis。

```bash
REDIS_URL=redis://:qyn030113@localhost:6379
REDIS_CHAT_TTL_SECONDS=86400
REDIS_REPORT_TTL_SECONDS=86400
```

说明：

- `REDIS_URL` 支持本机、Docker 或云 Redis
- 默认 TTL 为 24 小时
- 每次读取或更新会刷新 TTL

### 6. 运行项目

#### 方式一：CLI 演示

```bash
python demo.py
```

用于快速跑通完整分析流程，最适合先验证环境是否正常。

#### 方式二：启动后端 API

推荐先使用：

```bash
python -m uvicorn medagent.main:app --host 127.0.0.1 --port 8000
```

开发时如本机端口与权限正常，再使用热重载：

```bash
python -m uvicorn medagent.main:app --host 127.0.0.1 --port 8000 --reload
```

启动后可访问：

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/api/health`

#### 方式三：启动前端

先启动后端，再运行：

```bash
streamlit run medagent/frontend/app.py
```

浏览器访问：

- `http://127.0.0.1:8501`

---

## API 接口

### `POST /api/analyze`

输入结构化患者数据，返回完整分析报告。

请求体支持两种形式：

```json
{
  "patient_data": {}
}
```

或：

```json
{
  "raw_text": "患者自然语言病历文本"
}
```

成功返回示例：

```json
{
  "report_id": "a1b2c3d4",
  "success": true,
  "report": {}
}
```

失败返回示例：

```json
{
  "report_id": "a1b2c3d4",
  "success": false,
  "error": "缺少必填字段: ...",
  "missing_fields": [
    "clinical_tests.blood_sugar.hba1c"
  ]
}
```

### `POST /api/chat`

通过对话逐步采集患者信息，采集完整后自动触发分析。

### `GET /api/report/{report_id}`

根据 `report_id` 获取已生成的报告。

说明：

- `/api/chat` 的多轮会话状态保存在 Redis
- `/api/report/{report_id}` 读取的是 Redis 中缓存的报告
- 如果 Redis 不可用，相关接口会返回 `503`

### `GET /api/schema`

返回 `PatientData` 的 JSON Schema。

### `GET /api/health`

健康检查接口。

### 药物知识库管理接口

以下接口面向 MySQL 药物知识库后台管理：

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/drugs` | 获取药物列表 |
| `GET` | `/api/drugs/{id}` | 获取单个药物详情 |
| `POST` | `/api/drugs` | 创建药物 |
| `PUT` | `/api/drugs/{id}` | 完整更新药物 |
| `DELETE` | `/api/drugs/{id}` | 删除药物 |

请求体字段：

```json
{
  "name": "二甲双胍",
  "category": "双胍类",
  "aliases": ["metformin"],
  "indications": ["2型糖尿病一线用药"],
  "contraindications": {
    "egfr<30": "eGFR<30 mL/min禁用"
  },
  "dose_range": "500-2000mg/日，分2-3次",
  "side_effects": ["胃肠反应", "维生素B12缺乏"],
  "notes": "缓释片可减少胃肠反应"
}
```

说明：

- 这些接口依赖 MySQL 药物知识库可用
- 若 MySQL 未配置、已禁用或不可连接，接口会返回 `503`
- 当前仅管理药物主记录，不包含 `drug_interactions` 的后台维护接口

---

## 项目结构

```text
medagent/
├── demo.py
├── README.md
├── DEVELOPMENT.md
├── requirements.txt
├── .env.example
├── scripts/
│   ├── init_drug_mysql.py
│   └── schema_mysql.sql
├── tests/
│   ├── sample_patient.json
│   ├── sample_output.json
│   ├── demo_output.json
│   ├── test_schema.py
│   └── test_api.py
└── medagent/
    ├── __init__.py
    ├── config.py
    ├── main.py
    ├── agents/
    ├── graph/
    ├── models/
    ├── prompts/
    ├── tools/
    ├── storage/
    │   ├── database.py
    │   └── drug_repository.py
    └── frontend/
        └── app.py
```

补充说明：

- `medagent/agents`：各专科 Agent 实现
- `medagent/graph/workflow.py`：LangGraph 编排入口
- `medagent/models/schemas.py`：输入输出数据模型
- `medagent/tools`：所有确定性工具
- `medagent/storage`：MySQL 药物知识库接入层
- `scripts`：数据库初始化与结构脚本

---

## 配置说明

`.env.example` 中已经包含主要配置项。

### LLM 配置

```bash
LLM_PROVIDER=qwen
LLM_MODEL=qwen-plus

QWEN_MODEL=qwen-plus
QWEN_API_KEY=your-dashscope-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_ENABLE_THINKING=false

OPENAI_API_KEY=your-openai-or-compatible-key
OPENAI_BASE_URL=

ANTHROPIC_API_KEY=your-anthropic-key
ANTHROPIC_BASE_URL=
ANTHROPIC_MODEL=
```

说明：

- `LLM_PROVIDER` 支持 `openai`、`qwen`、`anthropic`
- `qwen` 走 OpenAI-compatible 协议接入
- `QWEN_ENABLE_THINKING=false` 可以减少影响下游 JSON 解析的额外输出

### MySQL 药物知识库配置

```bash
MYSQL_DRUG_DB_ENABLED=true
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your-mysql-password
MYSQL_DATABASE=drug_db
MYSQL_CHARSET=utf8mb4
```

可选项：

```bash
MYSQL_URL=mysql+pymysql://user:password@host:3306/drug_db?charset=utf8mb4
MYSQL_POOL_RECYCLE=1800
```

说明：

- 若设置了 `MYSQL_URL`，会优先使用完整连接串
- 若 `MYSQL_DRUG_DB_ENABLED=false`，药物工具会直接跳过数据库层
- 若 MySQL 连接失败，工具层会自动回退到内置药物知识库

### Redis 配置

```bash
REDIS_URL=redis://:qyn030113@localhost:6379
REDIS_CHAT_TTL_SECONDS=86400
REDIS_REPORT_TTL_SECONDS=86400
```

说明：

- `REDIS_URL` 为 Redis 连接串
- `REDIS_CHAT_TTL_SECONDS` 控制多轮会话过期时间
- `REDIS_REPORT_TTL_SECONDS` 控制报告缓存过期时间
- 未来 Docker 部署时，可直接把 `REDIS_URL` 指向容器服务名

---

## 测试

### 数据模型测试

```bash
python tests/test_schema.py
```

### API 测试

先启动后端：

```bash
python -m uvicorn medagent.main:app --host 127.0.0.1 --port 8000
```

再运行：

```bash
python tests/test_api.py
```

### 药物知识库管理接口测试

确保 MySQL 药物知识库已初始化后，运行：

```bash
python tests/test_drug_admin_api.py
```

---

## 已知限制

1. Redis 存储依赖外部服务可用；若 Redis 不可用，对话和报告接口将无法正常工作。
2. 药物知识库虽已支持 MySQL，但初始化脚本当前导入的仍是代码内置药物数据，后续仍可继续扩展数据库内容。
3. 药物知识库覆盖的是常见糖尿病相关药物，罕见药物和新上市药物可能未收录。
4. 完整分析耗时受模型响应和工具调用轮次影响，通常比普通问答更慢。
5. 输出仍需由临床专业人员复核，不能直接作为诊疗依据。

---

## 开发备注

- Agent 的工具调用轮次限制在 `medagent/agents/_base.py` 中配置
- API 入口在 [`medagent/main.py`](./medagent/main.py)
- 前端入口在 [`medagent/frontend/app.py`](./medagent/frontend/app.py)
- 药物知识库初始化脚本在 [`scripts/init_drug_mysql.py`](./scripts/init_drug_mysql.py)

如果后续你继续把药物数据完全外置化，这份 README 已经把当前“内置药物知识库 + MySQL 存储层 + 自动回退”的设计说明补齐了，后面只需要继续更新数据库字段和初始化方式即可。
