from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SPEECH_SERVICE_", env_file=".env")

    host: str = "0.0.0.0"
    port: int = 8080

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])

    checkpoints_dir: Path = Field(default_factory=lambda: _PROJECT_ROOT / "checkpoints")
    voices_dir: Path = Field(default_factory=lambda: _PROJECT_ROOT / "voices")
    whisper_model_dir: Path = Field(default_factory=lambda: _PROJECT_ROOT)
    whisper_model_name: str = "base"

    device: str | None = None
    use_fp16: bool = True
    use_cuda_kernel: bool | None = None
    use_torch_compile: bool = False
    max_concurrent_synthesis: int = 1

    def cfg_path(self) -> Path:
        return self.checkpoints_dir / "config.yaml"

    def model_dir(self) -> Path:
        return self.checkpoints_dir


@lru_cache
def get_settings() -> Settings:
    return Settings()
