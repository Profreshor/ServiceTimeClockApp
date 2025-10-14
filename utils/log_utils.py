# utils/log_utils.py
import logging
import os

def setup_logger():
    """
    Sets up a simple rotating logger that writes to /logs/app.log.
    Called once at app startup or module import.
    """
    logs_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    log_path = os.path.join(logs_dir, 'app.log')

    logger = logging.getLogger('ServiceTimeClock')
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        file_handler = logging.FileHandler(log_path)
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Optional: also print to console
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
