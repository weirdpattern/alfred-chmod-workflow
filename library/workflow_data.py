import os

from utils import PickleSerializer, ensure_path, atomic_write, atomic


class SerializationException(Exception):
    """Serialization error"""


class WorkflowData:
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
            if self.workflow.environment.get('workflow_data'):
                self._directory = self.workflow.environment.get('workflow_data')
            elif self.workflow.environment.get('version_build') >= 652:
                self._directory = os.path.join(
                    os.path.expanduser('~/Library/Application Support/Alfred-3/Workflow Data/'),
                    self.workflow.bundle
                )
            elif self.workflow.environment.get('version_build') < 652:
                self._directory = os.path.join(
                    os.path.expanduser('~/Library/Application Support/Alfred-2/Workflow Data/'),
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

    def read(self, filename):
        path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
        with open(path, 'rb') as handler:
            return self.serializer.load(handler)

    def save(self, filename, data):
        @atomic
        def atomic_save():
            try:
                path = os.path.join(self.directory, '{0}.{1}'.format(filename, self.serializer.name or 'custom'))
                settings = os.path.join(self.workflow.directory, 'settings.json')
                if path == settings:
                    raise SerializationException('Settings file is maintained automatically')

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
