from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_prefix="SPONGE_")

    database_url: str = "postgresql+psycopg://sponge:sponge_local@127.0.0.1:55432/sponge"
    redis_url: str = "redis://127.0.0.1:56379/0"
    storage_root: Path = Path("data/local")
    ee_project: str = ""
    ee_credentials_file: Path | None = None
    earthdata_token: SecretStr | None = None
    environment: str = "development"
    app_version: str = "0.1.0"
    web_dist: Path | None = None
    trusted_hosts: str = "127.0.0.1,localhost,testserver"
    trusted_proxy_cidrs: str = ""
    session_limit_per_hour: int = Field(120, ge=1)
    session_ttl_hours: int = Field(168, ge=1)
    retention_interval_seconds: int = Field(60, ge=5)
    job_stale_seconds: int = Field(3600, ge=60)
    cpu_reference_timeout_seconds: int = Field(120, ge=1)
    cpu_reference_concurrency: int = Field(2, ge=1)
    max_request_body_bytes: int = Field(25_000_000, ge=10_100_000)
    max_terrain_request_bytes: int = Field(102_000_000, ge=100_000_000)
    allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    nominatim_url: str = "https://nominatim.openstreetmap.org/search"
    photon_url: str = "https://photon.komoot.io/api/"


settings = Settings()
