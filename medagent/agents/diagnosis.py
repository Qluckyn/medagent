"""诊断评估Agent"""

from pathlib import Path

from medagent.agents._base import parse_json_response, run_with_tools
from medagent.models.schemas import DiagnosisResult, GraphState
from medagent.tools.drug_db import get_drug_info

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "diagnosis.md"

TOOLS = [get_drug_info]


def run_diagnosis_agent(state: GraphState) -> GraphState:
    if not state.patient_data:
        state.error = "诊断Agent: 缺少患者数据"
        return state

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    patient_json = state.patient_data.model_dump_json(indent=2)

    user_content = (
        "请根据以下患者数据进行糖尿病诊断评估。"
        "如需判断是否为药物性高血糖，可用 get_drug_info 工具查询可疑药物。"
        f"最后输出JSON格式:\n\n{patient_json}"
    )

    content = run_with_tools(system_prompt, user_content, TOOLS)
    try:
        result = DiagnosisResult(**parse_json_response(content))
        state.diagnosis_result = result
    except Exception as e:
        state.error = f"诊断评估解析失败: {str(e)}"

    return state
