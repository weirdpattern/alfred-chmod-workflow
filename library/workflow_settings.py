import os
import json

from utils import atomic_write, atomic, lock


class WorkflowSettings(dict):
    def __init__(self, path, defaults=None):
        super(WorkflowSettings, self).__init__()

        self._path = path
        self._original = {}
        self._defaults = defaults or {}

        for key, value in defaults.items():
            self._original[key] = value

        if os.path.exists(path):
            with open(path, 'rb') as handle:
                for key, value in json.load(handle, encoding='utf-8').items():
                    self._original[key] = value

        self.update(self._original)

    def save(self):
        @atomic
        def atomic_save():
            try:
                data = {}
                data.update(self)

                with lock(self._path):
                    with atomic_write(self._path, 'wb') as handle:
                        json.dump(data, handle, sort_keys=True, indent=2, encoding='utf-8')

                return True
            except (OSError, IOError):
                return False

        return atomic_save(self)

    def update(self, *args, **kwargs):
        super(WorkflowSettings, self).update(*args, **kwargs)
        self.save()

    def setdefault(self, key, value=None):
        results = super(WorkflowSettings, self).setdefault(key, value)
        self.save()

        return results

    def __setitem__(self, key, value):
        if self._original.get(key) != value:
            super(WorkflowSettings, self).__setitem__(key, value)
            self.save()

    def __delitem__(self, key):
        super(WorkflowSettings, self).__delitem__(key)
        self.save()
