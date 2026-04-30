from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SKLIK_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_token: str
    endpoint: str = "https://api.sklik.cz/drak/json/v5"
    fenix_endpoint: str = "https://api.sklik.cz/fenix/v1"
    request_timeout_s: int = 30
    log_level: str = "INFO"
