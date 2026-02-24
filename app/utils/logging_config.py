import logging
import os

DEV = os.getenv("DEV_MODE", "1") == "1"

def configure_logging():
    level = logging.DEBUG if DEV else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
