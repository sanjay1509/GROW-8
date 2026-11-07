import logging
import sys


def configure_logging(level: str = "INFO", service: str = "grow8") -> None:
    """Configure root logging with one structured line per record on stdout."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            f"%(asctime)s level=%(levelname)s service={service} logger=%(name)s msg=%(message)s"
        )
    )
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    logging.getLogger("pika").setLevel(logging.WARNING)
