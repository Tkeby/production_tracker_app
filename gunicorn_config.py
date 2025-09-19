bind = "127.0.0.1:8000"
workers = 2  # (CPU cores * 2) + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
daemon = False

# Logging
accesslog = "/home/deploy/production_tracker/gunicorn_access.log"
errorlog = "/home/deploy/production_tracker/gunicorn_error.log"
loglevel = "info"
