import os
import subprocess


class WorkflowActions(dict):
    icons = os.path.abspath(os.path.dirname(__file__))
    descriptions = {'--force-update': 'Use this option to force updates',
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
        self.update_keys = ['--check-for-update', '--force-update']

        self['--help'] = self.show_help()
        self['--version'] = self.show_version()

        self['--update-help'] = self.show_update_help()
        self['--update-settings'] = self.show_update_settings()

        if workflow.setting('update'):
            settings = workflow.setting('update')
            self['--force-update'] = self.force_update()
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
                                   WorkflowActions.customizer('sad.png'))

            return True

        return display

    def show_version(self):
        def display():
            if self.workflow.version:
                self.workflow.item('{0}'.format(str(self.workflow.version)), 'Workflow: {0}'.format(self.workflow.name),
                                   WorkflowActions.customizer('info.png'))
            else:
                self.workflow.item('Not available', 'Workflow: {0}'.format(self.workflow.name),
                                   WorkflowActions.customizer('sad.png'))

            return True

        return display

    def show_update_settings(self):
        def display():
            settings = self.workflow.setting('update')
            if not settings:
                self.workflow.item('Updates not supported',
                                   'Workflow: {0}'.format(self.workflow.name), WorkflowActions.customizer('sad.png'))

            elif settings['mode'] == 'disable':
                self.workflow.item('Updates are disabled for this workflow',
                                   'Use "--update-mode auto|manual" to enable updates',
                                   WorkflowActions.customizer('disable.png'))
            else:
                if settings['mode'] == 'auto':
                    mode = 'The workflow will be automatically updated when a new version is available'
                else:
                    mode = 'The workflow will display an option letting you choose when to update'

                self.workflow.item('Mode: {0}'.format(settings['mode']), mode, WorkflowActions.customizer('update.png'))

                self.workflow.item('Frequency: {0}'.format(settings['frequency']),
                                   'The frequency with which the workflow will look for new versions',
                                   WorkflowActions.customizer('time.png'))

                self.workflow.item('Include releases: {0}'.format(settings['include-prereleases']),
                                   'Whether pre-releases will be included in the updates or not',
                                   WorkflowActions.customizer('release.png'))

            return True

        return display

    def configure_update_mode_settings(self, settings):
        options = {}

        def callback():
            self.configure_update_mode_settings(settings)

        self.remove(self.update_keys, ['--enable-updates', '--disable-updates'])

        if not settings['enable']:
            options['--enable-updates'] = self.update_option('update', 'enable', True, callback)
        else:
            options['--disable-updates'] = self.update_option('update', 'enable', False, callback)

        self.update(options)
        self.update_keys.extend(options.keys())

    def configure_update_frequency_settings(self, settings):
        options = {}

        def callback():
            self.configure_update_frequency_settings(settings)

        self.remove(self.update_keys, ['--do-daily-updates', '--do-weekly-updates', '--do-monthly-updates',
                                       '--do-yearly-updates'])

        options['--do-daily-updates'] = self.update_option('update', 'frequency', 86400, callback)
        options['--do-weekly-updates'] = self.update_option('update', 'frequency', 604800, callback)
        options['--do-monthly-updates'] = self.update_option('update', 'frequency', 18144000, callback)
        options['--do-yearly-updates'] = self.update_option('update', 'frequency', 217728000, callback)

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

    def force_update(self):
        def process():
            self.workflow.update(True)

        return process

    def check_update(self):
        def process():
            self.workflow.check_update(True)

        return process

    def update_option(self, setting, option, value, callback):
        def process():
            old = self.workflow.setting(setting, option)

            self.workflow.setting(setting)[option] = value
            self.workflow.save_settings()

            self.workflow.item('Setting {0} updated successfully'.format(option),
                               'Changed from {0} to {1}'.format(old, value), WorkflowActions.customizer('ok.png'))

            callback()

            return True

        return process

    def show_update_help(self):
        def display():
            for key in self.update_keys:
                if key in self.keys():
                    self.workflow.item(key, WorkflowActions.descriptions[key], WorkflowActions.customizer('empty.png'))

            return True

        return display

    def remove(self, set, options):
        for option in options:
            self.pop(option, '')
            if option in set:
                set.remove(option)

    @staticmethod
    def customizer(icon=None, valid=False, arg=None):
        icon = os.path.join(WorkflowActions.icons, 'icons', icon) if icon else None

        def customize(item):
            item.icon = icon
            item.valid = valid
            item.arg = arg

            return item

        return customize
