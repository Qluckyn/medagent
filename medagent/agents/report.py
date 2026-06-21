"""报告生成Agent"""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from medagent.config import get_llm
from medagent.models.schemas import (
    ComprehensiveStrategy,
    GraphState,
    MedicalReport,
    TreatmentPlan,
    WarningPrediction,
)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "report.md"


def run_report_agent(state: GraphState) -> GraphState:
    llm = get_llm()
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    context = {
        "patient_info": {
            "id": state.patient_data.patient_id if state.patient_data else None,
            "name": state.patient_data.patient_name if state.patient_data else None,
            "age": state.patient_data.age if state.patient_data else None,
            "gender": state.patient_data.gender if state.patient_data else None,
        },
        "diagnosis": state.diagnosis_result.model_dump() if state.diagnosis_result else None,
        "blood_sugar": state.blood_sugar_assessment.model_dump() if state.blood_sugar_assessment else None,
        "insulin": state.insulin_assessment.model_dump() if state.insulin_assessment else None,
        "complication": state.complication_assessment.model_dump() if state.complication_assessment else None,
        "treatment": state.treatment_plan.model_dump() if state.treatment_plan else None,
    }

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                "请汇总以下所有评估结果，生成完整的糖尿病诊疗报告。\n"
                "同时输出两种格式:\n"
                "1. 结构化JSON (MedicalReport)\n"
                "2. 格式化文本报告\n\n"
                "请先输出JSON（用```json包裹），然后输出文本报告（用```text包裹）。\n\n"
                f"评估数据:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
            )
        ),
    ]

    response = llm.invoke(messages)
    content = response.content

    try:
        report = MedicalReport(
            patient_id=state.patient_data.patient_id if state.patient_data else None,
            patient_name=state.patient_data.patient_name if state.patient_data else None,
            diagnosis=state.diagnosis_result,
            blood_sugar_assessment=state.blood_sugar_assessment,
            insulin_assessment=state.insulin_assessment,
            complication_assessment=state.complication_assessment,
            treatment_plan=state.treatment_plan,
        )

        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0]
            extra = json.loads(json_str.strip())
            if "warning_prediction" in extra and extra["warning_prediction"]:
                report.warning_prediction = WarningPrediction(**extra["warning_prediction"])
            if "comprehensive_strategy" in extra and extra["comprehensive_strategy"]:
                report.comprehensive_strategy = ComprehensiveStrategy(**extra["comprehensive_strategy"])

        state.final_report = report
    except Exception as e:
        if state.diagnosis_result and state.treatment_plan:
            state.final_report = MedicalReport(
                patient_id=state.patient_data.patient_id if state.patient_data else None,
                patient_name=state.patient_data.patient_name if state.patient_data else None,
                diagnosis=state.diagnosis_result,
                blood_sugar_assessment=state.blood_sugar_assessment,
                insulin_assessment=state.insulin_assessment,
                complication_assessment=state.complication_assessment,
                treatment_plan=state.treatment_plan,
            )
        else:
            state.error = f"报告生成失败: {str(e)}"

    return state
