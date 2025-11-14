"""
Configuration management using Pydantic models for YAML validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, validator


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: str = "harvest.log"
    rotate_bytes: int = 10_485_760  # 10MB
    backup_count: int = 5


class HttpConfig(BaseModel):
    """HTTP client configuration."""

    user_agent: str = "pdfharvest/0.1.0"
    max_keepalive: int = 20
    max_connections: int = 20


class TimeoutConfig(BaseModel):
    """Timeout configuration."""

    read: float = 30.0
    connect: float = 15.0


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    force_refresh: bool = False


class FoldersConfig(BaseModel):
    """Output folder configuration."""

    downloads: str = "downloads"
    found: str = "output_found"
    notfound: str = "output_notfound"


class Config(BaseModel):
    """Main configuration model."""

    input_excel: str
    doi_column: str = "doi"
    email: str
    strings: List[str] = Field(default_factory=list)
    output_dir: str = "output"
    batch_size: int = 5
    concurrency: int = 6
    write_after_each_batch: bool = True

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    http: HttpConfig = Field(default_factory=HttpConfig)
    timeouts: TimeoutConfig = Field(default_factory=TimeoutConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    folders: FoldersConfig = Field(default_factory=FoldersConfig)

    @validator("email")
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Email must contain @ symbol")
        return v

    @validator("strings")
    def validate_strings(cls, v):
        if not v:
            raise ValueError("At least one search string must be provided")
        return v

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        """Load configuration from YAML file."""
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    def to_dict(self) -> Dict:
        """Convert to dictionary for backward compatibility."""
        return self.dict()


def load_config(path: str | Path) -> Config:
    """Load and validate configuration from YAML file."""
    return Config.from_yaml(path)
