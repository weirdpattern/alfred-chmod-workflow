import sys


class InvalidModifier(Exception):
    """Invalid modifier error"""


class InvalidText(Exception):
    """Invalid text error"""


class WorkflowItem:
    def __init__(self, title, subtitle):
        self.title = title
        self.subtitle = subtitle

        self.type = None
        self.icon = None
        self.icontype = None

        self.modifiers = {'cmd': None, 'ctrl': None, 'shift': None, 'alt': None, 'fn': None}

        self.uid = None
        self.arg = None
        self.valid = True
        self.autocomplete = None

        self.texts = {'large': None, 'copy': None}

    def modifier(self, key, value):
        if key not in self.modifiers:
            raise InvalidModifier('Modifier {0} not support'.format(key))

        self.modifiers[key] = value

    def text(self, texttype, value):
        if texttype not in self.texts:
            raise InvalidText('Text type {0} not support'.format(texttype))

        self.texts[texttype] = value

    def feedback(self, flush=False):
        item = '\t<item {0}>\n'

        options = []
        if self.uid:
            options.append('uid="{0}"'.format(self.uid))

        if self.valid:
            options.append('valid="Yes"')
        else:
            options.append('valid="No"')

        if self.autocomplete:
            options.append('autocomplete="{0}"'.format(self.autocomplete))

        item = item.format(' '.join(str(x) for x in options))
        item += '\t\t<title>{0}</title>\n'.format(self.title)

        if self.subtitle:
            item += '\t\t<subtitle>{0}</subtitle>\n'.format(self.subtitle)

        if self.icon and self.icontype:
            item += '\t\t<icon type="{1}">{0}</icon>\n'.format(self.icon, self.icontype)
        elif self.icon:
            item += '\t\t<icon>{0}</icon>\n'.format(self.icon)

        if self.arg:
            item += '\t\t<arg>{0}</arg>\n'.format(self.arg)

        for mod in self.modifiers.keys():
            if self.modifiers[mod]:
                item += '\t\t<subtitle mod="{1}">{0}</subtitle>\n'.format(self.modifiers[mod], mod)

        for texttype in self.texts.keys():
            if self.texts[texttype]:
                item += '\t\t<text type="{1}">{0}</text>\n'.format(self.texts[texttype], texttype)

        item += '\t</item>\n'

        sys.stdout.write(item)
        if flush:
            sys.stdout.flush()
