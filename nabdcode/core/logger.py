import logging
from rich.logging import RichHandler

FORMAT = "%(message)s"
logging.basicConfig(
    level="DEBUG", 
    format=FORMAT, 
    datefmt="[%X]", 
    handlers=[
        RichHandler(),
        logging.FileHandler("debug_nabd.log")
    ]
)
logger = logging.getLogger("nabdcode")
