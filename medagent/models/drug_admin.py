"""Pydantic models for drug knowledge base management APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DrugPayload(BaseModel):
    """Editable drug knowledge base payload."""

    name: str = Field(..., min_length=1, description="药物名称")
    category: str = Field("", description="药物分类")
    aliases: list[str] = Field(default_factory=list, description="药物别名列表")
    indications: list[str] = Field(default_factory=list, description="适应症列表")
    contraindications: dict[str, str] = Field(
        default_factory=dict,
        description="禁忌症规则，键为规则名，值为说明文本",
    )
    dose_range: str = Field("", description="剂量范围")
    side_effects: list[str] = Field(default_factory=list, description="主要不良反应列表")
    notes: str = Field("", description="备注")


class DrugRecord(DrugPayload):
    """Drug record returned by the management API."""

    id: int = Field(..., description="药物主键 ID")


class DrugDeleteResponse(BaseModel):
    """Delete response payload."""

    id: int = Field(..., description="已删除药物 ID")
    deleted: bool = Field(..., description="是否删除成功")

