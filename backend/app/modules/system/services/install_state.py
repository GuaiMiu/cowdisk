from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from app.core.config import settings

InstallPhase = Literal["PENDING", "RUNNING", "FAILED", "DONE"]


@dataclass(frozen=True)
class InstallStatus:
    installed: bool
    phase: InstallPhase
    message: str | None = None
    updated_at: str | None = None


class InstallStateService:
    _STATE_FILE = Path.cwd() / ".install_state.json"
    _SENTINEL_FILE = Path.cwd() / ".installed"

    @classmethod
    def _now_iso(cls) -> str:
        return datetime.now().isoformat()

    @classmethod
    def _safe_read_state(cls) -> dict:
        if not cls._STATE_FILE.exists():
            return {}
        try:
            raw = cls._STATE_FILE.read_text(encoding="utf-8")
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @classmethod
    def _write_state(cls, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False, indent=2)
        cls._STATE_FILE.write_text(payload, encoding="utf-8")

    @classmethod
    def is_done_fast(cls) -> bool:
        return bool(settings.INSTALL_COMPLETED) or cls._SENTINEL_FILE.exists()

    @classmethod
    def mark_phase(cls, phase: InstallPhase, message: str | None = None) -> None:
        data = {
            "phase": phase,
            "message": message,
            "updated_at": cls._now_iso(),
        }
        cls._write_state(data)

    @classmethod
    def mark_done(cls, message: str | None = None) -> None:
        cls._SENTINEL_FILE.write_text("installed=true\n", encoding="utf-8")
        cls.mark_phase("DONE", message=message or "安装已完成")

    @classmethod
    def get_status(cls) -> InstallStatus:
        if bool(settings.INSTALL_COMPLETED):
            state = cls._safe_read_state()
            return InstallStatus(
                installed=True,
                phase="DONE",
                message=str(state.get("message") or "安装已完成"),
                updated_at=str(state.get("updated_at") or cls._now_iso()),
            )
        if cls._SENTINEL_FILE.exists():
            state = cls._safe_read_state()
            return InstallStatus(
                installed=True,
                phase="DONE",
                message=str(state.get("message") or "安装已完成"),
                updated_at=str(state.get("updated_at") or cls._now_iso()),
            )
        state = cls._safe_read_state()
        phase = str(state.get("phase") or "PENDING").upper()
        if phase not in {"PENDING", "RUNNING", "FAILED", "DONE"}:
            phase = "PENDING"
        return InstallStatus(
            installed=False,
            phase=phase,  # type: ignore[arg-type]
            message=str(state.get("message") or ""),
            updated_at=str(state.get("updated_at") or ""),
        )
