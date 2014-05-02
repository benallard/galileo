"""\
This is where to look for for all user interaction stuff ...
"""

from HTMLParser import HTMLParser


class FormExtractor(HTMLParser):
    """ This read a whole html page and extract the forms """
    def __init__(self):
        self.forms = []
        self.inForm = False
        self.curForm = {}
        HTMLParser.__init__(self)
    def handle_starttag(self, tag, attrs):
        if tag == 'form':
            self.inForm = True
            self.curForm = {}
        if tag == 'input':
            attrs = dict(attrs)
            self.curForm[attrs['name']] = attrs.get('value', None)
    def handle_endtag(self, tag):
        if tag == 'form':
            self.forms.append(self.curForm)
            self.inForm = False

    def handle_data(self, data):
        pass


class BaseUI(object):
    """\
    This is the base of all ui classes, it provides an interface and handy
    methods
    """
    def request(self, action, client_display):
        raise NotImplementedError
