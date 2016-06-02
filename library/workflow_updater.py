import json
import threading

try:
    from urllib2 import Request, urlopen, URLError
except ImportError:
    from urllib.request import Request, urlopen
    from urllib.error import URLError


from utils import send_notification
from workflow_version import Version


class WorkflowUpdater:
    def __init__(self, workflow):
        self.workflow = workflow

    def check_update(self):
        if not self.workflow.setting('update', 'enabled'):
            return False

        thread = threading.Thread(None, do_check_update, 'check-update', (self.workflow,))
        thread.start()

        return True


def do_check_update(workflow):
    prereleases = workflow.setting('update', 'include-prereleases') or False
    github = workflow.setting('update', 'repository', 'github')
    if not github:
        send_notification('Workflow updater', 'No repository configuration has been detected')
        return False

    def fill():
        url = 'https://api.github.com/repos/{0}/{1}/releases'.format(github['username'], github['repository'])
        headers = {'User-Agent': 'Alfred-Workflow/1.17'}

        try:
            request = Request(url, headers=headers)
            response = urlopen(request)
            data = json.loads(response.read(), 'utf-8')
        except URLError:
            data = None
            send_notification('Workflow updater', 'Could not reach the repository')

        if data:
            urls = []
            for asset in data.get('assets', []):
                url = asset.get('browser_download_url')
                if not url or not url.endswith('.alfredworkflow'):
                    continue
                urls.append(url)

            return {
                'url': url[0],
                'version': data['tag_name'],
                'prerelease': data['prerelease']
            }

        return None

    message = 'You are running the latest version of "{0}"'.format(workflow.name)
    release = workflow.cache.read('.workflow_updater', fill, 3600)
    if release:
        if not release['prerelease'] or (release['prerelease'] and prereleases):
            latest = Version(release['version'])
            if latest > workflow.version:
                message = 'Version {0} of workflow {1} is available'.format(latest, workflow.name)

    send_notification('Workflow updater', message)
