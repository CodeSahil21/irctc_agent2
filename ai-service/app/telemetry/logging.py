import logging


def get_logger(name: str = "ai-service") -> logging.Logger:
    return logging.getLogger(name)