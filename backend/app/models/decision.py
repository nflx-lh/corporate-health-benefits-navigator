"""Decision response models for the benefits query engine."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    employee_id: str
    question: str


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
