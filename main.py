import concerto as conc

from src.core.config import get_settings
from src.core.exceptions import MeasurementReadError
from src.core.logging_server import get_logger
#from src.core.logging import get_logger, setup_logging

log = get_logger(__name__)

if __name__ == "__main__":
    #setup_logging()

    log.info("Test logger info....")
    settings = get_settings()
    log.info(f"Project Name: {settings.PROJECT_NAME}")
    log.info(f"Logging Level: {settings.LOGGING_DEFAULT_LEVEL}")
    pass
    try:
        file = conc.data.load_file(r"C:\ProgramData\AVL\CONCERTO 6\DemoData\MDF\OCV_CELL001.mf4")
    except Exception as e:
        raise MeasurementReadError(f"Failed to read measurement: {e}")

    open_files = conc.data.get_open_files()
    for of_i, of in enumerate(open_files):
        log.info(f"[{of_i+1}/{len(open_files)}] Open file: {of.file_name}")
    log.info("Completed test run.")

    # Generate logs to test rotation
    for i in range(25500):
        log.debug(f"Debug message {i+1}")
        log.info(f"Info message {i+1}")
        log.warning(f"Warning message {i+1}")
        log.error(f"Error message {i+1}")
        log.critical(f"Critical message {i+1}")
