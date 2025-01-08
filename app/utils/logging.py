import logging

logging.basicConfig(
    level=logging.DEBUG,  # Capture all levels: DEBUG and above
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file named 'app.log'
        logging.StreamHandler()  # Also log to the console
    ]
)
logger = logging.getLogger(__name__)