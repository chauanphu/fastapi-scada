import logging
import os
from datetime import datetime
# Create a logs directory if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")
# Filename is logs/{current_date}.log

file_name = datetime.now().strftime("%Y-%m-%d") + ".log"

# Set up basic config first
logging.basicConfig(
    level=logging.DEBUG,  # Capture all levels: DEBUG and above
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Log message format
    handlers=[
        logging.FileHandler(f"logs/{file_name}"),  # Log to a file named 'app.log'
        logging.StreamHandler()  # Also log to the console
    ]
)

# Restrict specific module logging
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)  # Changed from NOTSET to WARNING
logging.getLogger("passlib.registry").setLevel(logging.WARNING) # Changed from NOTSET to WARNING
logging.getLogger("pymongo.connection").setLevel(logging.WARNING)  # Changed from NOTSET to WARNING
logging.getLogger("pymongo.command").setLevel(logging.WARNING)  # Changed from NOTSET to WARNING
logging.getLogger("pymongo.serverSelection").setLevel(logging.WARNING)  # Changed from NOTSET to WARNING
logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)  # Changed from NOTSET to WARNING
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)  # Changed from NOTSET to WARNING

logger = logging.getLogger(__name__)