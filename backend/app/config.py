from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "EthosGate · 善治"
    app_env: str = "development"
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'app.db'}"
    jwt_secret: str = "change-this-development-secret"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 8
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.5"
    allow_default_admin_password: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.app_env == "production":
        if settings.jwt_secret == "change-this-development-secret":
            raise RuntimeError("生产环境必须设置强 JWT_SECRET")
        if settings.allow_default_admin_password:
            raise RuntimeError("生产环境必须关闭默认管理员密码：ALLOW_DEFAULT_ADMIN_PASSWORD=false")
    if settings.database_url.startswith("sqlite:///"):
        db_path = Path(settings.database_url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
