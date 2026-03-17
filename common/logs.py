import logging


def get_logger(name=__name__, level=logging.INFO):
    logger = logging.getLogger(name)

    if logger.hasHandlers():
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger