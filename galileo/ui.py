"""\
This is where to look for for all user interaction stuff ...
"""

from HTMLParser import HTMLParser


class FormExtractor(HTMLParser):
    """ This read a whole html page and extract the forms """
    def __init__(self):
        self.forms = []
        self.curForm = None
        self.curSelect = None
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.curForm = {}
        if tag == 'input':
            self.curForm[attrs['name']] = attrs.get('value', None)
        if tag == 'select':
            self.curSelect = attrs['name']
            self.curForm[self.curSelect] = None
        if tag == 'option' and 'selected' in attrs:
            self.curForm[self.curSelect] = attrs['value']


    def handle_endtag(self, tag):
        if tag == 'form':
            self.forms.append(self.curForm)
            self.curForm = None
        if tag == 'select':
            self.curSelect = None

    def handle_data(self, data): pass


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
                # Not found, search again, less picky
                for form in fe.forms:
                    for field in form:
                        if field in answer and form[field] is None and answer[field] is not None:
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
