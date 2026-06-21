"""治疗方案Agent"""

import json
from pathlib import Path

from medagent.agents._base import parse_json_response, run_with_tools
from medagent.models.schemas import GraphState, TreatmentPlan
from medagent.tools.drug_db import (
    check_contraindications,
    check_drug_interactions,
    get_drug_info,
)
from medagent.tools.guidelines import get_glucose_target, get_lipid_target

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "treatment.md"

TOOLS = [
    check_contraindications,
    check_drug_interactions,
    get_drug_info,
    get_glucose_target,
    get_lipid_target,
]


def run_treatment_agent(state: GraphState) -> GraphState:
    if not state.patient_data:
        state.error = "治疗Agent: 缺少患者数据"
        return state

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    context = {
        "patient_data": state.patient_data.model_dump(),
        "diagnosis": state.diagnosis_result.model_dump() if state.diagnosis_result else None,
        "blood_sugar": state.blood_sugar_assessment.model_dump() if state.blood_sugar_assessment else None,
        "insulin": state.insulin_assessment.model_dump() if state.insulin_assessment else None,
        "complication": state.complication_assessment.model_dump() if state.complication_assessment else None,
    }
    user_content = (
        "请根据以下全面评估结果制定治疗方案。"
        "制定降糖方案前，必须使用工具核实: "
        "check_contraindications(对每个拟用药物结合患者eGFR/肝功/过敏/妊娠等检查禁忌症)、"
        "check_drug_interactions(检查药物相互作用)、get_drug_info(查询药物剂量适应症)、"
        "get_glucose_target(确认个体化血糖目标)、get_lipid_target(确认血脂目标)。"
        "禁忌症分析章节必须基于 check_contraindications 的工具结果，不要凭记忆判断。"
        f"最后输出JSON格式:\n\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )

    content = run_with_tools(system_prompt, user_content, TOOLS)
    try:
        result = TreatmentPlan(**parse_json_response(content))
        state.treatment_plan = result
    except Exception as e:
        state.error = f"治疗方案解析失败: {str(e)}"

    return state
