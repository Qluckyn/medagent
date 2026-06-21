# MedAgent 开发者指南

面向需要扩展或维护本系统的开发者。涵盖：如何新增工具、如何新增Agent、如何修改工作流、如何扩充数据模型，以及常见坑。

阅读本指南前，建议先读 [README.md](./README.md) 了解整体架构。

---

## 目录

- [核心概念](#核心概念)
- [数据流：一次请求的完整路径](#数据流一次请求的完整路径)
- [如何新增一个 Tool](#如何新增一个-tool)
- [如何新增一个 Agent](#如何新增一个-agent)
- [如何修改工作流](#如何修改工作流)
- [如何扩充数据模型](#如何扩充数据模型)
- [药物知识库开发说明](#药物知识库开发说明)
- [Redis 会话与报告存储](#redis-会话与报告存储)
- [Agent 实现规范](#agent-实现规范)
- [调试技巧](#调试技巧)
- [常见坑](#常见坑)

---

## 核心概念

系统有三层状态表示，理解它们的转换关系是开发的关键：

| 状态 | 类型 | 位置 | 用途 |
|------|------|------|------|
| `WorkflowState` | `TypedDict` | `graph/workflow.py` | LangGraph 内部状态，字段带 `Annotated[..., _last]` reducer 以支持并行写入 |
| `GraphState` | Pydantic `BaseModel` | `models/schemas.py` | Agent 函数操作的对象，类型安全 |
| 各 `*Result` / `*Assessment` | Pydantic `BaseModel` | `models/schemas.py` | Agent 的结构化输出 |

**转换规则**（已封装在 `workflow.py`）：
- 进入节点：`WorkflowState`(dict) → `_state_to_gs()` → `GraphState`(pydantic)
- 离开节点：`GraphState` 字段 → `_gs_field_to_dict()` → dict → 写回 `WorkflowState`

为什么要两层？LangGraph 的并行节点需要 dict + reducer 来合并状态；而 Agent 业务逻辑用 Pydantic 更安全。这层转换是刻意的设计。

---

## 数据流：一次请求的完整路径

以 `POST /api/analyze` 为例：

```
1. main.py: analyze()
   └─ run_analysis(patient_data_dict)          [graph/workflow.py]

2. workflow.py: run_analysis()
   ├─ 构造 initial_state (WorkflowState dict)
   ├─ PatientData(**dict) 验证 → 存入 state["patient_data"]
   └─ app.invoke(initial_state)                 LangGraph 执行

3. LangGraph 逐节点执行:
   intake_node(state)
     ├─ _state_to_gs(state) → GraphState
     ├─ run_intake_agent(gs)                     [agents/intake.py]
     │    └─ validate_required_fields()          校验30项必填
     └─ return {patient_data, intake_valid, ...} 写回 dict

   check_intake(state) → 条件路由
     ├─ intake_valid=True  → [diagnosis, blood_sugar, insulin] 并行
     └─ intake_valid=False → error_end

   diagnosis_node / blood_sugar_node / insulin_node  (并行)
     └─ 各自 run_*_agent(gs)
          └─ run_with_tools(prompt, content, TOOLS) [agents/_base.py]
               └─ LLM ←→ tool 调用循环

   complication_node → treatment_node → report_node (串行)

4. 返回 final result dict → main.py 包装为 AnalyzeResponse
```

---

## 如何新增一个 Tool

工具是确定性函数，用 `@tool` 装饰。以新增"计算理想体重"为例：

### 步骤 1：在对应工具模块写函数

编辑 `medagent/tools/calculators.py`：

```python
@tool
def calc_ideal_weight(height_cm: float, gender: str = "男") -> str:
    """计算理想体重和体重管理目标。

    Args:
        height_cm: 身高，单位厘米
        gender: 性别，"男"或"女"
    """
    height_m = height_cm / 100
    # Broca 改良公式
    if gender == "男":
        ideal = (height_cm - 100) * 0.9
    else:
        ideal = (height_cm - 105) * 0.92
    ideal = round(ideal, 1)
    return f"理想体重 ≈ {ideal} kg（正常波动范围 ±10%: {round(ideal*0.9,1)}-{round(ideal*1.1,1)} kg）"
```

**要点**：
- 必须有 docstring，且每个参数都在 `Args:` 中说明——LLM 靠这个决定如何调用。
- 参数类型用基础类型（`float`/`int`/`str`/`bool`/`list`），便于 LLM 传参。
- 返回 `str`，内容应自包含、可读（LLM 会基于返回文本继续推理）。
- 给可选参数默认值，避免 LLM 漏传必填项时报错。

### 步骤 2：绑定到 Agent

编辑需要该工具的 Agent，例如 `medagent/agents/treatment.py`：

```python
from medagent.tools.calculators import calc_ideal_weight   # 新增导入

TOOLS = [
    check_contraindications,
    check_drug_interactions,
    get_drug_info,
    get_glucose_target,
    get_lipid_target,
    calc_ideal_weight,        # 加入列表
]
```

### 步骤 3：（可选）在 user_content 提示中引导

如果希望 LLM 主动调用，在 Agent 的 `user_content` 里点名：

```python
user_content = (
    "...制定生活方式干预时，可用 calc_ideal_weight 计算目标体重..."
)
```

### 步骤 4：单元测试

```python
python -c "
from medagent.tools.calculators import calc_ideal_weight
print(calc_ideal_weight.invoke({'height_cm': 172, 'gender': '男'}))
"
```

**完成。** 不需要改工作流或数据模型。

---

## 如何新增一个 Agent

假设要新增一个"预警预测 Agent"（prediction），输出病情趋势预警。

### 步骤 1：定义输出模型

编辑 `medagent/models/schemas.py`，`WarningPrediction` 已存在可复用，否则新增：

```python
class WarningPrediction(BaseModel):
    """预警及预测 [输出]"""
    disease_trend: str = Field(..., description="糖尿病病情发展趋势及预警")
    complication_trend: str = Field(..., description="并发症发展趋势及预警")
    medication_efficacy: str = Field(..., description="药物疗效预测")
```

并在 `GraphState` 中加字段：

```python
class GraphState(BaseModel):
    ...
    prediction_result: Optional[WarningPrediction] = None   # 新增
```

### 步骤 2：写系统提示词

创建 `medagent/prompts/prediction.md`，定义该Agent的角色、职责、输出JSON格式（参考现有 prompt 的写法）。

### 步骤 3：写 Agent 实现

创建 `medagent/agents/prediction.py`，遵循统一模式：

```python
"""预警预测Agent"""

import json
from pathlib import Path

from medagent.agents._base import parse_json_response, run_with_tools
from medagent.models.schemas import GraphState, WarningPrediction

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "prediction.md"

TOOLS = []   # 如需工具则加入

def run_prediction_agent(state: GraphState) -> GraphState:
    if not state.patient_data:
        state.error = "预警Agent: 缺少患者数据"
        return state

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    context = {
        "diagnosis": state.diagnosis_result.model_dump() if state.diagnosis_result else None,
        "blood_sugar": state.blood_sugar_assessment.model_dump() if state.blood_sugar_assessment else None,
        "complication": state.complication_assessment.model_dump() if state.complication_assessment else None,
    }
    user_content = f"请根据评估结果预测病情趋势，输出JSON:\n\n{json.dumps(context, ensure_ascii=False, indent=2)}"

    content = run_with_tools(system_prompt, user_content, TOOLS)
    try:
        state.prediction_result = WarningPrediction(**parse_json_response(content))
    except Exception as e:
        state.error = f"预警预测解析失败: {str(e)}"
    return state
```

> 注：若 Agent 不需要工具，`TOOLS = []` 时 `run_with_tools` 仍可正常工作（LLM 不会调用任何工具，直接返回文本）。也可以直接用 `config.get_llm()` 自己调用，参考 `report.py`。

### 步骤 4：接入工作流

编辑 `medagent/graph/workflow.py`：

**4a. 在 `WorkflowState` 加字段：**
```python
class WorkflowState(TypedDict, total=False):
    ...
    prediction_result: Annotated[dict | None, _last]
```

**4b. 写节点函数：**
```python
from medagent.agents.prediction import run_prediction_agent

def prediction_node(state: WorkflowState) -> dict:
    gs = _state_to_gs(state)
    gs = run_prediction_agent(gs)
    return {"prediction_result": _gs_field_to_dict(gs.prediction_result)}
```

**4c. 注册节点 + 连边**（在 `build_workflow()` 中）：
```python
workflow.add_node("prediction", prediction_node)
# 例如让 prediction 在 complication 后、treatment 前并行
workflow.add_edge("complication", "prediction")
workflow.add_edge("prediction", "report")   # 或接到合适位置
```

**4d. 在 `_state_to_gs` 转换中处理**（若该字段是嵌套dict需还原为pydantic，参考 patient_data 的处理；简单字段无需特殊处理，GraphState 会自动验证）。

### 步骤 5：让 report 汇总它

编辑 `medagent/agents/report.py`，把 `prediction_result` 加入 report 的 context 和 `MedicalReport` 构造。

### 步骤 6：端到端测试

```bash
python demo.py
```

---

## 如何修改工作流

工作流定义在 `graph/workflow.py:build_workflow()`。

### 并行 vs 串行

- **串行**：`workflow.add_edge("A", "B")` — A 完成后执行 B。
- **并行**：多个节点共享同一前驱即并行。当前 `diagnosis`/`blood_sugar`/`insulin` 通过条件路由 `check_intake` 同时启动。
- **fan-in**：多个节点指向同一后继，后继会等所有前驱完成。如三个评估Agent都 `add_edge(..., "complication")`。

### 条件路由

```python
def check_intake(state) -> list[str]:
    if state.get("intake_valid"):
        return ["diagnosis", "blood_sugar", "insulin"]   # 返回要执行的节点列表
    return ["error_end"]

workflow.add_conditional_edges("intake", check_intake,
    ["diagnosis", "blood_sugar", "insulin", "error_end"])  # 所有可能的目标
```

### 并行写入冲突

并行节点若写同一个 state 字段会冲突。本系统用 `Annotated[type, _last]` reducer 解决——每个并行节点**只写自己的输出字段**（diagnosis_node 只写 `diagnosis_result`），互不干扰。**新增并行节点时务必遵守这一点。**

---

## 如何扩充数据模型

数据模型在 `models/schemas.py`。

### 新增一个采集字段

例如在体格检查加"踝肱指数(ABI)"：

```python
class PhysicalExam(BaseModel):
    ...
    abi: Optional[float] = Field(None, description="踝肱指数(下肢动脉评估)")
```

- **必填** → 用 `Field(..., description=...)`，并在 `agents/intake.py:REQUIRED_FIELD_PATHS` 加上路径（如 `"physical_exam.abi"`）。
- **可选** → 用 `Field(None, ...)`，无需改校验。

### 派生字段

如需自动计算（如 BMI），在 `PatientData.compute_derived_fields()` 中添加逻辑，该方法在校验通过后被调用。

---

## 药物知识库开发说明

当前药物相关能力采用“双层数据源”：

- 第一层：MySQL 药物知识库
- 第二层：代码内置药物知识库 `medagent/tools/drug_db.py`

工具层统一入口仍然是：

- `get_drug_info`
- `check_contraindications`
- `check_drug_interactions`

也就是说，Agent 层不需要知道底层数据是来自 MySQL 还是内置常量。

### 相关文件

- `medagent/tools/drug_db.py`：工具层入口，负责“MySQL 优先，内置回退”
- `medagent/storage/database.py`：MySQL 引擎创建与缓存
- `medagent/storage/drug_repository.py`：数据库查询逻辑
- `scripts/schema_mysql.sql`：药物知识库表结构
- `scripts/init_drug_mysql.py`：将内置药物知识库导入 MySQL

### 查询与回退策略

当前行为约定如下：

1. 工具层先尝试读取 MySQL 药物知识库
2. 若 `MYSQL_DRUG_DB_ENABLED=false`、连接配置缺失、依赖缺失、数据库不可用或查询异常，则自动回退到内置药物知识库
3. 若 MySQL 能连接但具体药物未命中，也会继续尝试内置药物知识库

### 扩展药物数据时的建议

- 如果只是临时增加少量药物，可先补到 `DRUG_DATABASE`
- 如果希望长期维护或交由非开发者维护，优先补到 MySQL 药物知识库
- 若新增了新的禁忌症键名，需要同步更新 `check_contraindications` 的规则分支
- 若新增了别名匹配规则，应写入 `drug_aliases`，而不是在 Agent prompt 里硬编码同义词

### 初始化与刷新

本地初始化 MySQL 药物知识库：

```bash
python scripts/init_drug_mysql.py
```

该脚本会：

- 建表
- 用内置药物知识库刷新 MySQL 数据
- 重建药物相互作用记录

如果你修改了 `DRUG_DATABASE` 或 `DRUG_INTERACTIONS`，记得重新执行一次初始化脚本。

### 后台管理接口

当前已提供以下药物知识库管理接口：

- `GET /api/drugs`
- `GET /api/drugs/{id}`
- `POST /api/drugs`
- `PUT /api/drugs/{id}`
- `DELETE /api/drugs/{id}`

实现分层：

- `medagent/models/drug_admin.py`：接口输入输出模型
- `medagent/storage/drug_repository.py`：仓储层 CRUD
- `medagent/main.py`：FastAPI 路由与 HTTP 错误映射

设计约束：

- 这些接口只操作药物主记录及其子表：`aliases`、`indications`、`contraindications`、`side_effects`
- 目前不单独提供 `drug_interactions` 管理接口
- 更新药物名时，会同步更新 `drug_interactions` 里引用到该药名的记录
- 删除药物时，会同步清理 `drug_interactions` 中引用该药名的记录

错误约定：

- 记录不存在：`404`
- 药名冲突：`409`
- MySQL 药物知识库不可用：`503`

---

## Redis 会话与报告存储

当前多轮对话会话和已生成报告已迁移到 Redis，不再保存在 Python 进程内存中。

### 相关文件

- `medagent/storage/redis_client.py`：Redis 连接创建与缓存
- `medagent/storage/chat_session_repository.py`：多轮对话会话读写
- `medagent/storage/report_repository.py`：报告读写
- `medagent/main.py`：HTTP 接口层接入 Redis 存储

### 存储内容

- `POST /api/chat` 使用 Redis 存储 `GraphState`
- `POST /api/analyze` 和对话采集完成后的报告使用 Redis 存储结果字典
- `POST /api/chat` 每轮回复后会独立执行一次 `PatientData` 结构化抽取与必填校验

### Redis key 设计

- `medagent:chat:{session_id}`
- `medagent:report:{report_id}`

### 序列化方式

- 会话：`GraphState.model_dump(mode="json")` 后存为 JSON
- 报告：分析结果字典直接序列化为 JSON
- 读取时反序列化回 `GraphState` 或 `dict`

### 多轮对话完成判定

当前 chat 链路不再依赖助手在自然语言回复中主动输出 ```json。

改为：

1. 先生成正常对话回复
2. 再基于完整 `chat_history` 单独抽取 `PatientData` 结构
3. 用 `REQUIRED_FIELD_PATHS` 校验是否补齐必填字段
4. 一旦 `intake_valid=True`，立即触发 `run_analysis()` 并生成报告

### TTL 策略

- `REDIS_CHAT_TTL_SECONDS`：默认 86400 秒
- `REDIS_REPORT_TTL_SECONDS`：默认 86400 秒
- 每次读取成功后刷新 TTL，保持活跃会话和最近查看的报告

### 错误约定

- Redis 未配置、依赖缺失或连接失败：接口返回 `503`

### Docker 部署建议

- 推荐通过环境变量传入 `REDIS_URL`
- 在 Docker Compose 中可使用服务名，例如：
  `redis://:password@redis:6379`

---

## Agent 实现规范

所有 Agent 遵循统一模式，保证一致性：

```python
def run_xxx_agent(state: GraphState) -> GraphState:
    # 1. 前置检查
    if not state.patient_data:
        state.error = "XxxAgent: 缺少患者数据"
        return state

    # 2. 读提示词 + 组装上下文
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    context = {...}                          # 只放该Agent需要的数据
    user_content = f"...指令...\n\n{json.dumps(context, ensure_ascii=False, indent=2)}"

    # 3. 调用 LLM（带工具用 run_with_tools，不带工具可直接 get_llm().invoke）
    content = run_with_tools(system_prompt, user_content, TOOLS)

    # 4. 解析 → 写回 state（务必 try/except）
    try:
        state.xxx_result = XxxResult(**parse_json_response(content))
    except Exception as e:
        state.error = f"Xxx解析失败: {str(e)}"
    return state
```

**规范要点**：
- `context` 只放该Agent真正需要的字段，避免 prompt 过长拖慢速度。
- 解析必须 `try/except`，失败写 `state.error` 而非抛异常（否则中断整个工作流）。
- 提示词中明确要求"输出JSON"，并用 `parse_json_response` 容错提取（兼容 ` ```json ` 包裹）。
- 需要精确计算/查表的，**必须**在 `user_content` 中要求调用工具，不要让 LLM 自行心算。

---

## 调试技巧

### 1. 追踪工具调用

`demo.py` 中的 `patch_tool_tracing()` 给 `run_with_tools` 打补丁，实时打印每次工具调用。复制这段逻辑到任意脚本即可观察 LLM 实际调了哪些工具、传了什么参数。

### 2. 单独测试某个 Agent

```python
import json
from medagent.models.schemas import GraphState, PatientData
from medagent.agents.diagnosis import run_diagnosis_agent

with open('tests/sample_patient.json', encoding='utf-8') as f:
    pd = PatientData(**json.load(f))
gs = GraphState(patient_data=pd)
result = run_diagnosis_agent(gs)
print(result.diagnosis_result)
```

### 3. 检查工作流图结构

```python
from medagent.graph.workflow import create_app
app = create_app()
g = app.get_graph()
print("Nodes:", list(g.nodes.keys()))
print("Edges:", [(e.source, e.target) for e in g.edges])
```

### 4. 只测工具不花 LLM token

工具是纯函数，直接 `.invoke({...})` 测试，无需调 LLM。

---

## 常见坑

| 坑 | 现象 | 解决 |
|----|------|------|
| **并行节点写同一字段** | LangGraph 报 `InvalidUpdateError: Can receive only one value per step` | 每个并行节点只写自己的输出字段；共享字段需加 `Annotated[type, reducer]` |
| **工具 docstring 缺 Args** | LLM 不会调用或传错参数 | 每个参数都要在 docstring `Args:` 说明 |
| **解析未 try/except** | 单个 Agent JSON 解析失败导致整个工作流崩溃 | Agent 中所有 `parse_json_response` 必须包 try/except |
| **必填字段漏加路径** | 新增必填字段但校验没拦住 | 同步更新 `intake.py:REQUIRED_FIELD_PATHS` |
| **工具调用被截断** | 复杂病例工具没调完就出结果 | 调高 `_base.py:MAX_TOOL_ITERATIONS` |
| **禁忌症键名不匹配** | 药物有禁忌但 `check_contraindications` 没报 | 药物知识库 `contraindications` 的键必须是检查器认识的（egfr<30/severe_renal/heart_failure 等），新键需在检查器加分支 |
| **context 放了全量数据** | 单Agent响应慢、token超限 | context 只放该Agent需要的字段 |
| **模型大小写敏感** | API 报"该key不允许访问该模型" | 模型名严格匹配（如 `GPT-4.1` 而非 `gpt-4.1`） |
| **Windows 下 `uvicorn --reload` 绑定失败** | 启动时报 `WinError 10013` | 优先使用 `python -m uvicorn medagent.main:app --host 127.0.0.1 --port 8000`，确认正常后再加 `--reload`；必要时换到 `8010` 等端口 |

---

## 扩展建议（待办方向）

- **持久化**：`main.py` 的 `reports_store`/`chat_sessions` 改为 Redis/DB。
- **批量化验判读**：`interpret_lab` 改为一次传多个化验值，减少 complication agent 的工具调用往返（当前一个病例调11次）。
- **专门的预警/对策 Agent**：补全输出文档中的"预警及预测""综合性对策"两块（参考[如何新增Agent](#如何新增一个-agent)）。
- **流式输出**：API 改为 SSE，前端实时展示各 Agent 进度。
