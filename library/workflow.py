from __future__ import print_function, unicode_literals

import os
import sys
import plistlib

from utils import decode, register_path
from workflow_version import Version
from workflow_data import WorkflowData
from workflow_item import WorkflowItem
from workflow_cache import WorkflowCache
from workflow_actions import WorkflowActions
from workflow_updater import WorkflowUpdater
from workflow_settings import WorkflowSettings


class Workflow:
    def __init__(self, defaults=None):
        self._environment = None
        self._directory = None
        self._data_directory = None
        self._cache_directory = None

        self._info = None
        self._name = None
        self._bundle = None
        self._version = None

        self._defaults = defaults or {}

        self._items = []
        self._actions = None

        self._data = None
        self._cache = None
        self._updater = None
        self._settings = None

    @property
    def actions(self):
        if not self._actions:
            self._actions = WorkflowActions(self)

        return self._actions

    @property
    def args(self):
        feedback = False
        args = [decode(arg) for arg in sys.argv[1:]]

        if len(args) and self.setting('actionable'):
            for arg in args:
                if arg in self.actions.keys():
                    feedback = self.actions.get(arg)()

            if feedback:
                self.feedback()
                sys.exit(0)

        return args

    @property
    def environment(self):
        if not self._environment:
            if not sys.stdout.isatty():
                self._environment = {
                    'version': decode(os.getenv('alfred_version')),
                    'version_build': int(os.getenv('alfred_version_build')),
                    'workflow_bundleid': decode(os.getenv('alfred_workflow_bundleid')),
                    'workflow_uid': decode(os.getenv('alfred_workflow_uid')),
                    'workflow_name': decode(os.getenv('alfred_workflow_name')),
                    'workflow_cache': decode(os.getenv('alfred_workflow_cache')),
                    'workflow_data': decode(os.getenv('alfred_workflow_data'))
                }
            else:
                self._environment = {}

        return self._environment

    @property
    def directory(self):
        if not self._directory:
            candidates = [
                os.path.abspath(os.getcwdu()),
                os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
            ]

            for candidate in candidates:
                path = decode(candidate)
                while True:
                    if os.path.exists(os.path.join(path, 'info.plist')):
                        self._directory = path
                        break
                    elif os.path.exists(os.path.join(path, 'settings.json')):
                        self._directory = path
                        break
                    elif path == '/':
                        break

                    path = os.path.dirname(path)

                if self._directory:
                    break

            if not self._directory:
                raise IOError('No info.plist for the workflow')

        return self._directory

    @property
    def data(self):
        if not self._data:
            self._data = WorkflowData(self)

        return self._data

    @property
    def cache(self):
        if not self._cache:
            self._cache = WorkflowCache(self)

        return self._cache

    @property
    def info(self):
        if not self._info:
            if os.path.exists(os.path.join(self.directory, 'info.plist')):
                self._info = plistlib.readPlist(os.path.join(self.directory, 'info.plist'))
            else:
                self._info = {}

        return self._info

    @property
    def name(self):
        if not self._name:
            if self.environment.get('workflow_name'):
                self._name = decode(self.environment.get('workflow_name'))
            elif self.info.get('name'):
                self._name = decode(self.info.get('name'))
            elif self.setting('name'):
                self._name = decode(self.setting('name'))
            else:
                self._name = 'workflow'

        return self._name

    @property
    def bundle(self):
        if not self._bundle:
            if self.environment.get('workflow_bundleid'):
                self._bundle = decode(self.environment.get('workflow_bundleid'))
            elif self.info.get('bundleid'):
                self._bundle = decode(self.info.get('bundleid'))
            elif self.setting('bundleid'):
                self._bundle = decode(self.setting('bundleid'))
            else:
                self._bundle = ''

        return self._bundle

    @property
    def version(self):
        if not self._version:
            version = None

            if self.setting('version'):
                version = self.setting('version')

            if not version:
                path = os.path.join(self.directory, 'version')
                if os.path.exists(path):
                    with open(path, 'rb') as handle:
                        version = handle.read()

            if version:
                self._version = Version(version)

        return self._version

    def setting(self, setting, *params):
        if not self._settings:
            self._settings = WorkflowSettings(os.path.join(self.directory, 'settings.json'), self._defaults)

        if len(params) == 0:
            return self._settings.get(setting)
        else:
            setting = self._settings.get(setting)
            for param in params:
                setting = setting[param]

            return setting

    def save_settings(self):
        self._settings.save()

    def update(self, force=False):
        if not self._updater:
            self._updater = WorkflowUpdater(self)

    def check_update(self, force=False):
        if not self._updater:
            self._updater = WorkflowUpdater(self)

        if self.setting('update', 'enabled'):
            frequency = int(self.setting('update', 'frequency'))
            if force or self.cache.read('.updater', None, frequency):
                self._updater.check_update()

    def item(self, title, subtitle, customizer=None):
        item = WorkflowItem(title, subtitle)

        if customizer:
            customizer(item)

        self._items.append(item)

    def feedback(self):
        sys.stdout.write('<?xml version="1.0" encoding="utf-8"?>\n')
        sys.stdout.write('<items>\n')

        for item in self._items:
            item.feedback()

        sys.stdout.write('</items>')
        sys.stdout.flush()

    @staticmethod
    def library(path):
        register_path(path)

    @staticmethod
    def notify(self, title, message):
        os.system('osascript -e \'display notification "{0}" "{1}"\''.format(title, message))

    @staticmethod
    def run(main, workflow):
        def with_info(item):
            item.icon = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'icons/sad.png')
            item.valid = False

        try:
            main(workflow)
        except Exception as ex:
            workflow.item('Oops, something went wrong',
                          'Workflow {0} failed with exception - {1}'.format(workflow.name, ex.message),
                          with_info)

            workflow.feedback()

        return 0
