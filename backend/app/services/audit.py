from sqlalchemy.orm import Session

from ..models import LLMAuditRecord


def record_system_audit(db: Session, project_id: str, task: str, summary: str, output: str = "操作已记录") -> None:
    db.add(
        LLMAuditRecord(
            project_id=project_id,
            llm_task=task,
            model="system",
            prompt_version="audit_v1",
            input_summary=summary,
            output=output,
            human_status="accepted",
            human_reviewer="system",
        )
    )
