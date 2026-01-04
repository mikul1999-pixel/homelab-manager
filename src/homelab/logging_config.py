import logging
import logging.handlers
import os

def get_default_log_path():
    state_dir = os.environ.get("XDG_STATE_HOME", os.path.expanduser("~/.local/state"))
    return os.path.join(state_dir, "homelab-manager", "logs", "scheduler.log")

def setup_logging(log_file=None):
    """Setup logging configuration"""

    # Resolve default log location
    if log_file is None:
        log_file = get_default_log_path()

    # Always compute log_dir after resolving log_file
    log_dir = os.path.dirname(log_file)

    # Ensure directory exists
    os.makedirs(log_dir, exist_ok=True)

    # Configure logging
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S')
    )

    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger