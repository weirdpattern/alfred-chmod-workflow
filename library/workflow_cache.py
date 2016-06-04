import os
import time
from utils import PickleSerializer, ensure_path, atomic_write, atomic


class WorkflowCache:
    def __init__(self, workflow):
        self._workflow = workflow
        self._directory = None
        self._serializer = PickleSerializer()

    @property
    def workflow(self):
        return self._workflow

    @property
    def directory(self):
        if not self._directory:
            if self.workflow.environment.get('workflow_cache'):
                self._directory = self.workflow.environment.get('workflow_cache')
            elif self.workflow.environment.get('version_build') >= 652:
                self._directory = os.path.join(
                    os.path.expanduser('~/Library/Caches/com.runningwithcrayons.Alfred-3/Workflow Data/'),
                    self.workflow.bundle
                )
            elif self.workflow.environment.get('version_build') < 652:
                self._directory = os.path.join(
                    os.path.expanduser('~/Library/Caches/com.runningwithcrayons.Alfred-2/Workflow Data/'),
                    self.workflow.bundle
                )

        return ensure_path(self._directory)

    @property
    def serializer(self):
        return self._serializer

    @serializer.setter
    def serializer(self, serializer):
        getattr(serializer, 'name')
        self._serializer = serializer

    def stale(self, filename, threshold):
        age = 0
        path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
        if os.path.exists(path):
            age = time.time() - os.stat(path).st_mtime

        return age > threshold > 0

    def read(self, filename, regenerator, threshold=60):
        path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))

        if os.path.exists(path) and not self.stale(filename, threshold):
            with open(path, 'rb') as handle:
                return self.serializer.load(handle)

        if not regenerator:
            return None

        data = regenerator()
        self.save(filename, data)

        return data

    def save(self, filename, data):
        @atomic
        def atomic_save():

            try:
                path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
                with atomic_write(path, 'wb') as handle:
                    self.serializer.dump(data, handle)

                return True
            except (OSError, IOError):
                return False

        return atomic_save(self)

    def clear(self, filename):
        path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
        if os.path.exists(path):
            os.unlink(path)
            return True

        return False

