"""并发症与合并症评估Agent"""

import json
from pathlib import Path

from medagent.agents._base import parse_json_response, run_with_tools
from medagent.models.schemas import ComplicationAssessment, GraphState
from medagent.tools.calculators import calc_egfr
from medagent.tools.guidelines import classify_ckd_stage, classify_dr_stage, get_bp_target
from medagent.tools.lab_interpreter import interpret_lab

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "complication.md"

TOOLS = [calc_egfr, classify_ckd_stage, classify_dr_stage, get_bp_target, interpret_lab]


def run_complication_agent(state: GraphState) -> GraphState:
    if not state.patient_data:
        state.error = "并发症Agent: 缺少患者数据"
        return state

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    context = {
        "physical_exam": state.patient_data.physical_exam.model_dump(),
        "clinical_tests": state.patient_data.clinical_tests.model_dump(),
        "past_history": state.patient_data.past_history.model_dump(),
        "diagnosis": state.diagnosis_result.model_dump() if state.diagnosis_result else None,
        "age": state.patient_data.age,
        "gender": state.patient_data.gender,
    }
    user_content = (
        "请根据以下数据评估并发症和合并症。"
        "可用工具: calc_egfr(计算肾小球滤过率)、classify_ckd_stage(CKD分期与风险)、"
        "classify_dr_stage(视网膜病变分级)、get_bp_target(血压目标)、"
        "interpret_lab(判读化验值:fasting_glucose/hba1c/triglycerides/ldl_cholesterol/hdl_cholesterol/alt/ast/creatinine/uric_acid/uacr)。"
        "eGFR必须用 calc_egfr 工具从肌酐重新计算(CKD-EPI公式)作为准绳，若录入的eGFR与计算值不一致，以工具计算值为准并在结论中说明。"
        "然后用 classify_ckd_stage 传入计算所得eGFR做分期。"
        "请用工具判读每一项异常化验值，不要自行估算。"
        f"最后输出JSON格式:\n\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )

    content = run_with_tools(system_prompt, user_content, TOOLS)
    try:
        result = ComplicationAssessment(**parse_json_response(content))
        state.complication_assessment = result
    except Exception as e:
        state.error = f"并发症评估解析失败: {str(e)}"

    return state
