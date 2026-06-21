"""胰岛素功能评估Agent"""

import json
from pathlib import Path

from medagent.agents._base import parse_json_response, run_with_tools
from medagent.models.schemas import GraphState, InsulinFunctionAssessment
from medagent.tools.calculators import calc_homa_beta, calc_homa_ir

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "insulin_function.md"

TOOLS = [calc_homa_ir, calc_homa_beta]


def run_insulin_function_agent(state: GraphState) -> GraphState:
    if not state.patient_data:
        state.error = "胰岛素功能Agent: 缺少患者数据"
        return state

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    insulin_data = state.patient_data.clinical_tests.insulin.model_dump_json(indent=2)
    context = {
        "insulin": json.loads(insulin_data),
        "fasting_glucose": state.patient_data.clinical_tests.blood_sugar.fasting_glucose,
        "age": state.patient_data.age,
        "bmi": state.patient_data.physical_exam.bmi,
    }
    user_content = (
        "请根据以下胰岛素和C肽数据评估胰岛功能。"
        "必须调用 calc_homa_ir 和 calc_homa_beta 工具进行精确计算，不要自行心算。"
        f"最后输出JSON格式:\n\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )

    content = run_with_tools(system_prompt, user_content, TOOLS)
    try:
        result = InsulinFunctionAssessment(**parse_json_response(content))
        state.insulin_assessment = result
    except Exception as e:
        state.error = f"胰岛素功能评估解析失败: {str(e)}"

    return state
