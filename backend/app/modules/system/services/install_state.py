from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

InstallPhase = Literal["PENDING", "RUNNING", "FAILED", "DONE"]


@dataclass(frozen=True)
class InstallStatus:
    installed: bool
    phase: InstallPhase
    message: str | None = None
    updated_at: str | None = None


class InstallStateService:
    _SENTINEL_FILE = Path.cwd() / ".installed"
    _phase: InstallPhase = "PENDING"
    _message: str | None = None
    _updated_at: str | None = None

    @classmethod
    def _now_iso(cls) -> str:
        return datetime.now().isoformat()

    @classmethod
    def is_done_fast(cls) -> bool:
        return cls._SENTINEL_FILE.exists()

    @classmethod
    def mark_phase(cls, phase: InstallPhase, message: str | None = None) -> None:
        normalized_phase = phase.upper()
        if normalized_phase not in {"PENDING", "RUNNING", "FAILED", "DONE"}:
            normalized_phase = "PENDING"
        cls._phase = normalized_phase  # type: ignore[assignment]
        cls._message = message
        cls._updated_at = cls._now_iso()

    @classmethod
    def mark_running(cls, message: str | None = None) -> None:
        cls.mark_phase("RUNNING", message=message or "安装流程启动")

    @classmethod
    def mark_failed(cls, message: str | None = None) -> None:
        cls.mark_phase("FAILED", message=message or "安装流程失败")

    @classmethod
    def mark_done(cls, message: str | None = None) -> None:
        cls._SENTINEL_FILE.write_text("installed=true\n", encoding="utf-8")
        cls.mark_phase("DONE", message=message or "安装已完成")

    @classmethod
    def get_status(cls) -> InstallStatus:
        if cls._SENTINEL_FILE.exists():
            return InstallStatus(
                installed=True,
                phase="DONE",
                message=cls._message or "安装已完成",
                updated_at=cls._updated_at or cls._now_iso(),
            )
        return InstallStatus(
            installed=False,
            phase=cls._phase,
            message=cls._message,
            updated_at=cls._updated_at,
        )
