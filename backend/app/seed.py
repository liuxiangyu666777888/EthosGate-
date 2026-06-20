from sqlalchemy.orm import Session

from .auth import hash_password
from .catalog import COMPLIANCE_TEMPLATES
from datetime import datetime, timezone

from .models import ComplianceMapping, EngagementRecord, ModuleResult, Project, RiskResponse, StakeholderGroup, User
from .services.model_testing import seed_default_suite


def seed(db: Session) -> None:
    seed_default_suite(db)

    def enrich_demo_project(project: Project) -> None:
        if not db.query(RiskResponse).filter(RiskResponse.project_id == project.id).first():
            db.add(
                RiskResponse(
                    project_id=project.id,
                    question_id="privacy_001",
                    category="privacy",
                    answer=4,
                    severity=4,
                    likelihood=3,
                    exposure=4,
                    vulnerability_weight=1.3,
                    mitigation_confidence=0.45,
                    mitigation="默认不保存完整对话；敏感日志脱敏；争议输出转人工教师复核。",
                    mitigation_owner="安全负责人",
                    rationale="教育场景涉及未成年人和学习记录，需要更高隐私保护。",
                    evidence_type="policy_doc",
                    evidence_link="internal://privacy-policy",
                    confidence="medium",
                    assessor="系统种子数据",
                    reviewer="系统种子数据",
                )
            )
            db.add(
                RiskResponse(
                    project_id=project.id,
                    question_id="bias_001",
                    category="bias",
                    answer=3,
                    severity=3,
                    likelihood=3,
                    exposure=3,
                    vulnerability_weight=1.2,
                    mitigation_confidence=0.35,
                    mitigation="补充方言、低资源学习者和不同地区教材样本的测试集。",
                    mitigation_owner="评测负责人",
                    rationale="当前评估更偏向普通话和标准教材语境。",
                    evidence_type="audit_record",
                    evidence_link="internal://bias-audit",
                    confidence="medium",
                    assessor="系统种子数据",
                    reviewer="系统种子数据",
                )
            )
        now = datetime.now(timezone.utc)
        existing_modules = {
            row.module_type for row in db.query(ModuleResult).filter(ModuleResult.project_id == project.id).all()
        }
        for module in [
            ModuleResult(project_id=project.id, module_type="anticipation", data={"seed": True}, human_review_notes="示例风险已录入", completed_at=now),
            ModuleResult(project_id=project.id, module_type="reflexivity", data={"answers": {"我们假定的典型用户是谁？为什么？": "高中学生和一线教师，但需要避免把城市重点学校经验当成默认。"}}, human_review_notes="示例反思已确认", completed_at=now),
            ModuleResult(project_id=project.id, module_type="responsiveness", data={"timeline": ["T0", "T+1月", "T+3月"]}, human_review_notes="示例复审时间线", completed_at=now),
            ModuleResult(project_id=project.id, module_type="inclusion", data={"participation_plan": {"cadence": "上线前、3个月、年度复审"}}, human_review_notes="示例参与计划", completed_at=now),
        ]:
            if module.module_type not in existing_modules:
                db.add(module)
        if not db.query(StakeholderGroup).filter(StakeholderGroup.project_id == project.id).first():
            db.add(StakeholderGroup(project_id=project.id, name="低权力高影响学生群体", power=1, impact=5, vulnerability=True, exit_difficulty=4, priority="suggested", notes="需要访谈和申诉渠道"))
            db.add(
                EngagementRecord(
                    project_id=project.id,
                    stakeholder_group="低权力高影响学生群体",
                    participation_method="访谈",
                    key_concerns="担心模型反馈被误认为正式评价。",
                    design_response="增加教师复核提示和申诉入口。",
                    accepted_or_rejected="accepted",
                    follow_up_owner="产品负责人",
                )
            )

    if not db.query(User).filter(User.email == "admin@example.com").first():
        admin = User(
            email="admin@example.com",
            name="系统管理员",
            role="admin",
            password_hash=hash_password("admin123456"),
        )
        db.add(admin)
        db.flush()
        project = Project(
            name="教育辅导 LLM 部署评估",
            description="用于演示完整伦理评估流程的种子案例。",
            status="in_progress",
            owner_id=admin.id,
            model_info={"name": "TutorGPT", "version": "0.9", "base_model": "gpt-series", "params": "unknown"},
            deployment_context={
                "domain": "教育",
                "users": "高中学生、教师、家长",
                "languages": "中文为主，兼顾少量英语问答",
                "interface": "聊天界面",
            },
            team_info={"owner": "产品负责人", "technical": "模型工程团队", "ethics": "伦理顾问"},
            governance={
                "deployment_boundary": "课后辅导、知识解释、练习反馈；不用于升学决策或心理诊断。",
                "decision_impact": "建议",
                "human_review": "争议内容和高风险建议转人工教师确认。",
                "user_exit": "学生可转人工教师，家长可提交申诉。",
                "responsible_owner": "AI教育产品组",
            },
        )
        db.add(project)
        db.flush()
        for item in COMPLIANCE_TEMPLATES:
            db.add(ComplianceMapping(project_id=project.id, status="pending", reviewer_notes="", **item))
        enrich_demo_project(project)
    for project in db.query(Project).filter(Project.name == "教育辅导 LLM 部署评估").all():
        enrich_demo_project(project)
    db.commit()
