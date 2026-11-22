from __future__ import annotations

import threading
import time
from pathlib import Path

from woomba.db import connect
from woomba.jobs import next_queued_job, update_job
from woomba.models import JobStatus
from woomba.paths import db_path
from woomba.workers.runner import run_job

_stop = threading.Event()
_thread: threading.Thread | None = None


def start_worker(library_root: Path) -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()

    def _loop() -> None:
        conn = connect(db_path(library_root))
        while not _stop.is_set():
            job = next_queued_job(conn)
            if job is None:
                time.sleep(0.4)
                continue
            run_job(conn, library_root, job.id)

    _thread = threading.Thread(target=_loop, name="woomba-worker", daemon=True)
    _thread.start()


def stop_worker() -> None:
    _stop.set()


def cancel_job(conn, job_id: str) -> None:
    update_job(conn, job_id, status=JobStatus.cancelled)
