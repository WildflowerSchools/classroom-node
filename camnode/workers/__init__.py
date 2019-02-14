import os

from celery import Celery


app = Celery()

app.conf.enable_utc = True


def redis_info():
    bits = []
    if "QUEUE_REDIS_PASS" in os.environ:
        bits.append(':')
        bits.append(os.environ["QUEUE_REDIS_PASS"])
        bits.append('@')
    bits.append(os.environ.get("QUEUE_REDIS_HOST", "localhost"))
    if "QUEUE_REDIS_PORT" in os.environ:
        bits.append(':')
        bits.append(os.environ["QUEUE_REDIS_PORT"])
    return "".join(bits)


app.conf.result_backend = f"redis://{redis_info()}/{os.environ.get('QUEUE_RESULTS_REDIS_DB', '0')}"
app.conf.broker_url = f"redis://{redis_info()}/{os.environ.get('QUEUE_BROKER_REDIS_DB', '1')}"
app.conf.redis_max_connections = 4
app.conf.redis_socket_timeout = 10
app.conf.result_expires = 60 * 60 * 4  # 4 hours
app.autodiscover_tasks(["camnode.workers.honeycomb"])
