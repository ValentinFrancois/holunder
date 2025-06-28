import sys
from logging import INFO, StreamHandler, getLogger

logger = getLogger("holunder")
logger.setLevel(INFO)
handler = StreamHandler(stream=sys.stdout)
handler.setLevel(INFO)
logger.addHandler(handler)
