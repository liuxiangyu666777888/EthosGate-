from sqlalchemy import inspect, text

from .database import engine


def apply_sqlite_compat_migrations() -> None:
    if not engine.url.drivername.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "risk_responses" not in inspector.get_table_names():
        return
    with engine.begin() as connection:
        columns = {column["name"] for column in inspector.get_columns("risk_responses")}
        if "mitigation" not in columns:
            connection.execute(text("ALTER TABLE risk_responses ADD COLUMN mitigation TEXT DEFAULT ''"))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS model_connections (
                id VARCHAR PRIMARY KEY,
                project_id VARCHAR,
                name VARCHAR,
                base_url VARCHAR,
                model_name VARCHAR,
                request_style VARCHAR,
                auth_header VARCHAR,
                auth_scheme VARCHAR,
                api_key_hint VARCHAR,
                timeout_seconds INTEGER,
                created_at DATETIME,
                updated_at DATETIME
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS model_test_suites (
                id VARCHAR PRIMARY KEY,
                domain VARCHAR,
                name VARCHAR,
                version VARCHAR,
                scenario TEXT,
                is_active BOOLEAN,
                created_at DATETIME
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS model_test_cases (
                id VARCHAR PRIMARY KEY,
                suite_id VARCHAR,
                category VARCHAR,
                prompt TEXT,
                expected_behavior TEXT,
                severity INTEGER,
                tags JSON,
                target_group VARCHAR,
                enabled BOOLEAN
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS model_test_runs (
                id VARCHAR PRIMARY KEY,
                project_id VARCHAR,
                connection_id VARCHAR,
                suite_id VARCHAR,
                suite_version VARCHAR,
                model_name VARCHAR,
                endpoint_fingerprint VARCHAR,
                status VARCHAR,
                suite_name VARCHAR,
                total_cases INTEGER,
                flagged_cases INTEGER,
                reviewer_status VARCHAR,
                notes TEXT,
                started_at DATETIME,
                completed_at DATETIME
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS model_test_results (
                id VARCHAR PRIMARY KEY,
                run_id VARCHAR,
                project_id VARCHAR,
                case_id VARCHAR,
                category VARCHAR,
                prompt TEXT,
                expected_behavior TEXT,
                output TEXT,
                risk_signal VARCHAR,
                severity INTEGER,
                rationale TEXT,
                judge_status VARCHAR,
                judge_rationale TEXT,
                human_status VARCHAR,
                human_reviewer VARCHAR,
                human_notes TEXT,
                latency_ms INTEGER,
                error TEXT,
                created_at DATETIME
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS evidence_items (
                id VARCHAR PRIMARY KEY,
                project_id VARCHAR,
                source_type VARCHAR,
                source_id VARCHAR,
                title VARCHAR,
                summary TEXT,
                status VARCHAR,
                confidence VARCHAR,
                reviewer VARCHAR,
                report_section VARCHAR,
                created_at DATETIME
            )
        """))
        for table, additions in {
            "model_test_runs": [
                ("suite_id", "VARCHAR"),
                ("suite_version", "VARCHAR DEFAULT '1.0'"),
                ("model_name", "VARCHAR DEFAULT ''"),
                ("endpoint_fingerprint", "VARCHAR DEFAULT ''"),
            ],
            "model_test_results": [
                ("case_id", "VARCHAR"),
                ("expected_behavior", "TEXT DEFAULT ''"),
                ("judge_status", "VARCHAR DEFAULT 'not_requested'"),
                ("judge_rationale", "TEXT DEFAULT ''"),
                ("human_status", "VARCHAR DEFAULT 'draft'"),
                ("human_reviewer", "VARCHAR DEFAULT ''"),
                ("human_notes", "TEXT DEFAULT ''"),
            ],
        }.items():
            existing = {column["name"] for column in inspector.get_columns(table)}
            for name, ddl in additions:
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
