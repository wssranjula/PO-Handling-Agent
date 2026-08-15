"""Run Gmail polling as a dedicated process for production deployments."""

import asyncio

from app.config import get_settings
from app.db import close_database, initialize_database
from app.logging_config import configure_logging
from app.services.gmail import gmail_polling_loop


async def run() -> None:
    settings = get_settings()
    configure_logging(settings)
    await initialize_database()
    try:
        await gmail_polling_loop(settings)
    finally:
        await close_database()


if __name__ == "__main__":
    asyncio.run(run())
