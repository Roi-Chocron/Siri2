import logging
import os
from datetime import datetime

LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".log"
log_filepath = os.path.join(LOG_DIR, log_filename)

# Basic Configuration for logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath),
        logging.StreamHandler() # Also print to console
    ]
)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger instance with the specified name.
    """
    return logging.getLogger(name)

if __name__ == '__main__':
    logger = get_logger("TestLogger")
    logger.info("This is an info message from the test logger.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    print(f"Log file should be created at: {log_filepath}")
