"""MedAgent - 糖尿病诊疗智能Agent系统 FastAPI入口"""

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from medagent.agents.intake import run_intake_chat
from medagent.graph.workflow import run_analysis
from medagent.models.drug_admin import DrugDeleteResponse, DrugPayload, DrugRecord
from medagent.models.schemas import GraphState, MedicalReport, PatientData
from medagent.storage.chat_session_repository import get_chat_session, save_chat_session
from medagent.storage.drug_repository import (
    DrugConflictError,
    DrugNotFoundError,
    create_drug,
    delete_drug,
    get_drug_by_id,
    list_drugs,
    update_drug,
)
from medagent.storage.report_repository import get_report as get_report_by_id, save_report


# ── App ─────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(
    title="MedAgent - 糖尿病诊疗智能Agent系统",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request/Response models ─────────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    patient_data: dict | None = None
    raw_text: str | None = None


class AnalyzeResponse(BaseModel):
    report_id: str
    success: bool
    error: str | None = None
    report: dict | None = None
    missing_fields: list[str] | None = None


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    intake_complete: bool
    missing_fields: list[str] | None = None
    report_id: str | None = None


def _handle_drug_repo_error(exc: Exception) -> None:
    if isinstance(exc, DrugNotFoundError):
        raise HTTPException(status_code=404, detail="药物不存在") from exc
    if isinstance(exc, DrugConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if isinstance(exc, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail="MySQL药物知识库不可用，请检查数据库配置与连接",
        ) from exc
    raise exc


def _handle_redis_error(exc: Exception) -> None:
    if isinstance(exc, RuntimeError):
        raise HTTPException(
            status_code=503,
            detail="Redis不可用，请检查REDIS_URL配置与连接",
        ) from exc
    raise exc


# ── Endpoints ───────────────────────────────────────────────────────────────


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    """结构化JSON输入 → 完整分析报告"""
    if not req.patient_data and not req.raw_text:
        raise HTTPException(400, "必须提供patient_data或raw_text")

    result = run_analysis(
        patient_data_dict=req.patient_data,
        raw_text=req.raw_text,
    )

    report_id = str(uuid.uuid4())[:8]
    try:
        save_report(report_id, result)
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_redis_error(exc)

    if result.get("error") and not result.get("final_report"):
        return AnalyzeResponse(
            report_id=report_id,
            success=False,
            error=result["error"],
            missing_fields=result.get("missing_fields"),
        )

    return AnalyzeResponse(
        report_id=report_id,
        success=True,
        report=result.get("final_report"),
    )


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """对话模式: 逐步采集患者信息"""
    session_id = req.session_id or str(uuid.uuid4())[:8]

    try:
        state = get_chat_session(session_id)
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_redis_error(exc)

    if state is None:
        state = GraphState(conversation_mode=True)

    state, reply = run_intake_chat(state, req.message)
    try:
        save_chat_session(session_id, state)
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_redis_error(exc)

    if state.intake_valid and state.patient_data:
        result = run_analysis(patient_data_dict=state.patient_data.model_dump())
        report_id = str(uuid.uuid4())[:8]
        try:
            save_report(report_id, result)
        except Exception as exc:  # pragma: no cover - thin HTTP mapping
            _handle_redis_error(exc)

        return ChatResponse(
            session_id=session_id,
            reply=reply + "\n\n✅ 信息采集完成，已生成诊疗报告。",
            intake_complete=True,
            report_id=report_id,
        )

    return ChatResponse(
        session_id=session_id,
        reply=reply,
        intake_complete=False,
        missing_fields=state.missing_fields if state.missing_fields else None,
    )


@app.get("/api/report/{report_id}")
def get_report(report_id: str):
    """获取已生成的报告"""
    try:
        report = get_report_by_id(report_id)
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_redis_error(exc)

    if report is None:
        raise HTTPException(404, "报告不存在")
    return report


@app.get("/api/schema")
def get_schema():
    """获取PatientData的JSON Schema（含必填字段标注）"""
    return PatientData.model_json_schema()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "medagent"}


@app.get("/api/drugs", response_model=list[DrugRecord])
def get_drugs():
    """获取药物知识库列表。"""
    try:
        return list_drugs()
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_drug_repo_error(exc)


@app.get("/api/drugs/{drug_id}", response_model=DrugRecord)
def get_drug(drug_id: int):
    """获取单个药物详情。"""
    try:
        return get_drug_by_id(drug_id)
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_drug_repo_error(exc)


@app.post("/api/drugs", response_model=DrugRecord, status_code=status.HTTP_201_CREATED)
def create_drug_endpoint(payload: DrugPayload):
    """创建药物记录。"""
    try:
        return create_drug(payload.model_dump())
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_drug_repo_error(exc)


@app.put("/api/drugs/{drug_id}", response_model=DrugRecord)
def update_drug_endpoint(drug_id: int, payload: DrugPayload):
    """完整更新药物记录。"""
    try:
        return update_drug(drug_id, payload.model_dump())
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_drug_repo_error(exc)


@app.delete("/api/drugs/{drug_id}", response_model=DrugDeleteResponse)
def delete_drug_endpoint(drug_id: int):
    """删除药物记录。"""
    try:
        delete_drug(drug_id)
    except Exception as exc:  # pragma: no cover - thin HTTP mapping
        _handle_drug_repo_error(exc)
    return DrugDeleteResponse(id=drug_id, deleted=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("medagent.main:app", host="0.0.0.0", port=8000, reload=True)
