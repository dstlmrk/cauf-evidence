import logging

from django.utils.timezone import now

logger = logging.getLogger(__name__)

def print_hello_world():
    print("Hello world 👋", now(), flush=True)
    logger.info("BEZIME")
