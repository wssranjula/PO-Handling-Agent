import asyncio
import json

from app.config import get_settings
from app.db import SessionFactory, close_database, initialize_database
from app.logging_config import configure_logging
from app.services.knowledge_seed import seed_knowledge


async def main() -> None:
    settings = get_settings()
    configure_logging(settings)
    await initialize_database()
    async with SessionFactory() as session:
        result = await seed_knowledge(session, settings)
    print(json.dumps(result, indent=2))
    await close_database()


if __name__ == "__main__":
    asyncio.run(main())
