from __future__ import print_function, unicode_literals

import os
import re
import sys
import json
import zlib
import time
import errno
import socket
import signal
import pickle
import cPickle
import threading
import unicodedata

from functools import wraps
from contextlib import contextmanager

try:
    from urllib import urlencode
    from urllib2 import Request, URLError, HTTPError, HTTPRedirectHandler, HTTPBasicAuthHandler, \
        HTTPPasswordMgrWithDefaultRealm, build_opener, install_opener, urlparse, urlopen
except ImportError:
    from urllib.error import URLError, HTTPError
    from urllib.parse import urlparse, urlencode
    from urllib.request import Request, HTTPBasicAuthHandler, HTTPRedirectHandler, HTTPPasswordMgrWithDefaultRealm, \
        build_opener, install_opener, urlopen


class AcquisitionError(Exception):
    """Locking error"""


class NoRedirectHttpHandler(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class PickleSerializer:
    def __init__(self):
        self._serializer = cPickle if sys.version_info[0] < 3 else pickle

    @property
    def name(self):
        return 'pickle'

    def load(self, handler):
        return self._serializer.load(handler)

    def dump(self, obj, handler):
        return self._serializer.dump(obj, handler, protocol=-1)


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


def atomic(func):
    @wraps(func)
    def handler(self, *args, **kwargs):
        if is_main_thread():
            caught_signal = []
            old_signal_handler = signal.getsignal(signal.SIGTERM)

            signal.signal(signal.SIGTERM, lambda s, f: caught_signal.__setitem__(0, (s, f)))

            func(*args, **kwargs)

            signal.signal(signal.SIGTERM, old_signal_handler)
            if len(caught_signal) > 0:
                signum, frame = caught_signal[0]
                if callable(old_signal_handler):
                    old_signal_handler(signum, frame)
                elif old_signal_handler == signal.SIG_DFL:
                    sys.exit(0)
        else:
            func(self, *args, **kwargs)

    return handler


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


def send_notification(title, message):
    command = "osascript -e 'display notification \"{1}\" with title \"{0}\"'"
    command = command.format(title.replace('"', r'\"'), message.replace('"', r'\"'))

    os.system(command)


def is_main_thread():
    return isinstance(threading.current_thread(), threading._MainThread)


def item_customizer(icon=None, valid=False, arg=None, autocomplete=None):
    icon = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'icons', icon) if icon else None

    def customize(item):
        item.arg = arg
        item.icon = icon
        item.valid = valid
        item.autocomplete = autocomplete

        return item

    return customize


def format_headers(headers):
    dictionary = {}

    for k, v in headers.items():
        if isinstance(k, unicode):
            k = k.encode('utf-8')

        if isinstance(v, unicode):
            v = v.encode('utf-8')

        dictionary[k.lower()] = v.lower()

    return dictionary


def request(method, url, content_type, data=None, params=None, headers=None, cookies=None,
            auth=None, redirection=True, timeout=60):
    socket.setdefaulttimeout(timeout)

    openers = []
    if not redirection:
        openers.append(NoRedirectHttpHandler())

    if auth:
        manager = HTTPPasswordMgrWithDefaultRealm()
        manager.add_password(None, url, auth['username'], auth['password'])
        openers.append(HTTPBasicAuthHandler(manager))

    opener = build_opener(*openers)
    install_opener(opener)

    headers = headers or {}
    if cookies:
        for cookie in cookies.keys():
            headers['Cookie'] = "{0}={1}".format(cookie, cookies[cookie])

    if 'user-agent' not in headers:
        headers['user-agent'] = 'Alfred-Workflow/1.17'

    encodings = [s.strip() for s in headers.get('accept-encoding', '').split(',')]
    if 'gzip' not in encodings:
        encodings.append('gzip')

    headers['accept-encoding'] = ', '.join(encodings)

    if method == 'POST' and not data:
        data = ''

    if data and isinstance(data, dict):
        data = urlencode(format_headers(data))

    headers = format_headers(headers)

    if isinstance(url, unicode):
        url = url.encode('utf-8')

    if params:
        scheme, netloc, path, query, fragment = urlparse.urlsplit(url)

        if query:
            url_params = urlparse.parse_qs(query)
            url_params.update(params)
            params = url_params

        query = urlencode(format_headers(params), doseq=True)
        url = urlparse.urlunsplit((scheme, netloc, path, query, fragment))

    try:
        response = urlopen(Request(url, data, headers))
        response_headers = response.info()

        content = response.read()
        if ('gzip' in response_headers.get('content-encoding', '') or
                    'gzip' in response_headers.get('transfer-encoding', '')):
            content = unzip(content)

        if content_type.lower() == 'json':
            return json.loads(content, 'utf-8')

        return content
    except (HTTPError, URLError):
        send_notification('Workflow', 'Error while calling {0}'.format(url))
        if content_type.lower() == 'json':
            return {}

        return ''


def unzip(content):
    decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
    return decoder.decompress(content)
