from __future__ import annotations

import os
import shutil
from pathlib import Path

import psutil

from app.core.config import settings
from app.modules.system.schemas.monitor import CpuStatusOut, DiskStatusOut, MemoryStatusOut


class SystemMetricsProvider:
    @staticmethod
    def read_cpu_status() -> CpuStatusOut:
        usage_percent: float | None = None
        try:
            usage_percent = round(float(psutil.cpu_percent(interval=0.1)), 2)
        except Exception:
            usage_percent = None
        return CpuStatusOut(usage_percent=usage_percent, logical_cores=os.cpu_count())

    @staticmethod
    def read_memory_status() -> MemoryStatusOut:
        try:
            vm = psutil.virtual_memory()
            return MemoryStatusOut(
                total_bytes=int(vm.total),
                used_bytes=int(vm.used),
                available_bytes=int(vm.available),
                usage_percent=round(float(vm.percent), 2),
            )
        except Exception:
            return MemoryStatusOut()

    @staticmethod
    def read_disk_status() -> DiskStatusOut:
        root = (settings.DISK_ROOT or "").strip() or "./storage"
        path = Path(root).resolve()
        if not path.exists():
            return DiskStatusOut(path=str(path), status="down")
        try:
            usage = shutil.disk_usage(path)
            total = int(usage.total)
            used = int(usage.used)
            free = int(usage.free)
            percent = (used * 100.0 / total) if total > 0 else None
            return DiskStatusOut(
                path=str(path),
                total_bytes=total,
                used_bytes=used,
                free_bytes=free,
                usage_percent=round(percent, 2) if percent is not None else None,
                status="up",
            )
        except Exception:
            return DiskStatusOut(path=str(path), status="down")
