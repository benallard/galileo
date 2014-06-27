import unittest

from galileo.ui import Form, FormField

class testFormField(unittest.TestCase):
    def teststr(self):
        self.assertEqual("'name': 'value'", str(FormField('name', 'text', 'value')))
        self.assertEqual("'name': None", str(FormField('name', 'text')))

    def testasXML(self):
        self.assertEqual(FormField('name').asXMLParam(), ('param', {'name': 'name'}, [], None))
        self.assertEqual(FormField('name', value='value').asXMLParam(), ('param', {'name': 'name'}, [], 'value'))

class testHTMLForm(unittest.TestCase):
    def testasXML(self):
        f = Form()
        f.addField(FormField('name'))
        f.addField(FormField('name2'))
        self.assertEqual(f.asXML(), [('param', {'name': 'name'}, [], None), ('param', {'name': 'name2'}, [], None)])

    def testasXML2Submit(self):
        f = Form()
        f.addField(FormField('name', 'submit'))
        f.addField(FormField('name2', 'submit'))
        f.takeValuesFromAnswer({'name2': None})
        self.assertEqual(f.asXML(), [('param', {'name': 'name2'}, [], None)])
