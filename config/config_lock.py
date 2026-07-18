"""Shared lock for thread-safe config.yaml access."""
import threading

config_lock = threading.Lock()
