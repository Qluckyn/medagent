"""信息采集与校验Agent"""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from medagent.config import get_llm
from medagent.models.schemas import GraphState, PatientData

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "intake.md"

REQUIRED_FIELD_PATHS = [
    "core_symptoms.triad_symptoms",
    "core_symptoms.hypoglycemia_reaction",
    "medical_history.prior_glucose_history",
    "medical_history.steroid_diuretic_use",
    "past_history.diagnosed_diseases",
    "past_history.allergy_history",
    "physical_exam.height_cm",
    "physical_exam.weight_kg",
    "physical_exam.waist_cm",
    "physical_exam.hip_cm",
    "physical_exam.systolic_bp",
    "physical_exam.diastolic_bp",
    "physical_exam.pulse_rate",
    "clinical_tests.blood_sugar.fasting_glucose",
    "clinical_tests.blood_sugar.hba1c",
    "clinical_tests.blood_sugar.hypoglycemia_frequency",
    "clinical_tests.blood_sugar.medication_glucose_response",
    "clinical_tests.insulin.fasting_insulin",
    "clinical_tests.insulin.fasting_c_peptide",
    "clinical_tests.metabolic",
    "clinical_tests.urine.urinalysis",
    "clinical_tests.antibody.gad_antibody",
    "medications.oral_medications",
    "medications.insulin_therapy",
    "medications.glp1_therapy",
    "medications.other_medications",
    "lifestyle.diet_staple",
    "lifestyle.diet_regularity",
    "lifestyle.exercise_leisure",
    "family_history.diabetes_in_relatives",
    "family_history.other_family_diseases",
]


def _get_nested(obj: dict, path: str):
    parts = path.split(".")
    current = obj
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def validate_required_fields(data: dict) -> list[str]:
    missing = []
    for path in REQUIRED_FIELD_PATHS:
        val = _get_nested(data, path)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            missing.append(path)
    return missing


def run_intake_agent(state: GraphState) -> GraphState:
    if state.patient_data is not None:
        data_dict = state.patient_data.model_dump()
        missing = validate_required_fields(data_dict)
        if missing:
            state.intake_valid = False
            state.missing_fields = missing
        else:
            state.intake_valid = True
            state.missing_fields = []
            state.patient_data.compute_derived_fields()
        return state

    if state.raw_input:
        try:
            raw_dict = json.loads(state.raw_input)
            patient = PatientData(**raw_dict)
            state.patient_data = patient
            data_dict = patient.model_dump()
            missing = validate_required_fields(data_dict)
            if missing:
                state.intake_valid = False
                state.missing_fields = missing
            else:
                state.intake_valid = True
                state.missing_fields = []
                patient.compute_derived_fields()
            return state
        except (json.JSONDecodeError, Exception):
            pass

        llm = get_llm()
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        extraction_prompt = f"""请从以下患者信息中提取结构化数据，输出为PatientData的JSON格式。
对于无法确定的字段，填写null。

患者信息:
{state.raw_input}

请严格按照以下JSON结构输出（只输出JSON，不要其他内容）:
"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=extraction_prompt),
        ]
        response = llm.invoke(messages)
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            raw_dict = json.loads(content.strip())
            patient = PatientData(**raw_dict)
            state.patient_data = patient
            data_dict = patient.model_dump()
            missing = validate_required_fields(data_dict)
            state.intake_valid = len(missing) == 0
            state.missing_fields = missing
            if state.intake_valid:
                patient.compute_derived_fields()
        except Exception as e:
            state.error = f"信息提取失败: {str(e)}"
            state.intake_valid = False

    return state


def run_intake_chat(state: GraphState, user_message: str) -> tuple[GraphState, str]:
    """对话模式: 逐步引导采集信息"""
    llm = get_llm()
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    state.chat_history.append({"role": "user", "content": user_message})

    messages = [SystemMessage(content=system_prompt)]
    for msg in state.chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            from langchain_core.messages import AIMessage
            messages.append(AIMessage(content=msg["content"]))

    if state.missing_fields:
        missing_hint = f"\n\n当前仍缺少以下必填信息: {', '.join(state.missing_fields[:5])}"
        messages.append(HumanMessage(content=f"[系统提示]{missing_hint}，请继续引导采集。"))

    response = llm.invoke(messages)
    assistant_reply = response.content

    state.chat_history.append({"role": "assistant", "content": assistant_reply})

    if "```json" in assistant_reply:
        try:
            json_str = assistant_reply.split("```json")[1].split("```")[0]
            raw_dict = json.loads(json_str.strip())
            patient = PatientData(**raw_dict)
            state.patient_data = patient
            data_dict = patient.model_dump()
            missing = validate_required_fields(data_dict)
            state.intake_valid = len(missing) == 0
            state.missing_fields = missing
            if state.intake_valid:
                patient.compute_derived_fields()
        except Exception:
            pass

    return state, assistant_reply
