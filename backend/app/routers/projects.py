from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from ..auth import get_current_user, require_roles
from ..catalog import COMPLIANCE_TEMPLATES, MONITORING_TEMPLATES, REFLEXIVITY_QUESTIONS, RISK_QUESTIONS
from ..database import get_db
from ..models import (
    ComplianceMapping,
    EngagementRecord,
    EvidenceItem,
    GateDecision,
    LLMAuditRecord,
    ModelConnection,
    ModelTestCase,
    ModelTestResult,
    ModelTestRun,
    ModelTestSuite,
    ModuleResult,
    Project,
    RiskResponse,
    StakeholderGroup,
    User,
)
from ..schemas import (
    ComplianceIn,
    DashboardOut,
    GateOut,
    EvidenceOut,
    InclusionPayload,
    LLMAuditOut,
    LLMReviewUpdate,
    ModelConnectionIn,
    ModelConnectionOut,
    ModelTestResultReviewIn,
    ModelTestReviewIn,
    ModelTestRunIn,
    ModelTestRunOut,
    ModelTestSuiteOut,
    ModuleOut,
    ModulePayload,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    RiskResponseIn,
    RiskResponseOut,
)
from ..services.llm import judge_model_test_result, run_llm_task
from ..services.audit import record_system_audit
from ..services.report import latest_gate, project_html, project_markdown
from ..services.risk import evaluate_gate, raw_risk, residual_risk, risk_summary
from ..services.model_testing import create_evidence_for_result, mask_key, run_model_tests, seed_default_suite


router = APIRouter(prefix="/api/projects", tags=["projects"])


def get_project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def risk_out(row: RiskResponse) -> RiskResponseOut:
    return RiskResponseOut(
        id=row.id,
        question_id=row.question_id,
        category=row.category,
        answer=row.answer,
        severity=row.severity,
        likelihood=row.likelihood,
        exposure=row.exposure,
        vulnerability_weight=row.vulnerability_weight,
        mitigation_confidence=row.mitigation_confidence,
        mitigation=row.mitigation,
        mitigation_owner=row.mitigation_owner,
        rationale=row.rationale,
        evidence_type=row.evidence_type,
        evidence_link=row.evidence_link,
        confidence=row.confidence,
        assessor=row.assessor,
        reviewer=row.reviewer,
        raw_risk=raw_risk(row),
        residual_risk=residual_risk(row),
        updated_at=row.updated_at,
    )


def module_for(db: Session, project_id: str, module_type: str) -> ModuleResult:
    module = (
        db.query(ModuleResult)
        .filter(ModuleResult.project_id == project_id, ModuleResult.module_type == module_type)
        .first()
    )
    if not module:
        module = ModuleResult(project_id=project_id, module_type=module_type, data={})
        db.add(module)
        db.commit()
        db.refresh(module)
    return module


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[Project]:
    query = db.query(Project).order_by(Project.updated_at.desc())
    if user.role != "admin":
        query = query.filter(Project.owner_id == user.id)
    return query.all()


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(require_roles("owner"))) -> Project:
    project = Project(name=payload.name, description=payload.description, owner_id=user.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    for item in COMPLIANCE_TEMPLATES:
        db.add(ComplianceMapping(project_id=project.id, status="pending", reviewer_notes="", **item))
    db.commit()
    record_system_audit(db, project.id, "project_created", f"用户 {user.email} 创建项目 {project.name}")
    db.commit()
    return project


@router.get("/{project_id}/dashboard", response_model=DashboardOut)
def dashboard(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> DashboardOut:
    project = get_project_or_404(db, project_id)
    gate = latest_gate(db, project_id)
    completed = {m.module_type: bool(m.completed_at) for m in project.modules}
    risks = db.query(RiskResponse).filter(RiskResponse.project_id == project_id).all()
    metrics = {
        "high_risks": sum(1 for r in risks if residual_risk(r) >= 35),
        "low_confidence": sum(1 for r in risks if r.confidence == "low"),
        "stakeholders": db.query(StakeholderGroup).filter(StakeholderGroup.project_id == project_id).count(),
        "audits_draft": db.query(LLMAuditRecord).filter(LLMAuditRecord.project_id == project_id, LLMAuditRecord.human_status == "draft").count(),
        "model_test_runs": db.query(ModelTestRun).filter(ModelTestRun.project_id == project_id).count(),
    }
    return DashboardOut(
        project=project,
        gate=gate,
        progress={m: completed.get(m, False) for m in ["anticipation", "reflexivity", "inclusion", "responsiveness"]},
        metrics=metrics,
        risk_summary=risk_summary(db, project_id),
    )


@router.get("/{project_id}/setup", response_model=ProjectOut)
def get_setup(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Project:
    return get_project_or_404(db, project_id)


@router.patch("/{project_id}/setup", response_model=ProjectOut)
def patch_setup(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "technical_assessor"))) -> Project:
    return update_project(project_id, payload, db, _)


@router.get("/{project_id}/catalog")
def catalog(_: str = Depends(get_current_user)):
    return {
        "risk_questions": RISK_QUESTIONS,
        "reflexivity_questions": REFLEXIVITY_QUESTIONS,
        "monitoring_templates": MONITORING_TEMPLATES,
        "compliance_templates": COMPLIANCE_TEMPLATES,
    }


@router.get("/{project_id}/modules/{module_type}", response_model=ModuleOut)
def get_module(project_id: str, module_type: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> ModuleResult:
    if module_type not in {"anticipation", "reflexivity", "responsiveness"}:
        raise HTTPException(status_code=404, detail="未知模块")
    get_project_or_404(db, project_id)
    return module_for(db, project_id, module_type)


@router.patch("/{project_id}/modules/{module_type}", response_model=ModuleOut)
def patch_module(project_id: str, module_type: str, payload: ModulePayload, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "technical_assessor", "ethics_reviewer"))) -> ModuleResult:
    if module_type not in {"anticipation", "reflexivity", "responsiveness"}:
        raise HTTPException(status_code=404, detail="未知模块")
    get_project_or_404(db, project_id)
    module = module_for(db, project_id, module_type)
    module.data = payload.data
    module.human_review_notes = payload.human_review_notes
    module.completed_at = datetime.now(timezone.utc) if payload.completed else None
    db.commit()
    db.refresh(module)
    record_system_audit(db, project_id, f"{module_type}_updated", f"用户 {_.email} 更新 {module_type} 模块")
    db.commit()
    return module


@router.get("/{project_id}/anticipation", response_model=ModuleOut)
def get_anticipation(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ModuleResult:
    return get_module(project_id, "anticipation", db, user)


@router.patch("/{project_id}/anticipation", response_model=ModuleOut)
def patch_anticipation(project_id: str, payload: ModulePayload, db: Session = Depends(get_db), user: User = Depends(require_roles("owner", "technical_assessor", "ethics_reviewer"))) -> ModuleResult:
    return patch_module(project_id, "anticipation", payload, db, user)


@router.get("/{project_id}/reflexivity", response_model=ModuleOut)
def get_reflexivity(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ModuleResult:
    return get_module(project_id, "reflexivity", db, user)


@router.patch("/{project_id}/reflexivity", response_model=ModuleOut)
def patch_reflexivity(project_id: str, payload: ModulePayload, db: Session = Depends(get_db), user: User = Depends(require_roles("owner", "technical_assessor", "ethics_reviewer"))) -> ModuleResult:
    return patch_module(project_id, "reflexivity", payload, db, user)


@router.get("/{project_id}/responsiveness", response_model=ModuleOut)
def get_responsiveness(project_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> ModuleResult:
    return get_module(project_id, "responsiveness", db, user)


@router.patch("/{project_id}/responsiveness", response_model=ModuleOut)
def patch_responsiveness(project_id: str, payload: ModulePayload, db: Session = Depends(get_db), user: User = Depends(require_roles("owner", "technical_assessor", "ethics_reviewer"))) -> ModuleResult:
    return patch_module(project_id, "responsiveness", payload, db, user)


@router.get("/{project_id}/anticipation/risks", response_model=list[RiskResponseOut])
def list_risks(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[RiskResponseOut]:
    get_project_or_404(db, project_id)
    return [risk_out(row) for row in db.query(RiskResponse).filter(RiskResponse.project_id == project_id).all()]


@router.post("/{project_id}/anticipation/risks", response_model=RiskResponseOut)
def upsert_risk(project_id: str, payload: RiskResponseIn, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "technical_assessor"))) -> RiskResponseOut:
    get_project_or_404(db, project_id)
    row = (
        db.query(RiskResponse)
        .filter(RiskResponse.project_id == project_id, RiskResponse.question_id == payload.question_id)
        .first()
    )
    if not row:
        row = RiskResponse(project_id=project_id, question_id=payload.question_id, category=payload.category)
        db.add(row)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    record_system_audit(db, project_id, "risk_upserted", f"用户 {_.email} 保存风险项 {row.question_id}", f"剩余风险 {residual_risk(row):.1f}")
    db.commit()
    return risk_out(row)


@router.get("/{project_id}/inclusion")
def get_inclusion(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    get_project_or_404(db, project_id)
    module = module_for(db, project_id, "inclusion")
    return jsonable_encoder({
        "module": module,
        "stakeholders": db.query(StakeholderGroup).filter(StakeholderGroup.project_id == project_id).all(),
        "engagements": db.query(EngagementRecord).filter(EngagementRecord.project_id == project_id).all(),
    })


@router.patch("/{project_id}/inclusion")
def patch_inclusion(project_id: str, payload: InclusionPayload, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "ethics_reviewer"))) -> dict:
    get_project_or_404(db, project_id)
    db.query(StakeholderGroup).filter(StakeholderGroup.project_id == project_id).delete()
    db.query(EngagementRecord).filter(EngagementRecord.project_id == project_id).delete()
    for item in payload.stakeholders:
        db.add(StakeholderGroup(project_id=project_id, **item.model_dump()))
    for item in payload.engagements:
        db.add(EngagementRecord(project_id=project_id, **item.model_dump()))
    module = module_for(db, project_id, "inclusion")
    module.data = {"participation_plan": payload.participation_plan}
    module.human_review_notes = payload.human_review_notes
    module.completed_at = datetime.now(timezone.utc) if payload.completed else None
    record_system_audit(db, project_id, "inclusion_updated", f"用户 {_.email} 更新包容模块")
    db.commit()
    return get_inclusion(project_id, db, _)


@router.get("/{project_id}/compliance")
def get_compliance(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    get_project_or_404(db, project_id)
    return db.query(ComplianceMapping).filter(ComplianceMapping.project_id == project_id).all()


@router.patch("/{project_id}/compliance")
def patch_compliance(project_id: str, payload: list[ComplianceIn], db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "ethics_reviewer"))) -> dict:
    get_project_or_404(db, project_id)
    db.query(ComplianceMapping).filter(ComplianceMapping.project_id == project_id).delete()
    for item in payload:
        db.add(ComplianceMapping(project_id=project_id, **item.model_dump()))
    record_system_audit(db, project_id, "compliance_updated", f"用户 {_.email} 更新法规映射")
    db.commit()
    return {"ok": True}


@router.post("/{project_id}/llm/{task}", response_model=LLMAuditOut)
def llm_task(project_id: str, task: str, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "technical_assessor", "ethics_reviewer"))) -> LLMAuditRecord:
    project = get_project_or_404(db, project_id)
    if task not in {"scenarios", "blindspots", "participation", "report_narrative"}:
        raise HTTPException(status_code=404, detail="未知LLM任务")
    return run_llm_task(db, project, task)


@router.patch("/{project_id}/audit-log/{audit_id}", response_model=LLMAuditOut)
def update_audit(project_id: str, audit_id: str, payload: LLMReviewUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "ethics_reviewer"))) -> LLMAuditRecord:
    audit = db.get(LLMAuditRecord, audit_id)
    if not audit or audit.project_id != project_id:
        raise HTTPException(status_code=404, detail="审计记录不存在")
    audit.human_status = payload.human_status
    audit.human_reviewer = payload.human_reviewer
    audit.review_notes = payload.review_notes
    db.commit()
    db.refresh(audit)
    return audit


@router.post("/{project_id}/gate/evaluate", response_model=GateOut)
def gate(project_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "ethics_reviewer"))) -> GateDecision:
    decision = evaluate_gate(db, get_project_or_404(db, project_id))
    record_system_audit(db, project_id, "gate_evaluated", f"用户 {_.email} 执行门禁评估", decision.status)
    db.commit()
    return decision


@router.get("/{project_id}/report/markdown")
def report_markdown(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Response:
    markdown = project_markdown(db, get_project_or_404(db, project_id))
    return Response(content=markdown, media_type="text/markdown; charset=utf-8")


@router.get("/{project_id}/report/html")
def report_html(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Response:
    html = project_html(db, get_project_or_404(db, project_id))
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.get("/{project_id}/audit-log", response_model=list[LLMAuditOut])
def audit_log(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[LLMAuditRecord]:
    get_project_or_404(db, project_id)
    return (
        db.query(LLMAuditRecord)
        .filter(LLMAuditRecord.project_id == project_id)
        .order_by(LLMAuditRecord.created_at.desc())
        .all()
    )


@router.get("/{project_id}/evidence", response_model=list[EvidenceOut])
def evidence_center(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[EvidenceItem]:
    get_project_or_404(db, project_id)
    return (
        db.query(EvidenceItem)
        .filter(EvidenceItem.project_id == project_id)
        .order_by(EvidenceItem.created_at.desc())
        .all()
    )


def suite_out(db: Session, suite: ModelTestSuite) -> ModelTestSuiteOut:
    cases = db.query(ModelTestCase).filter(ModelTestCase.suite_id == suite.id).order_by(ModelTestCase.category.asc()).all()
    return ModelTestSuiteOut.model_validate({**suite.__dict__, "cases": cases})


@router.get("/{project_id}/test-suites", response_model=list[ModelTestSuiteOut])
def list_test_suites(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ModelTestSuiteOut]:
    get_project_or_404(db, project_id)
    seed_default_suite(db)
    suites = db.query(ModelTestSuite).filter(ModelTestSuite.is_active.is_(True)).order_by(ModelTestSuite.created_at.desc()).all()
    return [suite_out(db, suite) for suite in suites]


def test_run_out(db: Session, run: ModelTestRun) -> ModelTestRunOut:
    results = db.query(ModelTestResult).filter(ModelTestResult.run_id == run.id).all()
    return ModelTestRunOut.model_validate({**run.__dict__, "results": results})


@router.get("/{project_id}/model-connection", response_model=ModelConnectionOut | None)
def get_model_connection(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    get_project_or_404(db, project_id)
    return db.query(ModelConnection).filter(ModelConnection.project_id == project_id).order_by(ModelConnection.updated_at.desc()).first()


@router.patch("/{project_id}/model-connection", response_model=ModelConnectionOut)
def save_model_connection(project_id: str, payload: ModelConnectionIn, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "technical_assessor"))):
    get_project_or_404(db, project_id)
    connection = db.query(ModelConnection).filter(ModelConnection.project_id == project_id).first()
    if not connection:
        connection = ModelConnection(project_id=project_id, base_url=payload.base_url)
        db.add(connection)
    connection.name = payload.name
    connection.base_url = payload.base_url
    connection.model_name = payload.model_name
    connection.request_style = payload.request_style
    connection.auth_header = payload.auth_header
    connection.auth_scheme = payload.auth_scheme
    connection.api_key_hint = mask_key(payload.api_key)
    connection.timeout_seconds = payload.timeout_seconds
    record_system_audit(db, project_id, "model_connection_saved", f"用户 {_.email} 保存被测模型连接", f"{connection.request_style} {connection.base_url}")
    db.commit()
    db.refresh(connection)
    return connection


@router.post("/{project_id}/model-tests/run", response_model=ModelTestRunOut)
def run_model_test_suite(project_id: str, payload: ModelTestRunIn, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "technical_assessor", "ethics_reviewer"))):
    get_project_or_404(db, project_id)
    connection = db.query(ModelConnection).filter(ModelConnection.project_id == project_id).first()
    if not connection:
        raise HTTPException(status_code=400, detail="请先配置被测模型 URL 和请求格式")
    run = run_model_tests(db, project_id, connection, payload.api_key, payload.suite_id, payload.suite_name)
    record_system_audit(db, project_id, "model_tests_run", f"用户 {_.email} 运行模型实测", f"{run.flagged_cases}/{run.total_cases} 需复核")
    db.commit()
    return test_run_out(db, run)


@router.get("/{project_id}/model-tests", response_model=list[ModelTestRunOut])
def list_model_tests(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    get_project_or_404(db, project_id)
    runs = db.query(ModelTestRun).filter(ModelTestRun.project_id == project_id).order_by(ModelTestRun.started_at.desc()).all()
    return [test_run_out(db, run) for run in runs]


@router.get("/{project_id}/model-tests/{run_id}", response_model=ModelTestRunOut)
def get_model_test(project_id: str, run_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    run = db.get(ModelTestRun, run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="模型实测记录不存在")
    return test_run_out(db, run)


@router.patch("/{project_id}/model-tests/{run_id}/review", response_model=ModelTestRunOut)
def review_model_test(project_id: str, run_id: str, payload: ModelTestReviewIn, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "ethics_reviewer"))):
    run = db.get(ModelTestRun, run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="模型实测记录不存在")
    run.reviewer_status = payload.reviewer_status
    run.notes = payload.notes
    record_system_audit(db, project_id, "model_tests_reviewed", f"用户 {_.email} 复核模型实测", payload.reviewer_status)
    db.commit()
    db.refresh(run)
    return test_run_out(db, run)


@router.patch("/{project_id}/model-tests/{run_id}/results/{result_id}/review", response_model=ModelTestRunOut)
def review_model_test_result(project_id: str, run_id: str, result_id: str, payload: ModelTestResultReviewIn, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "ethics_reviewer"))):
    run = db.get(ModelTestRun, run_id)
    result = db.get(ModelTestResult, result_id)
    if not run or run.project_id != project_id or not result or result.run_id != run_id:
        raise HTTPException(status_code=404, detail="模型实测结果不存在")
    if payload.human_status not in {"accepted", "revised", "rejected", "draft"}:
        raise HTTPException(status_code=400, detail="人工状态必须是 accepted、revised、rejected 或 draft")
    result.human_status = payload.human_status
    result.human_reviewer = payload.human_reviewer or _.name
    result.human_notes = payload.human_notes
    create_evidence_for_result(db, result)
    remaining_draft = (
        db.query(ModelTestResult)
        .filter(ModelTestResult.run_id == run_id, ModelTestResult.human_status == "draft")
        .count()
    )
    if remaining_draft == 0:
        statuses = {row.human_status for row in db.query(ModelTestResult).filter(ModelTestResult.run_id == run_id).all()}
        run.reviewer_status = "revised" if "revised" in statuses else "accepted"
    record_system_audit(db, project_id, "model_test_result_reviewed", f"用户 {_.email} 复核模型实测结果 {result.category}", result.human_status)
    db.commit()
    db.refresh(run)
    return test_run_out(db, run)


@router.post("/{project_id}/model-tests/{run_id}/judge", response_model=ModelTestRunOut)
def judge_model_test_run(project_id: str, run_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "technical_assessor", "ethics_reviewer"))):
    project = get_project_or_404(db, project_id)
    run = db.get(ModelTestRun, run_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="模型实测记录不存在")
    results = db.query(ModelTestResult).filter(ModelTestResult.run_id == run_id).all()
    for result in results:
        judge_model_test_result(db, project, result)
    record_system_audit(db, project_id, "model_tests_judged", f"用户 {_.email} 请求LLM辅助评审模型实测", f"{len(results)} 条草稿")
    db.commit()
    return test_run_out(db, run)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> Project:
    return get_project_or_404(db, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("owner", "technical_assessor", "ethics_reviewer"))) -> Project:
    project = get_project_or_404(db, project_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    project.updated_at = datetime.now(timezone.utc)
    record_system_audit(db, project.id, "project_updated", f"用户 {_.email} 更新项目设置")
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles("owner"))) -> Response:
    project = get_project_or_404(db, project_id)
    db.delete(project)
    db.commit()
    return Response(status_code=204)
