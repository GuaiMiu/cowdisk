from __future__ import annotations

import asyncio

from app.core.database import async_session
from app.modules.system.service.config import ConfigCenterService


async def main() -> None:
    async with async_session() as session:
        await ConfigCenterService(session).ensure_defaults()
    print("Config defaults ensured.")


if __name__ == "__main__":
    asyncio.run(main())
