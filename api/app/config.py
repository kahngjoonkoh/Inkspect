import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str
    scorer_url: str
    admin_token: str
    regions_dir: Path
    fq_db_path: Path


def load_settings() -> Settings:
    return Settings(
        database_url=os.environ.get("DATABASE_URL", "sqlite:///./inkspect.db"),
        scorer_url=os.environ.get("SCORER_URL", "http://scorer:8000"),
        admin_token=os.environ.get("ADMIN_TOKEN", "dev-admin"),
        regions_dir=Path(os.environ.get("REGIONS_DIR", Path(__file__).resolve().parents[2] / "regions")),
        # The Exner FQ table is copyrighted, so it is not in git: put your own copy here or set FQ_DB_PATH.
        fq_db_path=Path(os.environ.get("FQ_DB_PATH", Path(__file__).resolve().parent / "data" / "fq_tables.db")),
    )


settings = load_settings()
