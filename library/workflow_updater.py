import threading

class WorkflowUpdater:
    def __init__(self, workflow):
        self.workflow = workflow

    def check_update(self):
        if not self.workflow.setting('update', 'enabled'):
            return False

        thread = threading.Thread(None, do_check_update, 'check-update', self.workflow)
        thread.start()

def do_check_update(workflow):
    prereleases = workflow.setting('update', 'include-prereleases')
    repository = workflow.setting('update', 'repository')


