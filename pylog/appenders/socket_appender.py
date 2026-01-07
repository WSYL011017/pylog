import socket
import struct
import time
import logging
from typing import Optional
from .base import Appender
from pylog.formatters.base import Formatter
from pylog.core.log_event import LogEvent

class SocketAppender(Appender):
    """
    Appends logs to a network socket (TCP/UDP).
    """
    def __init__(self, name: str, host: str, port: int, protocol: str = 'TCP', formatter: Optional[Formatter] = None):
        super().__init__(name, formatter)
        self.host = host
        self.port = port
        self.protocol = protocol.upper()
        self.sock: Optional[socket.socket] = None
        self._retry_interval = 5.0
        self._last_retry_time = 0
        
    def start(self):
        super().start()
        self._connect()

    def stop(self):
        super().stop()
        self._close_socket()

    def _connect(self):
        if self.sock:
            return
            
        try:
            if self.protocol == 'TCP':
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.host, self.port))
            elif self.protocol == 'UDP':
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            else:
                raise ValueError(f"Unknown protocol: {self.protocol}")
        except Exception as e:
            # print(f"Failed to connect to {self.host}:{self.port}: {e}")
            self.sock = None

    def _close_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def append(self, event: LogEvent):
        if not self.started:
            return
        
        try:
            if self.formatter:
                data = self.formatter.format(event)
                if isinstance(data, str):
                    data = data.encode('utf-8')
            else:
                data = str(event.get_message()).encode('utf-8') + b'\n'
            
            self._send_bytes(data)
                
        except Exception as e:
            # print(f"Socket send error: {e}")
            self._close_socket()

    def write_raw(self, content: str):
        """
        Writes raw string content to the socket. 
        Used by BufferingAppender.
        """
        if not self.started:
            return
        try:
            self._send_bytes(content.encode('utf-8'))
        except Exception:
            self._close_socket()

    def _send_bytes(self, data: bytes):
        # Reconnect logic for TCP
        if self.sock is None:
            now = time.time()
            if now - self._last_retry_time >= self._retry_interval:
                self._last_retry_time = now
                self._connect()
            
            if self.sock is None:
                return # Still offline

        if self.protocol == 'TCP':
            self.sock.sendall(data)
        else:
            # UDP
            self.sock.sendto(data, (self.host, self.port))
