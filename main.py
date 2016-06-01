import re
import sys

from library import Workflow


def main(workflow):
    query = workflow.args[0]
    numbers = re.match(r'^[0-7]{3}$', query)
    expression = re.match(r'^((?:r|-)(?:w|-)(?:x|-))\s*((?:r|-)(?:w|-)(?:x|-))\s*((?:r|-)(?:w|-)(?:x|-))\s*', query)

    if numbers:
        owner = get_permission_from_number(int(query[0]))
        group = get_permission_from_number(int(query[1]))
        others = get_permission_from_number(int(query[2]))

        chmod = 'chmod {0}{1}{2}'.format(owner[0], group[0], others[0])
        workflow.item(chmod, 'Copy {0} to clipboard'.format(chmod),
                      lambda item: with_info(item, 'terminal.png', True, chmod))

        workflow.item('Owner {0}'.format(owner[0]), 'has {0} access'.format(owner[1]),
                      lambda item: with_info(item, 'owner.png', False))

        workflow.item('Group {0}'.format(group[0]), 'has {0} access'.format(group[1]),
                      lambda item: with_info(item, 'group.png', False))

        workflow.item('Others {0}'.format(others[0]), 'has {0} access'.format(others[1]),
                      lambda item: with_info(item, 'others.png', False))

    elif expression:
        owner = get_number_from_permission(expression.group(0))
        group = get_number_from_permission(expression.group(1))
        others = get_number_from_permission(expression.group(2))

        chmod = 'chmod {0}{1}{2}'.format(owner[0], group[0], others[0])
        workflow.item(chmod, 'Copy {0} to clipboard'.format(chmod),
                      lambda item: with_info(item, 'terminal.png', True, chmod))

        workflow.item('Owner {0}'.format(owner[0]), '{0} access'.format(owner[1]),
                      lambda item: with_info(item, 'owner.png', False))

        workflow.item('Group {0}'.format(group[0]), '{0} access'.format(group[1]),
                      lambda item: with_info(item, 'group.png', False))

        workflow.item('Others {0}'.format(others[0]), '{0} access'.format(others[1]),
                      lambda item: with_info(item, 'others.png', False))
    else:
        workflow.item('Change Mode', 'Please input a valid permission set i.e. 777, rwxrw-rw',
                      lambda item: with_info(item, 'terminal.png', False))

    workflow.feedback()


def get_permission_from_number(number):
    permission = ''
    description = []

    read = number & 4
    write = number & 2
    execute = number & 1

    permission += 'r' if read == 4 else '-';
    if read == 4:
        description.append('read')

    permission += 'w' if write == 2 else '-';
    if write == 2:
        description.append('write')

    permission += 'x' if execute == 1 else '-';
    if execute == 1:
        description.append('execute')

    return [permission, format_description(description)]


def get_number_from_permission(expression):
    number = 0
    description = []

    number += 4 if expression[0] == 'r' else 0
    if expression[0] == 'r':
        description.append('read')

    number += 2 if expression[1] == 'w' else 0
    if expression[1] == 'w':
        description.append('write')

    number += 1 if expression[2] == 'x' else 0
    if expression[2] == 'x':
        description.append('execute')

    return [str(number), format_description(description)]


def with_info(item, icon, valid, arg=None):
    item.icon = icon
    item.valid = valid

    if arg:
        item.arg = arg

    return item


def format_description(description):
    if len(description) == 0:
        return 'no'

    access = description[0]
    if len(description) == 3:
        access += ', {0} and {1}'.format(description[1], description[2])
    elif len(description) == 2:
        access += ' and {0}'.format(description[1])

    return access

if __name__ == '__main__':
    sys.exit(Workflow.run(main, Workflow()))
