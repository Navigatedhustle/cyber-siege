"""Local configuration. Model endpoints must remain loopback only."""
import os
from pathlib import Path
from urllib.parse import urlparse
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
# Keep library scratch files and caches inside this project's workspace.
(ROOT/'runtime/tmp').mkdir(parents=True,exist_ok=True)
(ROOT/'runtime/app-cache').mkdir(parents=True,exist_ok=True)
os.environ['TMPDIR']=str(ROOT/'runtime/tmp')
os.environ['XDG_CACHE_HOME']=str(ROOT/'runtime/app-cache')

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    models_config: str = 'models.yaml'
    app_port: int = 8080
    public_base_url: str = 'http://127.0.0.1:8080'
    facilitator_pin: str = 'change-this-before-event'
    lab_request_url: str = ''
    max_teams: int = 15
    max_participants: int = 60
    agent_concurrency_limit: int = 32
    card_llm_polish: bool = False
    agentic_mode: bool = False
    gpu_telemetry_enabled: bool = True
    database_path: str = 'runtime/cyber_siege.sqlite3'
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_username: str = ''
    smtp_password: str = ''
    smtp_from: str = ''

settings = Settings()

def local_endpoint(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
        raise ValueError('Inference and metrics endpoints must use HTTP loopback or an SSH loopback forward')
    return url.rstrip('/')
