"""Periodic queue reconciliation and reference-safe retention service."""

import logging
import time

from services.api.queueing import reconcile_jobs
from services.api.retention import purge_expired
from services.api.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("sponge.maintenance")


def run_once():
    jobs = reconcile_jobs()
    retention = purge_expired()
    logger.info("maintenance jobs=%s retention=%s", jobs, retention)


if __name__ == "__main__":
    while True:
        try:
            run_once()
            delay = settings.retention_interval_seconds
        except Exception:
            logger.exception("maintenance cycle failed")
            delay = min(30, settings.retention_interval_seconds)
        time.sleep(delay)
