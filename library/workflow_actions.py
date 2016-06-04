import subprocess

from utils import item_customizer


class WorkflowActions(dict):
    descriptions = {'--update': 'Use this option to force an update',
                    '--check-for-update': 'Use this option to check for updates',
                    '--enable-updates': 'Use this option to enable updates',
                    '--disable-updates': 'Use this option to disable updates',
                    '--do-daily-updates': 'Use this option to allow the workflow to check for updates daily',
                    '--do-weekly-updates': 'Use this option to allow the workflow to check for updates weekly',
                    '--do-monthly-updates': 'Use this option to allow the workflow to check for updates monthly',
                    '--do-yearly-updates': 'Use this option to allow the workflow to check for updates yearly',
                    '--include-prereleases': 'Use this option to allow the workflow to update using a prereleases',
                    '--exclude-prereleases': 'Use this option to prevent the workflow from updating using prereleases'}

    def __init__(self, workflow):
        super(WorkflowActions, self).__init__()

        self.workflow = workflow
        self.update_keys = ['--update', '--check-for-update']

        self['--help'] = self.show_help()
        self['--version'] = self.show_version()

        self['--update-settings'] = self.show_update_settings()

        if workflow.setting('update'):
            settings = workflow.setting('update')
            self['--update-help'] = self.show_update_help()

            self['--update'] = self.install_update()
            self['--check-for-update'] = self.check_update()

            self.configure_update_mode_settings(settings)
            self.configure_update_frequency_settings(settings)
            self.configure_update_prereleases_settings(settings)

    def show_help(self):
        def display():
            if self.workflow.setting('help'):
                subprocess.call(['open', self.workflow.setting('help')])
            else:
                self.workflow.item('Not available', 'Workflow: {0}'.format(self.workflow.name),
                                   item_customizer('sad.png'))

            return True

        return display

    def show_version(self):
        def display():
            if self.workflow.version:
                self.workflow.item('{0}'.format(str(self.workflow.version)), 'Workflow: {0}'.format(self.workflow.name),
                                   item_customizer('info.png'))
            else:
                self.workflow.item('Not available', 'Workflow: {0}'.format(self.workflow.name),
                                   item_customizer('sad.png'))

            return True

        return display

    def show_update_settings(self):
        def display():
            settings = self.workflow.setting('update')
            if not settings:
                self.workflow.item('Updates not supported',
                                   'Workflow: {0}'.format(self.workflow.name), item_customizer('sad.png'))

            elif not settings['enabled']:
                self.workflow.item('Updates are disabled for this workflow',
                                   'Use "--update-mode auto|manual" to enable updates',
                                   item_customizer('disable.png'))
            else:
                self.workflow.item('Enabled: {0}'.format(settings['enabled']),
                                   'Workflow will automatically search for updates',
                                   item_customizer('update.png'))

                self.workflow.item('Frequency: {0}'.format(settings['frequency'] or 1),
                                   'The frequency in days with which the workflow will look for new versions',
                                   item_customizer('time.png'))

                self.workflow.item('Include releases: {0}'.format(settings['include-prereleases'] or False),
                                   'Whether pre-releases will be included in the updates or not',
                                   item_customizer('release.png'))

            return True

        return display

    def configure_update_mode_settings(self, settings):
        options = {}

        def callback():
            self.configure_update_mode_settings(settings)

        self.remove(self.update_keys, ['--enable-updates', '--disable-updates'])

        if not settings['enabled']:
            options['--enable-updates'] = self.update_option('update', 'enabled', True, callback)
        else:
            options['--disable-updates'] = self.update_option('update', 'enabled', False, callback)

        self.update(options)
        self.update_keys.extend(options.keys())

    def configure_update_frequency_settings(self, settings):
        options = {}

        def callback():
            self.configure_update_frequency_settings(settings)

        self.remove(self.update_keys, ['--do-daily-updates', '--do-weekly-updates', '--do-monthly-updates',
                                       '--do-yearly-updates'])

        options['--do-daily-updates'] = self.update_option('update', 'frequency', 1, callback)
        options['--do-weekly-updates'] = self.update_option('update', 'frequency', 7, callback)
        options['--do-monthly-updates'] = self.update_option('update', 'frequency', 30, callback)
        options['--do-yearly-updates'] = self.update_option('update', 'frequency', 365, callback)

        self.update(options)
        self.update_keys.extend(options.keys())

    def configure_update_prereleases_settings(self, settings):
        options = {}

        def callback():
            self.configure_update_prereleases_settings(settings)

        self.remove(self.update_keys, ['--include-prereleases', '--exclude-prereleases'])

        if settings['include-prereleases']:
            options['--exclude-prereleases'] = self.update_option('update', 'include-prereleases', False, callback)
        else:
            options['--include-prereleases'] = self.update_option('update', 'include-prereleases', True, callback)

        self.update(options)
        self.update_keys.extend(options.keys())

    def install_update(self):
        def process():
            self.workflow.install_update()

        return process

    def check_update(self):
        def process():
            self.workflow.check_update(True)

        return process

    def update_option(self, setting, option, value, callback):
        def process():
            old = self.workflow.setting(setting, option)
            self.workflow.setting(setting)[option] = value
            self.workflow.settings.save()

            self.workflow.item('Setting {0} updated successfully'.format(option),
                               'Changed from {0} to {1}'.format(old, value), item_customizer('ok.png'))

            callback()

            return True

        return process

    def show_update_help(self):
        def display():
            for key in self.update_keys:
                if key in self.keys():
                    self.workflow.item(key, WorkflowActions.descriptions[key], item_customizer('empty.png'))

            return True

        return display

    def remove(self, set, options):
        for option in options:
            self.pop(option, '')
            if option in set:
                set.remove(option)
