import unittest

from galileo.ui import FormExtractor, FormField

class testFormExtractor(unittest.TestCase):

    def testEasy(self):
        fe = FormExtractor()
        fe.feed('<html><body><form><input type="text" name="username"><input type="text" name="password"></form></body></html>')
        self.assertEquals(len(fe.forms), 1)
        self.assertEquals(len(fe.forms[0].fields), 2)
        self.assertEquals(fe.forms[0].asDict(), {'username':None, 'password':None})

    def testOneHidden(self):
        fe = FormExtractor()
        fe.feed('<html><body><form><input name="username" type="hidden" value="User"><input type="text" name="password"></form></body></html>')
        self.assertEquals(len(fe.forms), 1)
        self.assertEquals(fe.forms[0].asDict(), {'username': 'User', 'password': None})

    def testSelect(self):
        fe = FormExtractor()
        fe.feed('<html><body><form><select name="choice" ><option value="A" /><option value="B" selected></select></form></body></html>')
        self.assertEquals(len(fe.forms), 1)
        self.assertEquals(fe.forms[0].asDict(), {'choice': 'B'})
