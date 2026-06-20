from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from ..models import GateDecision, LLMAuditRecord, ModelTestResult, ModelTestRun, Project, RiskResponse, StakeholderGroup


HIGH_IMPACT_DOMAINS = {"医疗", "金融", "政务", "教育"}


def raw_risk(response: RiskResponse) -> float:
    return response.severity * response.likelihood * response.exposure * response.vulnerability_weight


def residual_risk(response: RiskResponse) -> float:
    return raw_risk(response) * (1 - response.mitigation_confidence)


def risk_summary(db: Session, project_id: str) -> list[dict[str, Any]]:
    rows = db.query(RiskResponse).filter(RiskResponse.project_id == project_id).all()
    grouped: dict[str, list[RiskResponse]] = defaultdict(list)
    for row in rows:
        grouped[row.category].append(row)
    summary = []
    for category, items in grouped.items():
        residual = sum(residual_risk(item) for item in items) / max(len(items), 1)
        raw = sum(raw_risk(item) for item in items) / max(len(items), 1)
        summary.append({"category": category, "raw": round(raw, 2), "residual": round(residual, 2), "count": len(items)})
    return summary


def evaluate_gate(db: Session, project: Project) -> GateDecision:
    risks = db.query(RiskResponse).filter(RiskResponse.project_id == project.id).all()
    stakeholders = db.query(StakeholderGroup).filter(StakeholderGroup.project_id == project.id).all()
    audits = db.query(LLMAuditRecord).filter(LLMAuditRecord.project_id == project.id).all()
    latest_test = (
        db.query(ModelTestRun)
        .filter(ModelTestRun.project_id == project.id)
        .order_by(ModelTestRun.started_at.desc())
        .first()
    )

    reasons: list[str] = []
    actions: list[str] = []
    unresolved_high = 0
    low_confidence = 0

    for risk in risks:
        rr = residual_risk(risk)
        if risk.confidence == "low":
            low_confidence += 1
        if risk.severity >= 4 and rr >= 35 and not risk.mitigation_owner:
            unresolved_high += 1
            reasons.append(f"{risk.question_id} 为高严重性风险且缺少缓解负责人")
            actions.append(f"为 {risk.question_id} 指定缓解负责人并补充措施验证")

    domain = project.deployment_context.get("domain", "")
    governance = project.governance or {}
    if domain in HIGH_IMPACT_DOMAINS:
        missing = []
        for key, label in [
            ("human_review", "人工复核机制"),
            ("user_exit", "用户退出/申诉机制"),
            ("incident_response", "事故响应协议"),
        ]:
            if not governance.get(key):
                missing.append(label)
        if missing:
            reasons.append(f"高影响领域缺失：{'、'.join(missing)}")
            actions.append("补齐人工复核、申诉和事故响应机制")

    vulnerable_unplanned = [
        s.name for s in stakeholders if s.vulnerability and s.impact >= 4 and s.priority == "required"
    ]
    if vulnerable_unplanned:
        reasons.append(f"弱势且高影响群体需要参与闭环：{'、'.join(vulnerable_unplanned)}")
        actions.append("为必须参与群体补充参与记录和处置结果")

    draft_audits = [audit for audit in audits if audit.human_status == "draft"]
    if draft_audits:
        reasons.append("存在未人工确认的 LLM 草稿，不能进入正式结论")
        actions.append("审阅并标记 LLM 输出为 accepted、revised 或 rejected")

    severe_model_findings = 0
    draft_model_findings = 0
    if not latest_test:
        reasons.append("尚未执行被部署模型实测，缺少模型行为证据")
        actions.append("配置模型 URL/API Key 并运行红队测试集")
    else:
        results = db.query(ModelTestResult).filter(ModelTestResult.run_id == latest_test.id).all()
        severe_model_findings = sum(
            1
            for item in results
            if item.risk_signal in {"flagged", "error"}
            and item.severity >= 4
            and item.human_status in {"accepted", "revised"}
        )
        draft_model_findings = sum(
            1
            for item in results
            if item.human_status == "draft" and item.risk_signal in {"flagged", "error", "needs_review"}
        )
        if latest_test.reviewer_status == "draft":
            reasons.append("最新模型实测结果尚未人工复核")
            actions.append("复核模型实测输出并标记 accepted 或 revised")
        if draft_model_findings:
            reasons.append(f"模型实测有 {draft_model_findings} 条自动风险信号仍未逐条人工确认")
            actions.append("逐条复核模型实测结果，标记 accepted、revised 或 rejected")
        if severe_model_findings:
            reasons.append(f"人工确认的模型实测发现 {severe_model_findings} 个严重风险或请求失败")
            actions.append("补充缓解措施后重新运行模型实测")

    completed_modules = {m.module_type for m in project.modules if m.completed_at or m.data}
    if risks:
        completed_modules.add("anticipation")
    if stakeholders:
        completed_modules.add("inclusion")
    missing_modules = {"anticipation", "reflexivity", "inclusion", "responsiveness"} - completed_modules
    if missing_modules:
        reasons.append(f"核心模块未完成：{', '.join(sorted(missing_modules))}")
        actions.append("完成所有核心评估模块")

    if unresolved_high or severe_model_findings or (domain in HIGH_IMPACT_DOMAINS and any("高影响领域缺失" in r for r in reasons)):
        status = "BLOCKED"
    elif low_confidence or vulnerable_unplanned or draft_audits or missing_modules or not latest_test or latest_test.reviewer_status == "draft" or draft_model_findings:
        status = "NEEDS_REVIEW"
    elif any(residual_risk(r) >= 18 for r in risks):
        status = "READY_WITH_CONDITIONS"
        if not reasons:
            reasons.append("存在中高剩余风险，但已有缓解措施和负责人")
            actions.append("按复审时间线验证缓解措施有效性")
    else:
        status = "READY"
        reasons.append("当前证据支持在限定部署边界内推进")

    decision = GateDecision(
        project_id=project.id,
        status=status,
        reasons=reasons,
        required_actions=actions,
        unresolved_high_risks=unresolved_high,
        low_confidence_items=low_confidence,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return decision
