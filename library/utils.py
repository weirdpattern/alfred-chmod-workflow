from __future__ import print_function, unicode_literals

import os
import re
import sys
import time
import errno
import signal
import pickle
import cPickle
import unicodedata

from contextlib import contextmanager


class AcquisitionError(Exception):
    """Locking error"""


class lock:
    def __init__(self, path, timeout=0, delay=0.05):
        self.file = path + '.lock'
        self.timeout = timeout
        self.delay = delay

        self.locked = False

    def acquire(self, blocking=True):
        start = time.time()
        while True:
            try:
                fd = os.open(self.file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                with os.fdopen(fd, 'w') as fd:
                    fd.write(str('{0}'.format(os.getpid())))
                break
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise
                if self.timeout and (time.time() - start) >= self.timeout:
                    raise AcquisitionError('Lock acquisition timed out')
                if not blocking:
                    return False
                time.sleep(self.delay)

        self.locked = True
        return True

    def release(self):
        self.locked = False
        os.unlink(self.file)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, type, value, traceback):
        self.release()

    def __del__(self):
        if self.locked:
            self.release()


class atomic:
    def __init__(self, func, class_name=''):
        self.func = func
        self._caught_signal = None

    def signal_handler(self, signum, frame):
        self._caught_signal = (signum, frame)

    def __call__(self, *args, **kwargs):
        self._caught_signal = None
        self.old_signal_handler = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.func(*args, **kwargs)

        signal.signal(signal.SIGTERM, self.old_signal_handler)
        if self._caught_signal is not None:
            signum, frame = self._caught_signal
            if callable(self.old_signal_handler):
                self.old_signal_handler(signum, frame)
            elif self.old_signal_handler == signal.SIG_DFL:
                sys.exit(0)

    def __get__(self, obj=None, klass=None):
        return self.__class__(self.func.__get__(obj, klass), klass.__name__)


class PickleSerializer:
    def __init__(self):
        self._serializer = cPickle if sys.version_info[0] < 3 else pickle

    @property
    def name(self):
        return 'pickle'

    def load(self, handler):
        return self._serializer.load(handler)

    def dump(self, object, handler):
        return self._serializer.dump(object, handler, protocol=-1)


@contextmanager
def atomic_write(path, mode):
    suffix = '.aw.temp'
    filepath = path + suffix
    with open(filepath, mode) as handler:
        try:
            yield handler
            os.rename(filepath, path)
        finally:
            try:
                os.remove(filepath)
            except (OSError, IOError):
                pass


def decode(text, normalization='NFC'):
    if text and not isinstance(text, unicode):
        text = text.decode('unicode-escape')
        return unicodedata.normalize(normalization, text)

    return text


def ensure_path(path):
    if not os.path.exists(path):
        os.makedirs(path)

    return path


def parse_version(string):
    version_matcher = re.compile(r'([0-9\.]+)([-+].+)?').match

    if string.startswith('v'):
        match = version_matcher(string[1:])
    else:
        match = version_matcher(string)

    if not match:
        raise ValueError('Invalid version (format): {0}'.format(string))

    parts = match.group(1).split('.')
    suffix = match.group(2)

    major = int(parts.pop(0))
    minor = int(parts.pop(0)) if len(parts) else 0
    patch = int(parts.pop(0)) if len(parts) else 0

    if not len(parts) == 0:
        raise ValueError('Invalid version (too long): {0}'.format(string))

    build = None
    release = None
    if suffix:
        parts = suffix.split('+')
        release = parts.pop(0)
        if release.startswith('-'):
            release = release[1:]
        else:
            raise ValueError('Invalid type (must start with -): {0}'.format(string))

        if len(parts):
            build = parts.pop(0)

    return major, minor, patch, release, build


def register_path(path):
    sys.path.insert(0, path)
