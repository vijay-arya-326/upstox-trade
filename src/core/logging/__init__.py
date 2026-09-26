from core.logging.fancy import fancy_print, print_json


def get_api_logger():
    from core.logging.api_logger import api_logger
    return api_logger


__all__ = ["fancy_print", "print_json", "get_api_logger"]