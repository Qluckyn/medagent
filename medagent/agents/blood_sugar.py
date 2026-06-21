"""血糖评估Agent"""

import json
from pathlib import Path

from medagent.agents._base import parse_json_response, run_with_tools
from medagent.models.schemas import BloodSugarAssessment, GraphState
from medagent.tools.calculators import calc_tir
from medagent.tools.guidelines import get_glucose_target

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "blood_sugar.md"

TOOLS = [calc_tir, get_glucose_target]


def run_blood_sugar_agent(state: GraphState) -> GraphState:
    if not state.patient_data:
        state.error = "血糖评估Agent: 缺少患者数据"
        return state

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    blood_sugar_data = state.patient_data.clinical_tests.blood_sugar.model_dump_json(indent=2)
    context = {
        "blood_sugar": json.loads(blood_sugar_data),
        "age": state.patient_data.age,
        "medications": state.patient_data.medications.model_dump() if state.patient_data.medications else None,
    }
    user_content = (
        "请根据以下血糖数据进行全面评估。"
        "可用工具: calc_tir(根据各时段血糖点值计算TIR/TAR/TBR)、get_glucose_target(获取个体化血糖目标)。"
        "请将所有可用的血糖读数(空腹、各餐前后、睡前)收集为列表传给 calc_tir。"
        f"最后输出JSON格式:\n\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )

    content = run_with_tools(system_prompt, user_content, TOOLS)
    try:
        result = BloodSugarAssessment(**parse_json_response(content))
        state.blood_sugar_assessment = result
    except Exception as e:
        state.error = f"血糖评估解析失败: {str(e)}"

    return state
