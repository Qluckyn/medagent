# MedAgent — 糖尿病诊疗智能Agent系统

基于多Agent协作的糖尿病诊疗辅助系统。输入患者完整临床信息，自动完成诊断分型、血糖评估、胰岛素功能分析、并发症评估，并生成个体化治疗方案。所有关键计算（HOMA-IR、eGFR、TIR）和药物禁忌症核查由确定性工具完成，不依赖大模型"心算"。

> ⚠️ 本系统为临床辅助决策工具，输出仅供医疗专业人员参考，不能替代医生诊断。

---

## 目录

- [系统架构](#系统架构)
- [核心特性](#核心特性)
- [工作流程](#工作流程)
- [Agent 说明](#agent-说明)
- [工具（Tools）说明](#工具tools说明)
- [数据模型](#数据模型)
- [快速开始](#快速开始)
- [API 接口](#api-接口)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [已知限制](#已知限制)

---

## 系统架构

```
                        ┌─────────────────┐
                        │  Streamlit 前端  │  结构化录入 / 对话采集 / 报告查看
                        └────────┬────────┘
                                 │ HTTP
                        ┌────────▼────────┐
                        │  FastAPI 服务    │  /api/analyze /api/chat /api/report
                        └────────┬────────┘
                                 │
                ┌────────────────▼────────────────┐
                │     LangGraph 工作流编排          │
                └────────────────┬────────────────┘
                                 │
   intake ─→ [校验] ─→ 并行(diagnosis │ blood_sugar │ insulin) ─→ complication ─→ treatment ─→ report
                                 │
                   每个 Agent 可调用确定性 Tools:
                   计算器 / 药物库 / 指南规则 / 检验判读
```

技术栈：**Python · LangGraph · LangChain · FastAPI · Streamlit · Pydantic**
LLM 底座：可配置（OpenAI / Anthropic），当前使用 GPT-4.1（京东云 ModelService）

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **多Agent协作** | 7个专科Agent分工，诊断/血糖/胰岛素三路并行，提升效率 |
| **确定性工具** | HOMA-IR、eGFR、TIR、药物禁忌症由代码计算/查表，杜绝大模型幻觉 |
| **必填校验** | 强制校验30项必填字段（对应采集规范黄色高亮项），缺失则拒绝分析 |
| **双输入模式** | 支持结构化JSON导入 和 自然语言对话式采集 |
| **可配置模型** | 通过 `.env` 切换 LLM provider，统一接口 |
| **结构化输出** | Pydantic强制约束输出schema，20项必输出字段全覆盖 |

---

## 工作流程

```
START
  │
  ▼
┌─────────┐   校验30项必填字段
│ intake  │ ──────────────────┐
└────┬────┘                   │ 缺失
     │ 通过                    ▼
     │                   ┌──────────┐
     │                   │ error_end │ 返回缺失字段列表
     │                   └──────────┘
     ▼ (并行 fan-out)
┌──────────┐ ┌────────────┐ ┌──────────┐
│diagnosis │ │blood_sugar │ │ insulin  │
└────┬─────┘ └─────┬──────┘ └────┬─────┘
     └─────────────┼─────────────┘ (fan-in)
                   ▼
            ┌──────────────┐
            │ complication │
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │  treatment   │
            └──────┬───────┘
                   ▼
            ┌──────────────┐
            │   report     │ 汇总 + 必输出校验
            └──────┬───────┘
                   ▼
                  END
```

并行设计：`diagnosis`、`blood_sugar`、`insulin` 三个Agent无相互依赖，同时执行；`complication` 需要诊断结果，故在fan-in后执行；`treatment` 需要全部评估结果。

---

## Agent 说明

| Agent | 职责 | 绑定工具 | 输出 |
|-------|------|---------|------|
| **intake** | 采集校验患者数据，支持JSON导入与对话提取；校验30项必填字段 | calc_bmi, calc_waist_hip_ratio | PatientData |
| **diagnosis** | 糖尿病分型（1型/2型/LADA/妊娠/老年/特殊）+ 急慢性病情分析 | get_drug_info | DiagnosisResult |
| **blood_sugar** | TIR/TAR/TBR、空腹/餐后达标、血糖波动、时段分析、HbA1c评估与预测 | calc_tir, get_glucose_target | BloodSugarAssessment |
| **insulin** | 基础/餐时胰岛素分泌功能、HOMA-IR/β、分泌曲线（抵抗/缺陷/延迟）分析 | calc_homa_ir, calc_homa_beta | InsulinFunctionAssessment |
| **complication** | 微血管（肾/眼/神经）+ 大血管（心/脑/颈/下肢）并发症、指标异常、体格异常 | calc_egfr, classify_ckd_stage, classify_dr_stage, get_bp_target, interpret_lab | ComplicationAssessment |
| **treatment** | 降糖方案、并发症治疗、禁忌症核查、随诊计划、生活方式、自我管理 | check_contraindications, check_drug_interactions, get_drug_info, get_glucose_target, get_lipid_target | TreatmentPlan |
| **report** | 汇总全部评估，校验20项必输出字段，生成结构化报告 | — | MedicalReport |

每个Agent的系统提示词独立维护在 `medagent/prompts/*.md`，便于调整专业逻辑而不改代码。

---

## 工具（Tools）说明

工具是本系统区别于"直接问大模型"的关键——确定性计算和查表，结果可靠可复现。

### 临床计算器 (`tools/calculators.py`)
| 工具 | 功能 |
|------|------|
| `calc_bmi` | BMI计算 + 中国标准分类（偏瘦/正常/超重/肥胖） |
| `calc_waist_hip_ratio` | 腰臀比 + 中心性肥胖判定（性别相关） |
| `calc_homa_ir` | 胰岛素抵抗指数 + 分级判读 |
| `calc_homa_beta` | β细胞功能指数 + 判读 |
| `calc_egfr` | CKD-EPI公式计算eGFR + CKD分期 |
| `calc_tir` | 从血糖读数计算TIR/TAR/TBR + 达标判定 |

### 药物知识库 (`tools/drug_db.py`)
- 收录 **21种** 糖尿病相关药物（双胍/磺脲/格列奈/SGLT2i/GLP-1RA/DPP-4i/TZD/α-糖苷酶抑制剂/胰岛素/他汀/ARB/降尿酸）
- `get_drug_info` — 适应症、剂量范围、不良反应
- `check_contraindications` — 结合患者eGFR/肝功/过敏/妊娠/心衰等逐项核查禁忌
- `check_drug_interactions` — 药物相互作用检查（9条规则）

### 指南规则引擎 (`tools/guidelines.py`)
| 工具 | 功能 |
|------|------|
| `get_glucose_target` | 个体化血糖目标（一般/老年/年轻/妊娠） |
| `get_bp_target` | 血压控制目标（糖尿病/CKD/蛋白尿/高龄） |
| `get_lipid_target` | 血脂目标（按心血管风险分层） |
| `classify_ckd_stage` | CKD分期（G1-G5 × A1-A3）+ 风险矩阵 |
| `classify_dr_stage` | 糖尿病视网膜病变分级 |

### 检验值判读器 (`tools/lab_interpreter.py`)
- `interpret_lab` — 按性别年龄判读 **11类** 化验项（血糖/HbA1c/血脂四项/肝功/肾功/尿酸/UACR），给出正常/异常及临床意义

---

## 数据模型

定义于 `medagent/models/schemas.py`，使用Pydantic。必填字段（对应采集规范黄色高亮）用 `Field(...)` 强制约束。

**输入模型 `PatientData`**（8个必填子模块）：
- `core_symptoms` — 核心症状（三多一少、低血糖反应）
- `medical_history` — 病程关键点
- `past_history` — 既往史、过敏史
- `physical_exam` — 体格检查（身高体重BMI、血压）
- `clinical_tests` — 血糖/胰岛素/代谢/尿液/抗体
- `medications` — 口服药/胰岛素/GLP-1
- `lifestyle` — 膳食/运动
- `family_history` — 家族史

**输出模型 `MedicalReport`**（5个必输出 + 2个可选）：
- 必输出：`diagnosis`, `blood_sugar_assessment`, `insulin_assessment`, `complication_assessment`, `treatment_plan`
- 可选：`warning_prediction`（预警预测）, `comprehensive_strategy`（综合对策）

派生字段（BMI、腰臀比）由 `compute_derived_fields()` 确定性计算。

---

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 填入 LLM provider 和 API Key
```

### 3. 三种运行方式

**方式一：CLI 演示（推荐先跑这个）**
```bash
python demo.py
```
加载样本病例，实时打印工具调用，输出完整报告。

**方式二：Web 服务**
```bash
# 终端1 — 启动后端
uvicorn medagent.main:app --reload

# 终端2 — 启动前端
streamlit run medagent/frontend/app.py
# 浏览器打开 http://localhost:8501
```

**方式三：API 调用**
```bash
uvicorn medagent.main:app --reload
python tests/test_api.py   # 或用 curl/Postman 调用
```

### 4. 运行测试
```bash
python tests/test_schema.py   # 数据模型与校验
python tests/test_api.py      # API 集成测试（需后端运行）
```

---

## API 接口

服务启动后访问 `http://localhost:8000/docs` 查看交互式文档。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analyze` | 结构化JSON输入 → 完整分析报告 |
| POST | `/api/chat` | 对话模式，逐步采集患者信息 |
| GET | `/api/report/{id}` | 获取已生成的报告 |
| GET | `/api/schema` | 获取PatientData的JSON Schema（含必填标注） |
| GET | `/api/health` | 健康检查 |

**示例：`POST /api/analyze`**
```json
{
  "patient_data": { ...完整PatientData JSON... }
}
```
返回：
```json
{
  "report_id": "a1b2c3d4",
  "success": true,
  "report": { ...MedicalReport... }
}
```
若必填字段缺失：
```json
{
  "report_id": "...",
  "success": false,
  "error": "缺少必填字段: ...",
  "missing_fields": ["clinical_tests.blood_sugar.hba1c", ...]
}
```

---

## 项目结构

```
medagent/
├── demo.py                      # CLI 演示脚本（含工具调用追踪）
├── requirements.txt
├── .env.example                 # 环境变量模板
├── medagent/
│   ├── config.py                # LLM 配置（多provider切换）
│   ├── main.py                  # FastAPI 入口
│   ├── models/
│   │   └── schemas.py           # Pydantic 数据模型（输入+输出+图状态）
│   ├── agents/
│   │   ├── _base.py             # tool-calling 循环 + JSON解析（共享）
│   │   ├── intake.py            # 信息采集与校验
│   │   ├── diagnosis.py         # 诊断评估
│   │   ├── blood_sugar.py       # 血糖评估
│   │   ├── insulin_function.py  # 胰岛素功能评估
│   │   ├── complication.py      # 并发症评估
│   │   ├── treatment.py         # 治疗方案
│   │   └── report.py            # 报告生成
│   ├── graph/
│   │   └── workflow.py          # LangGraph 工作流（并行+串行编排）
│   ├── prompts/                 # 7个Agent的系统提示词（.md）
│   ├── tools/
│   │   ├── calculators.py       # 临床计算器
│   │   ├── drug_db.py           # 药物知识库
│   │   ├── guidelines.py        # 指南规则引擎
│   │   └── lab_interpreter.py   # 检验值判读器
│   └── frontend/
│       └── app.py               # Streamlit 前端（3个Tab）
└── tests/
    ├── sample_patient.json      # 样本病例（55岁2型糖尿病）
    ├── test_schema.py           # 模型与校验测试
    ├── test_api.py              # API 集成测试
    └── demo_output.json         # 演示输出样例
```

---

## 配置说明

`.env` 文件关键配置：

```bash
# Provider 选择: openai / anthropic
LLM_PROVIDER=openai
LLM_MODEL=GPT-4.1

# OpenAI 兼容接口
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://your-endpoint/v1

# Anthropic（可选）
ANTHROPIC_API_KEY=your-key
ANTHROPIC_BASE_URL=http://127.0.0.1:8082
ANTHROPIC_MODEL=Claude-Opus-4.6
```

切换模型只需改 `LLM_PROVIDER` 和 `LLM_MODEL`，代码无需改动（`config.py:get_llm()` 统一封装）。

工具调用轮次上限：`medagent/agents/_base.py` 中 `MAX_TOOL_ITERATIONS = 10`。

---

## 已知限制

1. **性能**：单次完整分析约 80-160 秒，取决于模型调用工具的轮次（complication 和 treatment 工具调用最密集）。
2. **存储**：报告和对话会话目前为内存存储（`reports_store`、`chat_sessions`），服务重启后丢失。生产环境需接入持久化。
3. **药物库范围**：覆盖常用糖尿病及相关药物21种，罕见药物或新上市药物可能未收录（查询时返回"未找到"提示）。
4. **预警预测/综合对策**：输出文档中标记为非必填的"预警及预测""综合性对策"部分由 report agent 附带生成，质量不如核心评估稳定，尚无专门Agent。
5. **临床免责**：本系统为辅助决策工具，所有输出需由执业医师复核，不构成诊疗依据。
