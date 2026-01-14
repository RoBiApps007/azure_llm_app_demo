from .core import logging_server as _log_srv

_log_srv.setup_log_server()
LOGGER = _log_srv.get_logger(__name__)
LOGGER.info("Main package initialized")
