from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str

    model_config = {"from_attributes": True}


class ProjectCreate(BaseModel):
    name: str
    description: str = ""


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    model_info: dict[str, Any] | None = None
    deployment_context: dict[str, Any] | None = None
    team_info: dict[str, Any] | None = None
    governance: dict[str, Any] | None = None


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    status: str
    model_info: dict[str, Any]
    deployment_context: dict[str, Any]
    team_info: dict[str, Any]
    governance: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModulePayload(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)
    human_review_notes: str = ""
    completed: bool = False


class ModuleOut(BaseModel):
    module_type: str
    data: dict[str, Any]
    human_review_notes: str
    score: float | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class RiskResponseIn(BaseModel):
    question_id: str
    category: str
    answer: int = Field(ge=1, le=5)
    severity: int = Field(ge=1, le=5)
    likelihood: int = Field(ge=1, le=5)
    exposure: int = Field(ge=1, le=5)
    vulnerability_weight: float = Field(default=1.0, ge=1.0, le=2.0)
    mitigation_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    mitigation: str = ""
    mitigation_owner: str = ""
    rationale: str = ""
    evidence_type: str = "unknown"
    evidence_link: str = ""
    confidence: str = "medium"
    assessor: str = ""
    reviewer: str = ""


class RiskResponseOut(RiskResponseIn):
    id: str
    raw_risk: float
    residual_risk: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class StakeholderIn(BaseModel):
    name: str
    power: int = Field(default=1, ge=1, le=5)
    impact: int = Field(default=1, ge=1, le=5)
    vulnerability: bool = False
    exit_difficulty: int = Field(default=1, ge=1, le=5)
    priority: str = "suggested"
    notes: str = ""


class EngagementIn(BaseModel):
    stakeholder_group: str
    participation_method: str
    key_concerns: str = ""
    design_response: str = ""
    accepted_or_rejected: str = "pending"
    rejection_reason: str = ""
    follow_up_owner: str = ""


class InclusionPayload(BaseModel):
    stakeholders: list[StakeholderIn] = Field(default_factory=list)
    engagements: list[EngagementIn] = Field(default_factory=list)
    participation_plan: dict[str, Any] = Field(default_factory=dict)
    human_review_notes: str = ""
    completed: bool = False


class ComplianceIn(BaseModel):
    jurisdiction: str = "中国大陆"
    norm_reference: str
    requirement_summary: str
    related_questions: list[str] = Field(default_factory=list)
    evidence_required: str = ""
    status: str = "pending"
    reviewer_notes: str = ""


class LLMAuditOut(BaseModel):
    id: str
    project_id: str
    llm_task: str
    model: str
    prompt_version: str
    input_summary: str
    output: str
    human_status: str
    human_reviewer: str
    review_notes: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LLMReviewUpdate(BaseModel):
    human_status: str
    human_reviewer: str = ""
    review_notes: str = ""


class GateOut(BaseModel):
    status: str
    reasons: list[str]
    required_actions: list[str]
    unresolved_high_risks: int
    low_confidence_items: int
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    project: ProjectOut
    gate: GateOut | None
    progress: dict[str, bool]
    metrics: dict[str, int | float]
    risk_summary: list[dict[str, Any]]


class ModelTestCaseOut(BaseModel):
    id: str
    suite_id: str
    category: str
    prompt: str
    expected_behavior: str
    severity: int
    tags: list[str]
    target_group: str
    enabled: bool

    model_config = {"from_attributes": True}


class ModelTestSuiteOut(BaseModel):
    id: str
    domain: str
    name: str
    version: str
    scenario: str
    is_active: bool
    cases: list[ModelTestCaseOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ModelConnectionIn(BaseModel):
    name: str = "被测模型"
    base_url: str
    model_name: str = ""
    request_style: str = "openai_chat"
    auth_header: str = "Authorization"
    auth_scheme: str = "Bearer"
    api_key: str = ""
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class ModelConnectionOut(BaseModel):
    id: str
    project_id: str
    name: str
    base_url: str
    model_name: str
    request_style: str
    auth_header: str
    auth_scheme: str
    api_key_hint: str
    timeout_seconds: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModelTestRunIn(BaseModel):
    api_key: str = ""
    suite_id: str | None = None
    suite_name: str = "教育辅导LLM伦理红队测试"


class ModelTestResultOut(BaseModel):
    id: str
    case_id: str | None = None
    category: str
    prompt: str
    expected_behavior: str
    output: str
    risk_signal: str
    severity: int
    rationale: str
    judge_status: str
    judge_rationale: str
    human_status: str
    human_reviewer: str
    human_notes: str
    latency_ms: int
    error: str

    model_config = {"from_attributes": True}


class ModelTestRunOut(BaseModel):
    id: str
    project_id: str
    connection_id: str | None
    suite_id: str | None = None
    suite_version: str
    model_name: str
    endpoint_fingerprint: str
    status: str
    suite_name: str
    total_cases: int
    flagged_cases: int
    reviewer_status: str
    notes: str
    started_at: datetime
    completed_at: datetime | None
    results: list[ModelTestResultOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class ModelTestReviewIn(BaseModel):
    reviewer_status: str
    notes: str = ""


class ModelTestResultReviewIn(BaseModel):
    human_status: str
    human_reviewer: str = ""
    human_notes: str = ""


class EvidenceOut(BaseModel):
    id: str
    source_type: str
    source_id: str
    title: str
    summary: str
    status: str
    confidence: str
    reviewer: str
    report_section: str
    created_at: datetime

    model_config = {"from_attributes": True}
