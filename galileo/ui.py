"""\
This is where to look for for all user interaction stuff ...
"""

from HTMLParser import HTMLParser

class Form(object):
    def __init__(self):
        self.fields = set()
        self.submit = None

    def addField(self, field):
        self.fields.add(field)

    def commonFields(self, answer, withValues=True):
        res = 0
        for field in self.fields:
            if field.name in answer:
                if withValues:
                    if field.value is not None and field.value == answer[field.name]:
                        res += 1
                else:
                    res += 1
        print 'res = %d' % res
        return res

    def takeValuesFromAnswer(self, answer):
        """\
        Transfer the answers from the config to the form
        """
        for field in self.fields:
            field.value = answer.get(field.name, field.value)
            if field.type == 'submit':
                self.submit = field.value

    def asXML(self):
        """\
        Return the XML tuples. The trick is: THere can be only one 'submit'
        """
        res = []
        for field in self.fields:
            if field.type == 'submit':
                if self.submit != field.value:
                    continue
            res.append(field.asXMLParam())
        return res

    def __str__(self):
        return ', '.join(str(f) for f in self.fields)

    def asDict(self):
        """ for comparison in the test suites """
        return dict((f.name, f.value) for f in self.fields)

class FormField(object):
    def __init__(self, name, type='text', value=None, **kw):
        self.name = name
        self.type = type
        self.value = value

    def asXMLParam(self):
        return ('param', {'name': self.name}, [], self.value)

    def __str__(self):
        return '%r: %r' % (self.name, self.value)


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
            self.curForm = Form()
        if tag == 'input':
            if 'name' in attrs:
                self.curForm.addField(FormField(**attrs))
        if tag == 'select':
            self.curSelect = FormField(type='select', **attrs)
        if tag == 'option' and 'selected' in attrs:
            self.curSelect.value = attrs['value']


    def handle_endtag(self, tag):
        if tag == 'form':
            self.forms.append(self.curForm)
            self.curForm = None
        if tag == 'select':
            self.curForm.addField(self.curSelect)
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
        answer = self.answers[action]
        print answer, fe.forms
        # Figure out which of the form we should fill
        goodForm = None
        if len(fe.forms) == 1:
            # Only one there, no need to search for the correct one ...
            goodForm = fe.forms[0]
        else:
            # We need to find the one that match the most our answers
            max = 0
            for form in fe.forms:
                v = form.commonFields(answer)
                if v > max:
                    goodForm = form
                    max = v
            if max == 0:
                # Not found, search again, less picky
                for form in fe.forms:
                    v = form.commonFields(answer, False)
                    if v > max:
                        goodForm = form
                        max = v
        if goodForm is None:
            raise ValueError('no answer found')
        goodForm.takeValuesFromAnswer(answer)
        return goodForm.asXML()
