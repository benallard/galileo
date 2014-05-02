import unittest

from galileo.ui import FormExtractor

class testFormExtractor(unittest.TestCase):

    def testEasy(self):
        fe = FormExtractor()
        fe.feed('<html><body><form><input name="username"><input name="password"></form></body></html>')
        self.assertEquals(len(fe.forms), 1)
        self.assertEquals(fe.forms[0], {'username': None, 'password': None})

    def testOneHidden(self):
        fe = FormExtractor()
        fe.feed('<html><body><form><input name="username" type="hidden" value="Ben"><input name="password"></form></body></html>')
        self.assertEquals(len(fe.forms), 1)
        self.assertEquals(fe.forms[0], {'username': 'Ben', 'password': None})
