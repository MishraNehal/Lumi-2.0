import sys

from loguru import logger


_LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)


def configure_logging(log_level: str = "INFO") -> None:
    logger.remove()
    logger.add(
        sys.stdout,
        level=log_level.upper(),
        format=_LOG_FORMAT,
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )
