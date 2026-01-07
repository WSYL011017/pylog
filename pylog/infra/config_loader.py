import yaml
import logging
from typing import Dict, Any, List
from pylog.core.logger import LoggerConfig
from pylog.appenders.console import ConsoleAppender
from pylog.formatters.json_formatter import JSONFormatter
from pylog.formatters.pattern_formatter import PatternFormatter

from pylog.appenders.rolling_file import RollingFileAppender, SizeBasedTriggeringPolicy, TimeBasedTriggeringPolicy, DefaultRolloverStrategy, parse_size
from pylog.appenders.failover import FailoverAppender
from pylog.appenders.socket_appender import SocketAppender
from pylog.appenders.http_appender import HTTPAppender
from pylog.appenders.kafka_appender import KafkaAppender
from pylog.appenders.buffering import BufferingAppender

class ConfigLoader:
    """
    Loads configuration from YAML files.
    """
    def load_file(self, path: str) -> (Dict[str, LoggerConfig], Dict[str, Any]):
        with open(path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        self.validate_schema(config_dict)
        return self.parse(config_dict)

    def validate_schema(self, config_dict: Dict[str, Any]):
        """
        Validates the configuration dictionary against a basic schema.
        Raises ValueError if configuration is invalid.
        """
        if not isinstance(config_dict, dict):
            raise ValueError("Configuration root must be a dictionary.")
            
        cfg = config_dict.get('configuration', config_dict)
        if not isinstance(cfg, dict):
            raise ValueError("'configuration' section must be a dictionary.")
            
        # Check appenders
        appenders = cfg.get('appenders', {})
        if not isinstance(appenders, dict):
             raise ValueError("'appenders' section must be a dictionary.")
             
        for name, app_conf in appenders.items():
            if not isinstance(app_conf, dict):
                raise ValueError(f"Appender '{name}' configuration must be a dictionary.")
            
        # Check loggers
        loggers = cfg.get('loggers', {})
        if not isinstance(loggers, dict):
             raise ValueError("'loggers' section must be a dictionary.")

    def parse(self, config_dict: Dict[str, Any]) -> (Dict[str, LoggerConfig], Dict[str, Any]):
        cfg = config_dict.get('configuration', {})
        if not cfg:
            cfg = config_dict

        global_settings = {
            "status": cfg.get("status", "INFO"),
            "monitorInterval": cfg.get("monitorInterval", 0),
            "async_queue": cfg.get("async_queue", {})
        }

        appenders = self._parse_appenders(cfg.get('appenders', {}))
        loggers = self._parse_loggers(cfg.get('loggers', {}), appenders)
        
        return loggers, global_settings

    def _parse_appenders(self, appenders_conf: Dict[str, Any]) -> Dict[str, Any]:
        appenders = {}
        # Pass 1: Concrete Appenders
        for key, conf in appenders_conf.items():
            if 'failover' in key.lower() or conf.get('type') == 'Failover':
                continue
            self._create_appender(key, conf, appenders)
            
        # Pass 2: Composite Appenders (Failover)
        for key, conf in appenders_conf.items():
            if 'failover' in key.lower() or conf.get('type') == 'Failover':
                self._create_failover_appender(key, conf, appenders)
                
        return appenders

    def _create_appender(self, key: str, conf: Dict[str, Any], appenders: Dict[str, Any]):
        name = conf.get('name', key)
        
        # Formatter
        formatter = JSONFormatter() # Default
        if 'json_layout' in conf:
            layout_conf = conf['json_layout']
            formatter = JSONFormatter(
                compact=layout_conf.get('compact', True),
                event_eol=layout_conf.get('event_eol', True),
                masked_keys=layout_conf.get('masked_keys', [])
            )
        elif 'pattern_layout' in conf:
            layout_conf = conf['pattern_layout']
            pattern = layout_conf.get('pattern', "%d [%t] %p %c - %m%n")
            formatter = PatternFormatter(pattern=pattern)
        
        appender = None
        if 'console' in key.lower() or conf.get('type') == 'Console':
            target = conf.get('target', 'SYSTEM_OUT')
            appender = ConsoleAppender(name, formatter, target)
        
        elif 'rolling_file' in key.lower() or conf.get('type') == 'RollingFile':
            file_name = conf.get('fileName')
            file_pattern = conf.get('filePattern')
            
            policies = []
            policy_conf = conf.get('policies', {})
            if 'size_based' in policy_conf:
                size_str = policy_conf['size_based'].get('size', '10 MB')
                policies.append(SizeBasedTriggeringPolicy(parse_size(size_str)))
            if 'time_based' in policy_conf:
                interval = int(policy_conf['time_based'].get('interval', 1))
                policies.append(TimeBasedTriggeringPolicy(interval=interval))
            
            strategy_conf = conf.get('strategy', {})
            max_files = int(strategy_conf.get('max', 10))
            strategy = DefaultRolloverStrategy(max_files, file_pattern)
            
            # Check for multiprocess lock setting
            use_lock = conf.get('use_multiprocess_lock', False)
            
            appender = RollingFileAppender(
                name=name,
                formatter=formatter,
                file_name=file_name,
                file_pattern=file_pattern,
                policies=policies,
                strategy=strategy,
                use_multiprocess_lock=use_lock
            )
        
        elif 'socket' in key.lower() or conf.get('type') == 'Socket':
            host = conf.get('host', 'localhost')
            port = int(conf.get('port', 9000))
            protocol = conf.get('protocol', 'TCP')
            appender = SocketAppender(name, host, port, protocol, formatter)

        elif 'http' in key.lower() or conf.get('type') == 'HTTP':
            url = conf.get('url')
            if url:
                method = conf.get('method', 'POST')
                headers = conf.get('headers', {})
                appender = HTTPAppender(name, url, method, headers, formatter)

        elif 'kafka' in key.lower() or conf.get('type') == 'Kafka':
            bootstrap_servers = conf.get('bootstrap_servers', 'localhost:9092')
            topic = conf.get('topic', 'logs')
            async_send = conf.get('async_send', True)
            producer_config = conf.get('producer_config', {})
            appender = KafkaAppender(name, bootstrap_servers, topic, formatter, async_send, producer_config)

        if appender:
            if conf.get('buffered_io', False):
                batch_size = int(conf.get('batch_size', 100))
                flush_interval = float(conf.get('flush_interval', 1.0))
                appender = BufferingAppender(appender, batch_size, flush_interval)

            appender.start()
            appenders[name] = appender

    def _create_failover_appender(self, key: str, conf: Dict[str, Any], appenders: Dict[str, Any]):
        name = conf.get('name', key)
        primary_ref = conf.get('primary')
        failover_refs = conf.get('failovers', [])
        retry_interval = int(conf.get('retry_interval', 60))
        
        if not primary_ref or primary_ref not in appenders:
            print(f"Error: Primary appender '{primary_ref}' for FailoverAppender '{name}' not found.")
            return

        primary = appenders[primary_ref]
        failovers = []
        for ref in failover_refs:
            if ref in appenders:
                failovers.append(appenders[ref])
            else:
                print(f"Warning: Failover appender '{ref}' not found.")
        
        appender = FailoverAppender(name, primary, failovers, retry_interval)
        appender.start()
        appenders[name] = appender

    def _parse_loggers(self, loggers_conf: Dict[str, Any], appenders: Dict[str, Any]) -> Dict[str, LoggerConfig]:
        configs = {}
        
        for name, conf in loggers_conf.items():
            if name == 'root':
                root_config = LoggerConfig(
                    name="root", 
                    level=self._parse_level(conf.get('level', 'INFO')),
                    additivity=False
                )
                self._attach_appenders(root_config, conf, appenders)
                configs['root'] = root_config
            elif name == 'logger':
                # Handle list format as per spec
                if isinstance(conf, list):
                    for l_conf in conf:
                        l_name = l_conf.get('name')
                        if l_name:
                            lc = LoggerConfig(
                                name=l_name,
                                level=self._parse_level(l_conf.get('level', 'INFO')),
                                additivity=l_conf.get('additivity', True)
                            )
                            self._attach_appenders(lc, l_conf, appenders)
                            configs[l_name] = lc
            else:
                # Handle dict key as logger name
                lc = LoggerConfig(
                    name=name,
                    level=self._parse_level(conf.get('level', 'INFO')),
                    additivity=conf.get('additivity', True)
                )
                self._attach_appenders(lc, conf, appenders)
                configs[name] = lc
                        
        return configs

    def _attach_appenders(self, config: LoggerConfig, conf: Dict[str, Any], appenders: Dict[str, Any]):
        refs = conf.get('appender_refs', [])
        for ref in refs:
            ref_name = ref.get('ref')
            if ref_name in appenders:
                config.add_appender(appenders[ref_name])
            else:
                print(f"Warning: AppenderRef {ref_name} not found")

    def _parse_level(self, level_str: str) -> int:
        if not level_str:
            return logging.INFO
        
        try:
            level = level_str.upper()
            # logging.getLevelName returns the level integer if passed a valid level name
            # But if it returns a string (like "Level X"), it means it might be custom or mapped differently depending on python version
            # However, safe way is accessing logging._nameToLevel or getattr(logging, level)
            # Standard method:
            val = logging.getLevelName(level)
            if isinstance(val, int):
                return val
            # For "Level X" return (Python < 3.4 behavior sometimes) or if invalid name
            # In newer python, getLevelName returns "Level {level}" string if input is int, 
            # or the int if input is string. If input is invalid string, it returns "Level {input}".
            
            # Let's try direct mapping first for safety
            name_to_level = logging._nameToLevel
            if level in name_to_level:
                return name_to_level[level]
                
            # Fallback
            print(f"Warning: Unknown log level '{level_str}'. Defaulting to INFO.")
            return logging.INFO
        except Exception:
             print(f"Error parsing log level '{level_str}'. Defaulting to INFO.")
             return logging.INFO
