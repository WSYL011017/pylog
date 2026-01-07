from typing import Dict, Union, List, Optional
import logging
import os
from pylog.core.logger import Logger, LoggerConfig
from pylog.infra.config_loader import ConfigLoader
from pylog.core.async_queue import AsyncQueueHandler
from pylog.infra.reloader import HotReloader

class LogManager:
    """
    Central management class for PyLog.
    """
    _configs: Dict[str, LoggerConfig] = {}
    _loggers: Dict[str, Logger] = {}
    _root_config: LoggerConfig = LoggerConfig("root", logging.INFO)
    _async_queue: Optional[AsyncQueueHandler] = None
    _reloader: Optional[HotReloader] = None
    _initialized: bool = False

    @classmethod
    def _try_autoload_config(cls):
        """
        Attempt to auto-load configuration from default files.
        """
        if cls._initialized:
            return

        candidates = ["pylog_config.yaml", "pylog.yaml", "pylog.json"]
        for f in candidates:
            if os.path.exists(f):
                # print(f"PyLog: Auto-loading configuration from {f}")
                cls.load_config(f)
                return
        
        # Mark initialized even if no config found (use defaults)
        cls._initialized = True
    
    @classmethod
    def _get_async_queue(cls) -> AsyncQueueHandler:
        if cls._async_queue is None:
            cls._async_queue = AsyncQueueHandler()
            cls._async_queue.start()
        return cls._async_queue

    @classmethod
    def configure_async_queue(cls, queue_size: int = 4096, full_policy: str = "Discard"):
        """
        Configure the global async queue.
        Must be called before any logging occurs, or it will restart the queue.
        """
        if cls._async_queue:
            cls._async_queue.stop()
        cls._async_queue = AsyncQueueHandler(queue_size=queue_size, full_policy=full_policy)
        cls._async_queue.start()
        
        # Update existing loggers to use the new queue
        for logger in cls._loggers.values():
            logger.async_queue = cls._async_queue

    @classmethod
    def load_config(cls, files: Union[str, List[str]], monitor_interval: int = 0):
        """
        Load configuration from file(s).
        """
        cls._initialized = True
        if isinstance(files, str):
            files = [files]
            
        loader = ConfigLoader()
        
        for f in files:
            try:
                configs, global_settings = loader.load_file(f)
                cls._configs.update(configs)
                if 'root' in configs:
                    cls._root_config = configs['root']
                
                # Apply Global Settings
                # 1. Async Queue
                aq_conf = global_settings.get("async_queue", {})
                if aq_conf:
                    size = aq_conf.get("size", 4096)
                    policy = aq_conf.get("full_policy", "Discard")
                    cls.configure_async_queue(queue_size=size, full_policy=policy)
                
                # 2. Monitor Interval (Override if provided in arg, else use config)
                if monitor_interval == 0:
                    monitor_interval = global_settings.get("monitorInterval", 0)

            except Exception as e:
                print(f"Failed to load config {f}: {e}")
        
        # Update existing loggers
        for name, logger in cls._loggers.items():
            logger.config = cls._get_config_for(name)

        # Setup Hot Reload
        if monitor_interval > 0:
            if cls._reloader:
                cls._reloader.stop()
            
            # Callback simply reloads the same files
            # Note: Avoid infinite recursion or re-registering reloader
            def reload_callback():
                print("Reloading configuration...")
                cls.load_config(files, monitor_interval=0) # recursive reload without re-enabling monitor

            cls._reloader = HotReloader(reload_callback, files)
            cls._reloader.start()

    @classmethod
    def get_logger(cls, name: Union[str, type] = "root") -> Logger:
        """
        Get or create a logger.
        """
        if not cls._initialized:
            cls._try_autoload_config()

        if isinstance(name, type):
            name = name.__module__ + "." + name.__qualname__
            
        if name in cls._loggers:
            return cls._loggers[name]
            
        config = cls._get_config_for(name)
        # In this architecture, we use AsyncQueue by default for all loggers
        # unless configured otherwise (future).
        logger = Logger(name, config, async_queue=cls._get_async_queue())
        cls._loggers[name] = logger
        return logger

    @classmethod
    def _get_config_for(cls, name: str) -> LoggerConfig:
        if name in cls._configs:
            return cls._configs[name]
            
        # Hierarchical search
        parts = name.split('.')
        for i in range(len(parts) - 1, 0, -1):
            key = ".".join(parts[:i])
            if key in cls._configs:
                return cls._configs[key]
                
        return cls._root_config

    @classmethod
    def shutdown(cls):
        """
        Shutdown the logging system.
        """
        if cls._async_queue:
            cls._async_queue.stop()
            cls._async_queue = None
            
        # Stop all appenders
        # Collect unique appenders
        unique_appenders = set()
        for config in cls._configs.values():
            for appender in config.appenders:
                unique_appenders.add(appender)
        
        # Also check root config if not in _configs
        for appender in cls._root_config.appenders:
            unique_appenders.add(appender)
            
        for appender in unique_appenders:
            try:
                if hasattr(appender, 'stop'):
                    appender.stop()
            except Exception as e:
                print(f"Error stopping appender {appender}: {e}")
        
        cls._configs.clear()
        cls._loggers.clear()
