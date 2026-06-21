"""信息采集与校验Agent"""

import json
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

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


def _extract_json_block(content: str) -> dict:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    return json.loads(text.strip())


def _extract_patient_data_dict_from_chat(state: GraphState) -> dict | None:
    """Extract a schema-shaped PatientData dict from full chat history.

    This is intentionally separate from the conversational reply so that
    report generation no longer depends on the assistant spontaneously
    returning a JSON block in normal dialogue.
    """
    if not state.chat_history:
        return None

    llm = get_llm()
    schema_json = json.dumps(PatientData.model_json_schema(), ensure_ascii=False, indent=2)
    required_json = json.dumps(REQUIRED_FIELD_PATHS, ensure_ascii=False, indent=2)
    transcript_lines = []
    for msg in state.chat_history:
        role = "用户" if msg["role"] == "user" else "助手"
        transcript_lines.append(f"{role}: {msg['content']}")
    transcript = "\n".join(transcript_lines)

    extraction_prompt = (
        "请根据以下完整对话，提取为严格符合 PatientData 结构的 JSON。\n"
        "要求：\n"
        "1. 顶层字段名必须与 PatientData schema 完全一致，不允许自定义字段名。\n"
        "2. 对于未知字段，保留字段但填 null；不要凭空猜测。\n"
        "3. 对于文本型必填字段，如果对话中没有明确信息，填空字符串。\n"
        "4. 对于数值型必填字段，如果对话中没有明确信息，填 null。\n"
        "5. 只输出 JSON，不要输出解释。\n\n"
        f"PatientData JSON Schema:\n{schema_json}\n\n"
        f"系统必填字段路径:\n{required_json}\n\n"
        f"完整对话:\n{transcript}"
    )

    messages = [
        SystemMessage(
            content=(
                "你是糖尿病病例结构化抽取器。"
                "你的唯一任务是把对话内容映射为 PatientData JSON。"
            )
        ),
        HumanMessage(content=extraction_prompt),
    ]

    response = llm.invoke(messages)
    try:
        return _extract_json_block(response.content)
    except Exception:
        return None


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
            messages.append(AIMessage(content=msg["content"]))

    if state.missing_fields:
        missing_hint = f"\n\n当前仍缺少以下必填信息: {', '.join(state.missing_fields[:5])}"
        messages.append(HumanMessage(content=f"[系统提示]{missing_hint}，请继续引导采集。"))

    response = llm.invoke(messages)
    assistant_reply = response.content

    state.chat_history.append({"role": "assistant", "content": assistant_reply})

    extracted = _extract_patient_data_dict_from_chat(state)
    if extracted is not None:
        missing = validate_required_fields(extracted)
        state.missing_fields = missing
        state.intake_valid = len(missing) == 0
        if state.intake_valid:
            try:
                patient = PatientData(**extracted)
                patient.compute_derived_fields()
                state.patient_data = patient
            except Exception:
                state.intake_valid = False
        else:
            state.patient_data = None

    return state, assistant_reply
