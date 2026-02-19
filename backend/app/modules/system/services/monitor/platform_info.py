from __future__ import annotations

import platform
import socket
import time
from datetime import datetime

from app.modules.system.schemas.monitor import ServerInfoOut
from app.modules.system.services.monitor.utils import read_cpu_name


class ServerInfoProvider:
    def __init__(self, *, app_start_ts: float | None = None) -> None:
        self._app_start_ts = app_start_ts if app_start_ts is not None else time.time()

    @property
    def app_start_ts(self) -> float:
        return self._app_start_ts

    def read(self) -> ServerInfoOut:
        return ServerInfoOut(
            hostname=socket.gethostname(),
            os=platform.system(),
            os_release=platform.release(),
            machine=platform.machine(),
            processor=read_cpu_name(),
            app_start_time=datetime.fromtimestamp(self._app_start_ts),
        )
