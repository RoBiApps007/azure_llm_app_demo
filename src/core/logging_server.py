import json
import logging
import os
import socket
import socketserver
import threading
import time
from logging.handlers import RotatingFileHandler

from src.core.config import get_settings

settings = get_settings()

_server_instance: 'SyslogUDPServer | None' = None
_server_thread: threading.Thread | None = None
_last_activity: float | None = None
_shutdown_event = threading.Event()

# Syslog facilities and levels mapping
# From https://en.wikipedia.org/wiki/Syslog
FACILITY = {
    'kern': 0, 'user': 1, 'mail': 2, 'daemon': 3,
    'auth': 4, 'syslog': 5, 'lpr': 6, 'news': 7,
    'uucp': 8, 'cron': 9, 'authpriv': 10, 'ftp': 11,
    'local0': 16, 'local1': 17, 'local2': 18, 'local3': 19,
    'local4': 20, 'local5': 21, 'local6': 22, 'local7': 23,
}

LEVEL = {
    'emerg': 0, 'alert': 1, 'crit': 2, 'err': 3,
    'warning': 4, 'notice': 5, 'info': 6, 'debug': 7,
}

# Map syslog levels to Python logging levels
SYSLOG_TO_LOGGING_LEVEL = {
    LEVEL['emerg']: logging.CRITICAL,
    LEVEL['alert']: logging.CRITICAL,
    LEVEL['crit']: logging.CRITICAL,
    LEVEL['err']: logging.ERROR,
    LEVEL['warning']: logging.WARNING,
    LEVEL['notice']: logging.INFO,
    LEVEL['info']: logging.INFO,
    LEVEL['debug']: logging.DEBUG,
}

LOG_LEVEL_MAP = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}


class JSONFormatter(logging.Formatter):
    """
    Formats log records as a JSON string.
    """
    def __init__(self, delimiter='|'):
        super().__init__()
        self.delimiter = delimiter
        self.fields = [
            'asctime', 'name', 'levelname', 'message', 'module', 'funcName'
        ]

    def format(self, record):
        # Create a dictionary with the desired fields
        log_object = {field: getattr(record, field) for field in self.fields}

        # Ensure asctime is formatted
        if 'asctime' in self.fields:
            log_object['asctime'] = self.formatTime(record, self.datefmt)

        # The message might be complex, so make sure it's represented as a string
        log_object['message'] = record.getMessage()

        return json.dumps(log_object)

class SyslogUDPHandler(socketserver.BaseRequestHandler):
    """
    A syslog server handler that receives messages over UDP,
    parses them, and logs them using the standard Python logging framework.
    """

    def handle(self):
        """
        Handles incoming syslog messages.
        """
        global _last_activity
        _last_activity = time.time()  # Update last activity time
        try:
            data = self.request[0].strip()
            message = data.decode('utf-8')

            # Basic syslog message parsing to extract priority
            if message.startswith('<') and '>' in message:
                end_pri = message.find('>')
                pri_part = message[1:end_pri]
                if pri_part.isdigit():
                    priority = int(pri_part)
                    level = priority & 7  # Severity is the lower 3 bits

                    # The actual message content is after the priority tag
                    log_message = message[end_pri + 1:]

                    # Get the corresponding Python logging level
                    logging_level = SYSLOG_TO_LOGGING_LEVEL.get(level, LOG_LEVEL_MAP.get(settings.LOGGING_DEFAULT_LEVEL, logging.INFO))

                    # Log using a logger named after the client's address
                    logger = logging.getLogger(settings.LOGGING_APP_ID)
                    logger.log(logging_level, log_message)
                    return

            # If parsing fails, log the raw message
            fallback_logger = logging.getLogger("syslog_raw")
            fallback_logger.info(message)

        except Exception:
            # In case of any error (e.g., decoding), log the raw data
            error_logger = logging.getLogger("syslog_error")
            error_logger.exception("Error handling syslog message")

class SyslogUDPServer(socketserver.UDPServer):
    """
    A simple UDP-based syslog server.
    """
    def __init__(self, host=settings.LOGGING_SYSLOG_HOST, port=settings.LOGGING_SYSLOG_PORT, handler=SyslogUDPHandler):
        super().__init__((host, port), handler)
        self.logname = None

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        """Handle one request at a time until shutdown."""
        self.timeout = poll_interval
        while not _shutdown_event.is_set():
            self.handle_request()

def is_port_in_use(port: int, host: str) -> bool:
    """
    Checks if a UDP port is already in use on a given host.
    Returns True if the port is in use, False otherwise.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.bind((host, port))
        except OSError:
            return True
    return False

def setup_log_server() -> None:
    """
    Set up logging and start the syslog server in a background thread if not already running.
    The server will automatically shut down after a configured idle time.

    Client applications can be configured to send logs to this server
    using Python's standard SysLogHandler.
    """
    global _server_instance, _server_thread, _last_activity, _shutdown_event
    server_address = (settings.LOGGING_SYSLOG_HOST, settings.LOGGING_SYSLOG_PORT)

    # If already running, just reset the state and return
    if _server_instance:
        logging.info("Syslog server is already running.")
        return

    # Verify if syslog server with expected host and port is already running.
    if is_port_in_use(server_address[1], server_address[0]):
        logging.info(f"Syslog server port {server_address[1]} is already in use. Assuming another process is running it.")
        return

    # Reset shutdown event
    _shutdown_event.clear()
    
    # Configure logging handlers
    delimiter = settings.LOGGING_DELIMITER
    log_format = f'%(asctime)s{delimiter}%(name)s{delimiter}%(levelname)s{delimiter}%(message)s{delimiter}%(module)s{delimiter}%(funcName)s'
    date_format = settings.LOGGING_DATE_FORMAT

    root_logger = logging.getLogger('')
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)

        # Standard file handler
        file_handler = logging.FileHandler(f'{settings.LOGGING_FILE_NAME}.log', mode='a')
        file_formatter = logging.Formatter(log_format, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        # Rotating JSON file handler
        json_handler = RotatingFileHandler(
            filename=f'{settings.LOGGING_FILE_NAME}.json',
            maxBytes=settings.LOGGING_MAX_FILE_SIZE * 1024 * 1024,
            backupCount=settings.LOGGING_BACKUP_COUNT
        )
        json_formatter = JSONFormatter(delimiter=delimiter)
        json_formatter.datefmt = date_format
        json_handler.setFormatter(json_formatter)
        root_logger.addHandler(json_handler)

    # Start the server in a background thread
    try:
        _server_instance = SyslogUDPServer(host=server_address[0], port=server_address[1])
        _server_thread = threading.Thread(target=_server_instance.serve_forever)
        _server_thread.daemon = True  # Allows main program to exit
        _server_thread.start()

        _last_activity = time.time()

        # Start a monitoring thread for idle timeout
        monitor_thread = threading.Thread(target=_idle_monitor)
        monitor_thread.daemon = True
        monitor_thread.start()

        log_msg = f"Starting syslog server on port {_server_instance.server_address[1]} in a background thread."
        logging.info(log_msg)
        print(log_msg)

    except Exception as e:
        log_msg = f"Failed to start syslog server: {e}"
        logging.error(log_msg)
        print(log_msg)
        _server_instance = None

def _idle_monitor():
    """Monitors for server idleness and shuts it down."""
    while not _shutdown_event.is_set():
        if _last_activity and (time.time() - _last_activity > settings.LOGGING_IDLE_TIMEOUT_S):
            logging.info(f"Syslog server idle for more than {settings.LOGGING_IDLE_TIMEOUT_S} seconds. Shutting down.")
            shutdown_log_server()
            break
        time.sleep(5) # Check every 5 seconds

def shutdown_log_server():
    """Shuts down the running syslog server."""
    global _server_instance, _server_thread
    if _server_instance:
        logging.info("Shutting down syslog server.")
        _shutdown_event.set()
        _server_instance.shutdown()
        _server_instance.server_close()
        if _server_thread:
            _server_thread.join(timeout=5)
        _server_instance = None
        _server_thread = None
        logging.info("Syslog server shut down.")

def get_logger(name: str | None = None) -> logging.Logger:
    """
    Returns a logger with the defined name or if not defined of the calling module.
    Dynamically identifies the caller from the stack trace.
    """
    if name:
        requested_logger = logging.getLogger(f"{settings.LOGGING_APP_ID}.{name}")
    else:
        import inspect
        # Get the caller's frame from the stack
        caller_frame = inspect.stack()[1]
        module = inspect.getmodule(caller_frame[0])
        module_name = module.__name__ if module else ''
        file_name_caller = os.path.splitext(os.path.basename(caller_frame.filename))[0]

        if module_name == "":
            requested_logger = logging.getLogger(f"{settings.LOGGING_APP_ID}")
        else:
            requested_logger = logging.getLogger(f"{settings.LOGGING_APP_ID}.{file_name_caller}.{module_name}")
    requested_logger.setLevel(LOG_LEVEL_MAP.get(settings.LOGGING_DEFAULT_LEVEL, logging.INFO))
    handler = logging.handlers.SysLogHandler(address=(settings.LOGGING_SYSLOG_HOST, settings.LOGGING_SYSLOG_PORT))
    requested_logger.addHandler(handler)
    return requested_logger
    '''
    # Use file name and module name for logger naming, else just file name
    module_name = module.__name__ if module else ''
    file_name_caller = os.path.splitext(os.path.basename(caller_frame.filename))[0]
    if module_name == "":
        return logging.getLogger(f"{settings.LOGGING_APP_ID}.{file_name_caller}")
    else:
        return logging.getLogger(f"{settings.LOGGING_APP_ID}.{file_name_caller}.{module_name}")
    '''

