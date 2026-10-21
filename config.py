"""Environment configuration; relative paths are anchored to this project."""
from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')


@dataclass
class Settings:
    database_url: str = ''
    data_dir: Path | None = None
    session_secret: str = ''
    session_hours: int = 12
    cookie_secure: bool = False
    match_threshold: float = 45
    semantic_mode: str = 'auto'
    semantic_model_dir: Path | None = None
    demo_mode: bool = False

    @classmethod
    def from_env(cls):
        return cls(
            database_url=os.getenv('DATABASE_URL', 'sqlite:///./lost_and_found.db'),
            data_dir=Path(os.getenv('DATA_DIR', './data')),
            session_secret=os.getenv('SESSION_SECRET', ''),
            session_hours=int(os.getenv('SESSION_HOURS', '12')),
            cookie_secure=os.getenv('COOKIE_SECURE', 'false').lower() == 'true',
            match_threshold=float(os.getenv('MATCH_THRESHOLD', '45')),
            semantic_mode=os.getenv('SEMANTIC_MODE', 'auto'),
            semantic_model_dir=Path(os.getenv('SEMANTIC_MODEL_DIR', str(ROOT / 'models' / 'all-MiniLM-L6-v2'))),
            demo_mode=os.getenv('DEMO_MODE','false').lower()=='true',
        )

    def prepare(self):
        url = make_url(self.database_url or 'sqlite:///./lost_and_found.db')
        if url.drivername != 'sqlite' or not url.database or url.database == ':memory:':
            raise ValueError('Use a file-backed sqlite:/// database URL.')
        path = Path(url.database)
        path = (path if path.is_absolute() else ROOT / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.database_url = url.set(database=str(path)).render_as_string(hide_password=False)
        self.data_dir = Path(self.data_dir or ROOT / 'data')
        if not self.data_dir.is_absolute():
            self.data_dir = ROOT / self.data_dir
        self.data_dir = self.data_dir.resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.semantic_model_dir = Path(self.semantic_model_dir or ROOT / 'models' / 'all-MiniLM-L6-v2')
        if not self.semantic_model_dir.is_absolute():
            self.semantic_model_dir = ROOT / self.semantic_model_dir
        if self.semantic_mode not in {'auto', 'off'}:
            raise ValueError('SEMANTIC_MODE must be auto or off.')
        if not 0 <= self.match_threshold <= 100 or not 1 <= self.session_hours <= 168:
            raise ValueError('Invalid matching threshold or session lifetime.')
        if not self.session_secret:
            import secrets
            key = self.data_dir / 'session.key'
            try:
                with key.open('x', encoding='utf-8') as stream:
                    stream.write(secrets.token_urlsafe(48))
            except FileExistsError:
                pass
            self.session_secret = key.read_text(encoding='utf-8').strip()
        if len(self.session_secret) < 32:
            raise ValueError('SESSION_SECRET must have at least 32 characters.')
        return self
