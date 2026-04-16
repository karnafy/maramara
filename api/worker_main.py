"""RQ worker entry point.

Run with:
    python worker_main.py          # foreground worker
    rq worker maramara-segments    # native RQ CLI
"""
from __future__ import annotations

import os
import sys

from redis import Redis
from rq import Queue, Worker

from config import get_settings
from db.supabase_client import init_supabase_client
from utils.logger import configure_logging


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_supabase_client(settings)

    conn = Redis.from_url(settings.redis_url)
    queues = [Queue("maramara-segments", connection=conn)]
    worker = Worker(queues, connection=conn, name=os.getenv("WORKER_NAME", "maramara-worker"))
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    sys.exit(main())
