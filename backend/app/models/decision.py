"""Decision response models for the benefits query engine."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employee_id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Z]{2,5}\d{1,6}$")
    question: str = Field(min_length=1, max_length=500)

    @field_validator("question", mode="before")
    @classmethod
    def strip_question(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class QueryResponse(BaseModel):
    query_id: str
    employee_id: str
    decision: str = Field(description="covered | not_covered | insufficient_info")
    benefit_type: Optional[str] = None
    service_category: Optional[str] = None
    reason_summary: str
    reason_codes: list[str] = Field(default_factory=list)
    matched_rule_ids: list[str] = Field(default_factory=list)
    required_docs: list[str] = Field(default_factory=list)
    preauth_required: Optional[bool] = None
    coverage_percent: Optional[float] = None
    annual_limit_sgd: Optional[float] = None
    co_pay_sgd: Optional[float] = None
    decision_path: list[str] = Field(default_factory=list)
