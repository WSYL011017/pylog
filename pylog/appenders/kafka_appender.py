from typing import Optional, Dict
from .base import Appender
from pylog.formatters.base import Formatter
from pylog.core.log_event import LogEvent

try:
    from confluent_kafka import Producer
except ImportError:
    Producer = None

class KafkaAppender(Appender):
    """
    Appends logs to a Kafka topic using confluent-kafka.
    """
    def __init__(self, 
                 name: str, 
                 bootstrap_servers: str, 
                 topic: str, 
                 formatter: Optional[Formatter] = None, 
                 async_send: bool = True,
                 producer_config: Optional[Dict] = None):
        super().__init__(name, formatter)
        
        if Producer is None:
            raise ImportError("confluent-kafka is not installed. Run 'pip install confluent-kafka'")
            
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.async_send = async_send
        self.producer: Optional[Producer] = None
        
        self._config = {'bootstrap.servers': bootstrap_servers}
        if producer_config:
            self._config.update(producer_config)

    def start(self):
        super().start()
        try:
            self.producer = Producer(self._config)
        except Exception as e:
            print(f"KafkaAppender: Failed to create producer: {e}")
            self.started = False

    def stop(self):
        if self.producer:
            # Flush any outstanding messages
            self.producer.flush(timeout=5.0)
        super().stop()

    def append(self, event: LogEvent):
        if not self.started or not self.producer:
            return

        try:
            if self.formatter:
                value = self.formatter.format(event)
            else:
                value = str(event.get_message())
                
            if isinstance(value, str):
                value = value.encode('utf-8')
            
            # Use logger name as key for partitioning
            key = event.logger_name.encode('utf-8') if event.logger_name else None
            
            self.producer.produce(self.topic, value=value, key=key, on_delivery=self._delivery_report)
            
            if not self.async_send:
                self.producer.flush()
            else:
                # Trigger callbacks from previous produce calls
                self.producer.poll(0)
                
        except Exception as e:
            # Avoid recursive logging errors
            # print(f"KafkaAppender: Error producing message: {e}")
            pass

    def _delivery_report(self, err, msg):
        """Called once for each message produced to indicate delivery result."""
        if err is not None:
            # print(f"Message delivery failed: {err}")
            pass
