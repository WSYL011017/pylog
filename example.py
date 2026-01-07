import sys
import os

# Add current dir to path
sys.path.insert(0, os.getcwd())

import pylog
from pylog import LogManager, ThreadContext, Marker

def main():
    print("Loading config...")
    LogManager.load_config("pylog_config.yaml")
    
    logger = pylog.get_logger("my.app")
    
    print("Logging info...")
    logger.info("Application started")
    
    with ThreadContext.scope(req_id="12345", user="admin"):
        logger.info("Processing request", action="login")
        
        SECURITY = Marker("SECURITY")
        logger.info("Security check passed", marker=SECURITY)
        
        try:
            1 / 0
        except ZeroDivisionError:
            logger.exception("Calculation failed")

    # Test lazy evaluation
    def slow_compute():
        return "Computed Result"
        
    logger.debug("Lazy: {}", slow_compute)

    LogManager.shutdown()

if __name__ == "__main__":
    main()
