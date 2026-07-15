import logging


def configure_logging() -> None:
    """Configure a useful baseline without overriding a host application's setup."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
