from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def uuid() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default="owner")
    password_hash: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="draft")
    owner_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    model_info: Mapped[dict] = mapped_column(JSON, default=dict)
    deployment_context: Mapped[dict] = mapped_column(JSON, default=dict)
    team_info: Mapped[dict] = mapped_column(JSON, default=dict)
    governance: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner = relationship("User")
    modules = relationship("ModuleResult", cascade="all, delete-orphan")
    risk_responses = relationship("RiskResponse", cascade="all, delete-orphan")


class ModuleResult(Base):
    __tablename__ = "module_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    module_type: Mapped[str] = mapped_column(String, index=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    human_review_notes: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class RiskResponse(Base):
    __tablename__ = "risk_responses"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    question_id: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[str] = mapped_column(String, index=True)
    answer: Mapped[int] = mapped_column(Integer, default=1)
    severity: Mapped[int] = mapped_column(Integer, default=1)
    likelihood: Mapped[int] = mapped_column(Integer, default=1)
    exposure: Mapped[int] = mapped_column(Integer, default=1)
    vulnerability_weight: Mapped[float] = mapped_column(Float, default=1.0)
    mitigation_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    mitigation: Mapped[str] = mapped_column(Text, default="")
    mitigation_owner: Mapped[str] = mapped_column(String, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    evidence_type: Mapped[str] = mapped_column(String, default="unknown")
    evidence_link: Mapped[str] = mapped_column(String, default="")
    confidence: Mapped[str] = mapped_column(String, default="medium")
    assessor: Mapped[str] = mapped_column(String, default="")
    reviewer: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class StakeholderGroup(Base):
    __tablename__ = "stakeholder_groups"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String)
    power: Mapped[int] = mapped_column(Integer, default=1)
    impact: Mapped[int] = mapped_column(Integer, default=1)
    vulnerability: Mapped[bool] = mapped_column(Boolean, default=False)
    exit_difficulty: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[str] = mapped_column(String, default="suggested")
    notes: Mapped[str] = mapped_column(Text, default="")


class EngagementRecord(Base):
    __tablename__ = "engagement_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    stakeholder_group: Mapped[str] = mapped_column(String)
    participation_method: Mapped[str] = mapped_column(String)
    key_concerns: Mapped[str] = mapped_column(Text, default="")
    design_response: Mapped[str] = mapped_column(Text, default="")
    accepted_or_rejected: Mapped[str] = mapped_column(String, default="pending")
    rejection_reason: Mapped[str] = mapped_column(Text, default="")
    follow_up_owner: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReviewRecord(Base):
    __tablename__ = "review_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    review_type: Mapped[str] = mapped_column(String)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    findings: Mapped[str] = mapped_column(Text, default="")
    mitigations: Mapped[str] = mapped_column(Text, default="")
    assessor: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="passed_with_conditions")


class ComplianceMapping(Base):
    __tablename__ = "compliance_mappings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    jurisdiction: Mapped[str] = mapped_column(String, default="中国大陆")
    norm_reference: Mapped[str] = mapped_column(String)
    requirement_summary: Mapped[str] = mapped_column(Text)
    related_questions: Mapped[list] = mapped_column(JSON, default=list)
    evidence_required: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="pending")
    reviewer_notes: Mapped[str] = mapped_column(Text, default="")


class LLMAuditRecord(Base):
    __tablename__ = "llm_audit_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    llm_task: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    prompt_version: Mapped[str] = mapped_column(String)
    input_summary: Mapped[str] = mapped_column(Text)
    output: Mapped[str] = mapped_column(Text)
    human_status: Mapped[str] = mapped_column(String, default="draft")
    human_reviewer: Mapped[str] = mapped_column(String, default="")
    review_notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GateDecision(Base):
    __tablename__ = "gate_decisions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    required_actions: Mapped[list] = mapped_column(JSON, default=list)
    unresolved_high_risks: Mapped[int] = mapped_column(Integer, default=0)
    low_confidence_items: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelConnection(Base):
    __tablename__ = "model_connections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String, default="被测模型")
    base_url: Mapped[str] = mapped_column(String)
    model_name: Mapped[str] = mapped_column(String, default="")
    request_style: Mapped[str] = mapped_column(String, default="openai_chat")
    auth_header: Mapped[str] = mapped_column(String, default="Authorization")
    auth_scheme: Mapped[str] = mapped_column(String, default="Bearer")
    api_key_hint: Mapped[str] = mapped_column(String, default="")
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ModelTestSuite(Base):
    __tablename__ = "model_test_suites"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    domain: Mapped[str] = mapped_column(String, default="教育")
    name: Mapped[str] = mapped_column(String)
    version: Mapped[str] = mapped_column(String, default="1.0")
    scenario: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModelTestCase(Base):
    __tablename__ = "model_test_cases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    suite_id: Mapped[str] = mapped_column(String, ForeignKey("model_test_suites.id"), index=True)
    category: Mapped[str] = mapped_column(String, index=True)
    prompt: Mapped[str] = mapped_column(Text)
    expected_behavior: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[int] = mapped_column(Integer, default=1)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    target_group: Mapped[str] = mapped_column(String, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)


class ModelTestRun(Base):
    __tablename__ = "model_test_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    connection_id: Mapped[str | None] = mapped_column(String, ForeignKey("model_connections.id"), nullable=True)
    suite_id: Mapped[str | None] = mapped_column(String, ForeignKey("model_test_suites.id"), nullable=True)
    suite_version: Mapped[str] = mapped_column(String, default="1.0")
    model_name: Mapped[str] = mapped_column(String, default="")
    endpoint_fingerprint: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="completed")
    suite_name: Mapped[str] = mapped_column(String, default="伦理红队基础测试")
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    flagged_cases: Mapped[int] = mapped_column(Integer, default=0)
    reviewer_status: Mapped[str] = mapped_column(String, default="draft")
    notes: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ModelTestResult(Base):
    __tablename__ = "model_test_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    run_id: Mapped[str] = mapped_column(String, ForeignKey("model_test_runs.id"), index=True)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    case_id: Mapped[str | None] = mapped_column(String, ForeignKey("model_test_cases.id"), nullable=True)
    category: Mapped[str] = mapped_column(String, index=True)
    prompt: Mapped[str] = mapped_column(Text)
    expected_behavior: Mapped[str] = mapped_column(Text, default="")
    output: Mapped[str] = mapped_column(Text, default="")
    risk_signal: Mapped[str] = mapped_column(String, default="unknown")
    severity: Mapped[int] = mapped_column(Integer, default=1)
    rationale: Mapped[str] = mapped_column(Text, default="")
    judge_status: Mapped[str] = mapped_column(String, default="not_requested")
    judge_rationale: Mapped[str] = mapped_column(Text, default="")
    human_status: Mapped[str] = mapped_column(String, default="draft")
    human_reviewer: Mapped[str] = mapped_column(String, default="")
    human_notes: Mapped[str] = mapped_column(Text, default="")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    project_id: Mapped[str] = mapped_column(String, ForeignKey("projects.id"), index=True)
    source_type: Mapped[str] = mapped_column(String, index=True)
    source_id: Mapped[str] = mapped_column(String, default="")
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="draft")
    confidence: Mapped[str] = mapped_column(String, default="medium")
    reviewer: Mapped[str] = mapped_column(String, default="")
    report_section: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
