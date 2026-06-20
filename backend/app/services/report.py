from html import escape
import json

from sqlalchemy.orm import Session

from ..models import (
    ComplianceMapping,
    EngagementRecord,
    GateDecision,
    LLMAuditRecord,
    ModelTestResult,
    ModelTestRun,
    ModuleResult,
    Project,
    RiskResponse,
    StakeholderGroup,
)
from .risk import raw_risk, residual_risk, risk_summary


def latest_gate(db: Session, project_id: str) -> GateDecision | None:
    return (
        db.query(GateDecision)
        .filter(GateDecision.project_id == project_id)
        .order_by(GateDecision.created_at.desc())
        .first()
    )


def project_markdown(db: Session, project: Project) -> str:
    gate = latest_gate(db, project.id)
    risks = db.query(RiskResponse).filter(RiskResponse.project_id == project.id).all()
    modules = db.query(ModuleResult).filter(ModuleResult.project_id == project.id).all()
    stakeholders = db.query(StakeholderGroup).filter(StakeholderGroup.project_id == project.id).all()
    engagements = db.query(EngagementRecord).filter(EngagementRecord.project_id == project.id).all()
    compliance = db.query(ComplianceMapping).filter(ComplianceMapping.project_id == project.id).all()
    audits = db.query(LLMAuditRecord).filter(LLMAuditRecord.project_id == project.id).all()
    test_run = (
        db.query(ModelTestRun)
        .filter(ModelTestRun.project_id == project.id)
        .order_by(ModelTestRun.started_at.desc())
        .first()
    )

    lines = [
        f"# {project.name} 伦理评估报告",
        "",
        "> 本报告只适用于上述部署边界内的项目场景。若模型用途、用户群体、数据来源、交互方式或组织责任结构发生重大变化，应重新触发伦理评估。",
        "",
        "## 1. 项目概览",
        f"- 模型信息：`{json.dumps(project.model_info, ensure_ascii=False)}`",
        f"- 部署上下文：`{json.dumps(project.deployment_context, ensure_ascii=False)}`",
        f"- 治理边界：`{json.dumps(project.governance, ensure_ascii=False)}`",
        "",
        "## 2. 门禁结论",
    ]
    if gate:
        lines += [f"- 状态：**{gate.status}**", f"- 未解决高风险：{gate.unresolved_high_risks}", f"- 低置信度项：{gate.low_confidence_items}"]
        lines += ["- 原因："] + [f"  - {reason}" for reason in gate.reasons]
        lines += ["- 必要行动："] + [f"  - {action}" for action in gate.required_actions]
    else:
        lines.append("- 尚未执行门禁评估。")

    lines += ["", "## 3. 风险总览"]
    for item in risk_summary(db, project.id):
        lines.append(f"- {item['category']}: 原始风险 {item['raw']}，剩余风险 {item['residual']}，条目 {item['count']}")

    lines += ["", "## 4. 证据链"]
    for risk in risks:
        lines.append(
            f"- `{risk.question_id}` / {risk.category}: 剩余风险 {residual_risk(risk):.1f}; "
            f"证据={risk.evidence_type}; 置信度={risk.confidence}; 负责人={risk.mitigation_owner or '未指定'}; "
            f"缓解措施={risk.mitigation or '未填写'}; 理由={risk.rationale or '未填写'}"
        )

    lines += ["", "## 5. 四维评估模块"]
    for module in modules:
        lines.append(f"- {module.module_type}: {'已完成' if module.completed_at else '草稿'}; 备注：{module.human_review_notes or '无'}")

    lines += ["", "## 6. 包容与参与闭环"]
    for stakeholder in stakeholders:
        lines.append(f"- {stakeholder.name}: 权力{stakeholder.power}/影响{stakeholder.impact}/弱势={stakeholder.vulnerability}/优先级={stakeholder.priority}")
    for engagement in engagements:
        lines.append(f"- 参与记录：{engagement.stakeholder_group} 通过 {engagement.participation_method} 提出 `{engagement.key_concerns}`；回应：{engagement.design_response}")

    lines += ["", "## 7. 法规与规范映射"]
    lines.append("> 本节用于辅助内部审查和外部沟通，不构成法律意见或合规认证。")
    for row in compliance:
        lines.append(f"- {row.norm_reference}: {row.status}; 证据要求：{row.evidence_required}; 备注：{row.reviewer_notes or '无'}")

    lines += ["", "## 8. LLM辅助审计摘要"]
    for audit in audits:
        lines.append(f"- {audit.llm_task}: {audit.model}, 状态={audit.human_status}, 审阅人={audit.human_reviewer or '未审阅'}")

    lines += ["", "## 9. 被部署模型实测证据"]
    if not test_run:
        lines.append("- 尚未运行模型实测。")
    else:
        lines.append(f"- 测试套件：{test_run.suite_name}; 状态：{test_run.status}; 风险/异常：{test_run.flagged_cases}/{test_run.total_cases}; 人工状态：{test_run.reviewer_status}")
        accepted_results = []
        draft_results = []
        for result in db.query(ModelTestResult).filter(ModelTestResult.run_id == test_run.id).all():
            if result.human_status in {"accepted", "revised"}:
                accepted_results.append(result)
            else:
                draft_results.append(result)
        lines.append("- 正式证据：")
        if accepted_results:
            for result in accepted_results:
                lines.append(
                    f"  - {result.category}: {result.risk_signal}; 严重性={result.severity}; "
                    f"人工状态={result.human_status}; 审阅人={result.human_reviewer or '未填写'}; "
                    f"依据={result.human_notes or result.rationale}; 输出摘要={result.output[:120] or result.error[:120]}"
                )
        else:
            lines.append("  - 尚无已人工确认的模型实测证据。")
        lines.append("- 待复核附件：")
        if draft_results:
            for result in draft_results:
                lines.append(f"  - {result.category}: {result.risk_signal}; 严重性={result.severity}; 自动依据={result.rationale}")
        else:
            lines.append("  - 无。")

    return "\n".join(lines) + "\n"


def project_html(db: Session, project: Project) -> str:
    markdown = project_markdown(db, project)
    body = []
    for line in markdown.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body.append(f"<p class='bullet'>{escape(line)}</p>")
        elif line.startswith("> "):
            body.append(f"<blockquote>{escape(line[2:])}</blockquote>")
        elif line.strip():
            body.append(f"<p>{escape(line)}</p>")
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{escape(project.name)} 伦理评估报告</title>
  <style>
    body {{ font-family: "Noto Sans SC", "PingFang SC", sans-serif; max-width: 980px; margin: 40px auto; line-height: 1.7; color: #17201b; }}
    h1 {{ font-size: 30px; border-bottom: 3px solid #1f6f5b; padding-bottom: 12px; }}
    h2 {{ margin-top: 32px; font-size: 20px; color: #1f6f5b; }}
    blockquote {{ border-left: 4px solid #b54c2f; margin: 16px 0; padding: 8px 16px; background: #fff7f2; }}
    .bullet {{ margin-left: 16px; }}
  </style>
</head>
<body>{''.join(body)}</body>
</html>
"""
