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


class HardCodedUI(BaseUI):
    """\
    This ui class doesn't show anything to the user and takes its answers
    from a list of hard-coded ones
    """
    def __init__(self, answers):
        self.answers = answers
    def request(self, action, html):
        if html.startswith('<![CDATA[') and html.endswith(']]>'):
            html = html[len('<![CDATA['):-len(']]>')]
        fe = FormExtractor()
        fe.feed(html)
        answer = self.answers.get(action, {})
        print answer, fe.forms
        # Figure out which of the form we should fill
        goodForm = None
        if len(fe.forms) == 1:
            # Only one there, no need to searcj for the correct one ...
            goodForm = fe.forms[0]
        else:
            # We need to find the one that match the most our answers
            for form in fe.forms:
                for field in form:
                    if field in answer and form[field] is not None and form[field] == answer[field]:
                        goodForm = form
                if goodForm:
                    break
        if goodForm is None:
            return []
        # Transfer the answers from the config to the form
        for field in goodForm:
            if field in answer:
                goodForm[field] = answer[field]
        # Return the XML tuples
        res = []
        for field in goodForm:
            res.append(('param', {'name': field}, [], goodForm[field]))
        return res
