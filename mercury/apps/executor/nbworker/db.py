import sys
from apps.executor.models import Worker
from apps.notebooks.models import Notebook
from django.utils.timezone import make_aware
import logging

from datetime import datetime, timedelta

from apps.executor.nbworker.utils import WorkerState

log = logging.getLogger(__name__)


class DBClient:
    def __init__(self, notebook_id, session_id, worker_id):
        self.notebook_id = notebook_id
        self.session_id = session_id
        self.worker_id = worker_id
        self.worker = None  # db object
        self.state = WorkerState.Unknown
        self.load_notebook()

    def load_notebook(self):
        try:
            log.debug(f"Load notebook id={self.notebook_id}")
            self.notebook = Notebook.objects.get(pk=self.notebook_id)
        except Exception:
            log.exception("Expetion when notebook load, quit")
            sys.exit(0)

    def is_presentation(self):
        try:
            log.debug("Check if notebook is presentation")
            return self.notebook.output == "slides"
        except Exception:
            log.exception("Exception when check if notebook is presentation")
        return False

    def worker_state(self):
        return self.state

    def set_worker_state(self, new_state):
        try:
            log.debug(f"Worker id={self.worker_id} set state {new_state}")
            self.state = new_state
            if self.worker_exists() and self.worker is not None:
                self.worker.state = new_state
                self.worker.save()
        except Exception:
            log.exception("Exception when set worker state")

    @staticmethod
    def delete_worker_in_db(worker_id):
        try:
            log.debug(f"Delete worker id={worker_id}")
            Worker.objects.get(pk=worker_id).delete()
        except Exception:
            log.exception(f"Exception when delete worker")

    def delete_worker(self):
        DBClient.delete_worker_in_db(self.worker_id)

    def delete_stale_workers(self):
        try:
            log.debug(
                (
                    "Delete stale workers, "
                    f"notebook_id={self.notebook_id}, "
                    f"session_id={self.session_id}, "
                    f"worker_id<{self.worker_id}"
                )
            )
            workers = Worker.objects.filter(
                session_id=self.session_id,
                notebook__id=self.notebook_id,
                pk__lt=self.worker_id,
            )
            workers.delete()
        except Exception as e:
            log.exception("Exception when delete stale workers")

    def worker_exists(self):
        try:
            log.debug(f"Worker id={self.worker_id} exists")
            self.worker = Worker.objects.get(pk=self.worker_id)
        except Worker.DoesNotExist as e:
            log.exception(f"Worker id={self.worker_id} does not exists, quit")
            sys.exit(1)
        return True

    def is_worker_stale(self):
        try:
            log.debug(f"Check worker id={self.worker_id} is stale")
            self.worker = Worker.objects.get(pk=self.worker_id)
            return self.worker.updated_at < make_aware(
                datetime.now() - timedelta(minutes=1)
            )
        except Exception:
            log.exception(
                f"Exception when check if worker id={self.worker_id} is stale"
            )
        return True
