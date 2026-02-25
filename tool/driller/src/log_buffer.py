"""Log buffer for collecting and sending logs to backend"""
import logging
import threading
import time
from collections import deque
from datetime import datetime
from typing import Optional
import requests


class LogBuffer:
    """Buffers log records and sends them to backend periodically"""

    def __init__(self, job_id: int, backend_url: str, send_interval: int = 5):
        self.job_id = job_id
        self.backend_url = backend_url
        self.send_interval = send_interval
        self.logs = deque()
        self.lock = threading.Lock()
        self.running = False
        self.sender_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the background thread that sends logs periodically"""
        if self.running:
            return
        self.running = True
        self.sender_thread = threading.Thread(
            target=self._send_logs_loop,
            daemon=True
        )
        self.sender_thread.start()

    def stop(self):
        """Stop the background thread and send any remaining logs"""
        if not self.running:
            return
        self.running = False
        # Send remaining logs
        self._send_buffered_logs()
        if self.sender_thread:
            self.sender_thread.join(timeout=5)

    def add_log(self, level: str, message: str):
        """Add a log entry to the buffer"""
        with self.lock:
            self.logs.append({
                "timestamp": datetime.utcnow().isoformat(),
                "level": level,
                "message": message
            })

    def _send_logs_loop(self):
        """Background loop that sends logs at regular intervals"""
        while self.running:
            time.sleep(self.send_interval)
            self._send_buffered_logs()

    def _send_buffered_logs(self):
        """Send all buffered logs to the backend"""
        with self.lock:
            if not self.logs:
                return
            logs_to_send = list(self.logs)
            self.logs.clear()

        try:
            response = requests.post(
                f"{self.backend_url}/api/job-logs",
                json={
                    "job_id": self.job_id,
                    "logs": logs_to_send,
                },
                timeout=5.0
            )
            response.raise_for_status()
        except Exception as e:
            # Log errors locally but don't fail
            print(f"Failed to send logs for job {self.job_id}: {e}")


class LogBufferHandler(logging.Handler):
    """Logging handler that feeds logs to a LogBuffer"""

    def __init__(self, log_buffer: LogBuffer):
        super().__init__()
        self.log_buffer = log_buffer

    def emit(self, record: logging.LogRecord):
        """Handle a log record"""
        try:
            message = self.format(record)
            self.log_buffer.add_log(record.levelname, message)
        except Exception:
            self.handleError(record)
