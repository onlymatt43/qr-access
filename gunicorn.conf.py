import multiprocessing

# Sensible defaults for a small dyno/container; tune as needed
workers = int((multiprocessing.cpu_count() * 2) + 1)
threads = 2
worker_class = "gthread"
preload_app = True
bind = ":8000"
# Heroku/Render style proxy headers
forwarded_allow_ips = "*"
proxy_protocol = True
# Keep-alive tuning
timeout = 60
keepalive = 75
# Access logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
