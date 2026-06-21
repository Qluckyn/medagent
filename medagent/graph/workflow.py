"""LangGraph 工作流定义

流程:
  intake → [校验] → parallel_assessment(diagnosis + blood_sugar + insulin)
                  → complication → treatment → report

使用 TypedDict + Annotated 处理并行节点状态合并。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, StateGraph

from medagent.agents.blood_sugar import run_blood_sugar_agent
from medagent.agents.complication import run_complication_agent
from medagent.agents.diagnosis import run_diagnosis_agent
from medagent.agents.insulin_function import run_insulin_function_agent
from medagent.agents.intake import run_intake_agent
from medagent.agents.report import run_report_agent
from medagent.agents.treatment import run_treatment_agent
from medagent.models.schemas import GraphState


# ── State definition for LangGraph ──────────────────────────────────────────


def _last(a, b):
    """Reducer: keep the latest non-None value."""
    return b if b is not None else a


class WorkflowState(TypedDict, total=False):
    raw_input: Annotated[str | None, _last]
    patient_data: Annotated[dict | None, _last]
    intake_valid: Annotated[bool, _last]
    missing_fields: Annotated[list[str], _last]
    diagnosis_result: Annotated[dict | None, _last]
    blood_sugar_assessment: Annotated[dict | None, _last]
    insulin_assessment: Annotated[dict | None, _last]
    complication_assessment: Annotated[dict | None, _last]
    treatment_plan: Annotated[dict | None, _last]
    final_report: Annotated[dict | None, _last]
    error: Annotated[str | None, _last]
    chat_history: Annotated[list[dict], _last]
    conversation_mode: Annotated[bool, _last]


def _state_to_gs(state: dict) -> GraphState:
    """Convert WorkflowState dict → GraphState pydantic model."""
    from medagent.models.schemas import PatientData

    s = dict(state)
    pd = s.get("patient_data")
    if pd and isinstance(pd, dict):
        s["patient_data"] = PatientData(**pd)
    return GraphState(**{k: v for k, v in s.items() if v is not None})


def _gs_field_to_dict(val):
    if val is None:
        return None
    if hasattr(val, "model_dump"):
        return val.model_dump()
    return val


# ── Node functions ──────────────────────────────────────────────────────────


def intake_node(state: WorkflowState) -> dict:
    gs = _state_to_gs(state)
    gs = run_intake_agent(gs)
    return {
        "patient_data": _gs_field_to_dict(gs.patient_data),
        "intake_valid": gs.intake_valid,
        "missing_fields": gs.missing_fields,
        "error": gs.error,
    }


def diagnosis_node(state: WorkflowState) -> dict:
    gs = _state_to_gs(state)
    gs = run_diagnosis_agent(gs)
    return {
        "diagnosis_result": _gs_field_to_dict(gs.diagnosis_result),
    }


def blood_sugar_node(state: WorkflowState) -> dict:
    gs = _state_to_gs(state)
    gs = run_blood_sugar_agent(gs)
    return {
        "blood_sugar_assessment": _gs_field_to_dict(gs.blood_sugar_assessment),
    }


def insulin_node(state: WorkflowState) -> dict:
    gs = _state_to_gs(state)
    gs = run_insulin_function_agent(gs)
    return {
        "insulin_assessment": _gs_field_to_dict(gs.insulin_assessment),
    }


def complication_node(state: WorkflowState) -> dict:
    gs = _state_to_gs(state)
    gs = run_complication_agent(gs)
    return {
        "complication_assessment": _gs_field_to_dict(gs.complication_assessment),
    }


def treatment_node(state: WorkflowState) -> dict:
    gs = _state_to_gs(state)
    gs = run_treatment_agent(gs)
    return {
        "treatment_plan": _gs_field_to_dict(gs.treatment_plan),
    }


def report_node(state: WorkflowState) -> dict:
    gs = _state_to_gs(state)
    gs = run_report_agent(gs)
    return {
        "final_report": _gs_field_to_dict(gs.final_report),
    }


def error_node(state: WorkflowState) -> dict:
    missing = state.get("missing_fields", [])
    error_msg = state.get("error", "")
    if missing:
        error_msg = f"缺少必填字段: {', '.join(missing)}"
    return {"error": error_msg}


# ── Conditional edges ───────────────────────────────────────────────────────


def check_intake(state: WorkflowState) -> list[str]:
    """Route after intake: fan-out to 3 parallel agents, or error."""
    if state.get("intake_valid"):
        return ["diagnosis", "blood_sugar", "insulin"]
    return ["error_end"]


# ── Build the graph ─────────────────────────────────────────────────────────


def build_workflow() -> StateGraph:
    workflow = StateGraph(WorkflowState)

    workflow.add_node("intake", intake_node)
    workflow.add_node("diagnosis", diagnosis_node)
    workflow.add_node("blood_sugar", blood_sugar_node)
    workflow.add_node("insulin", insulin_node)
    workflow.add_node("complication", complication_node)
    workflow.add_node("treatment", treatment_node)
    workflow.add_node("report", report_node)
    workflow.add_node("error_end", error_node)

    workflow.set_entry_point("intake")

    # Conditional fan-out: intake → [diagnosis, blood_sugar, insulin] or error
    workflow.add_conditional_edges(
        "intake",
        check_intake,
        ["diagnosis", "blood_sugar", "insulin", "error_end"],
    )

    # Fan-in: all three → complication
    workflow.add_edge("diagnosis", "complication")
    workflow.add_edge("blood_sugar", "complication")
    workflow.add_edge("insulin", "complication")

    # Sequential tail
    workflow.add_edge("complication", "treatment")
    workflow.add_edge("treatment", "report")
    workflow.add_edge("report", END)
    workflow.add_edge("error_end", END)

    return workflow


def create_app():
    workflow = build_workflow()
    return workflow.compile()


def run_analysis(patient_data_dict: dict | None = None, raw_text: str | None = None) -> dict:
    """运行完整分析流程"""
    app = create_app()

    initial_state: WorkflowState = {
        "raw_input": None,
        "patient_data": None,
        "intake_valid": False,
        "missing_fields": [],
        "diagnosis_result": None,
        "blood_sugar_assessment": None,
        "insulin_assessment": None,
        "complication_assessment": None,
        "treatment_plan": None,
        "final_report": None,
        "error": None,
        "chat_history": [],
        "conversation_mode": False,
    }

    if patient_data_dict:
        from medagent.models.schemas import PatientData
        try:
            patient = PatientData(**patient_data_dict)
            initial_state["patient_data"] = patient.model_dump()
        except Exception:
            initial_state["raw_input"] = str(patient_data_dict)
    elif raw_text:
        initial_state["raw_input"] = raw_text

    result = app.invoke(initial_state)
    return result
