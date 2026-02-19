from __future__ import annotations

import os
import platform
import sys

import psutil

from app.modules.system.schemas.monitor import PythonStatusOut


class PythonInfoProvider:
    @staticmethod
    def read() -> PythonStatusOut:
        process_cpu_percent: float | None = None
        try:
            process = psutil.Process(os.getpid())
            process_cpu_percent = round(float(process.cpu_percent(interval=0.0)), 2)
        except Exception:
            process_cpu_percent = None

        return PythonStatusOut(
            status="running",
            version=platform.python_version(),
            executable=os.path.realpath(sys.executable),
            implementation=platform.python_implementation(),
            process_id=os.getpid(),
            process_cpu_percent=process_cpu_percent,
        )
