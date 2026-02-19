from __future__ import annotations

import ast
import json
import platform
import subprocess
from typing import Any


def normalize_text(value: str | bytes | int | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return str(value)


def parse_user_id_from_session_key(key: str) -> int | None:
    _, _, user_part = key.rpartition(":")
    if not user_part.isdigit():
        return None
    return int(user_part)


def safe_parse_device_info(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw

    text = normalize_text(raw).strip()
    if not text:
        return None

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return None


def read_cpu_name() -> str:
    system_name = platform.system().lower()

    if system_name == "windows":
        # 1) Preferred: registry ProcessorNameString.
        try:
            import winreg  # type: ignore

            reg_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_path) as key:
                value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                name = normalize_text(value).strip()
                if name:
                    return name
        except Exception:
            pass

        # 2) Fallback: WMI/CIM processor name (often more readable on Windows).
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)",
            ]
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
            name = normalize_text(result.stdout).strip()
            if name:
                return name
        except Exception:
            pass

    if system_name == "linux":
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        _, raw = line.split(":", 1)
                        name = raw.strip()
                        if name:
                            return name
                        break
        except Exception:
            pass

    fallback = (
        (platform.processor() or "").strip()
        or (platform.uname().processor or "").strip()
    )
    return fallback
