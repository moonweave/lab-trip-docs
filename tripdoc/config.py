from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    data_dir: Path
    db_path: Path
    uploads_dir: Path
    exports_dir: Path
    admin_user: str
    admin_password: str


def load_config() -> Config:
    data_dir = Path(os.environ.get("TRIPDOC_DATA_DIR", "data")).resolve()
    return Config(
        host=os.environ.get("TRIPDOC_HOST", "0.0.0.0"),
        port=int(os.environ.get("TRIPDOC_PORT", "8501")),
        data_dir=data_dir,
        db_path=data_dir / "app.db",
        uploads_dir=data_dir / "uploads",
        exports_dir=data_dir / "exports",
        admin_user=os.environ.get("TRIPDOC_ADMIN_USER", "admin"),
        admin_password=os.environ.get("TRIPDOC_ADMIN_PASSWORD", "change-me"),
    )

