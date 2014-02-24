import unittest

from galileo import __version__

import galileo.net
from galileo.net import GalileoClient, SyncError

class requestResponse(object):
    def __init__(self, text):
        self.text = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><galileo-server version="2.0"><server-version>

</server-version>%s</galileo-server>""" % text
    def raise_for_status(self): pass

class testStatus(unittest.TestCase):

    def testOk(self):
        def mypost(url, data, headers):
            self.assertEqual(url, 'someurl')
            self.assertEqual(data, """\
<?xml version='1.0' encoding='UTF-8'?>
<galileo-client version="2.0"><client-info><client-id>%(id)s</client-id><client-version>%(version)s</client-version><client-mode>status</client-mode></client-info></galileo-client>""" % {
    'id': GalileoClient.ID, 'version': __version__})
            self.assertEqual(headers['Content-Type'], 'text/xml')
            return requestResponse('')

        galileo.net.requests.post = mypost
        gc = GalileoClient('someurl')
        gc.requestStatus()

    def testError(self):
        URL = 'someurl'
        def mypost(url, data, headers):
            self.assertEqual(url, URL)
            self.assertEqual(data, """\
<?xml version='1.0' encoding='UTF-8'?>
<galileo-client version="2.0"><client-info><client-id>%(id)s</client-id><client-version>%(version)s</client-version><client-mode>status</client-mode></client-info></galileo-client>""" % {
    'id': GalileoClient.ID,
    'version': __version__})
            self.assertEqual(headers['Content-Type'], 'text/xml')
            return requestResponse('<error>Something is Wrong</error>')

        galileo.net.requests.post = mypost
        gc = GalileoClient(URL)
        self.assertRaises(SyncError, gc.requestStatus)

class MyDongle(object):
    def __init__(self, M, m): self.major=M; self.minor=m
class MyMegaDump(object):
    def __init__(self, b64): self.b64 = b64
    def toBase64(self): return self.b64

class testSync(unittest.TestCase):

    def testOk(self):
        URL = 'some_url'
        T_ID = 'abcd'
        D = MyDongle(0, 0)
        d = MyMegaDump('YWJjZA==')
        def mypost(url, data, headers):
            self.assertEqual(url, URL)
            self.assertEqual(data, """\
<?xml version='1.0' encoding='UTF-8'?>
<galileo-client version="2.0"><client-info><client-id>%(id)s</client-id><client-version>%(version)s</client-version><client-mode>sync</client-mode><dongle-version major="%(M)d" minor="%(m)d" /></client-info><tracker tracker-id="%(t_id)s"><data>%(b64dump)s</data></tracker></galileo-client>""" % {
    'id': GalileoClient.ID,
    'version': __version__,
    'M': D.major,
    'm': D.minor,
    't_id': T_ID,
    'b64dump': d.toBase64()})
            self.assertEqual(headers['Content-Type'], 'text/xml')
            return requestResponse('<tracker tracker-id="abcd" type="megadumpresponse"><data>ZWZnaA==</data></tracker>')

        galileo.net.requests.post = mypost
        gc = GalileoClient(URL)
        self.assertEqual(gc.sync(D, T_ID, d),
                         [101, 102, 103, 104])

    def testNoTracker(self):
        URL = 'some_url'
        T_ID = 'aaaabbbb'
        D = MyDongle(34, 88)
        d = MyMegaDump('base64Dump')
        def mypost(url, data, headers):
            self.assertEqual(url, URL)
            self.assertEqual(data, """\
<?xml version='1.0' encoding='UTF-8'?>
<galileo-client version="2.0"><client-info><client-id>%(id)s</client-id><client-version>%(version)s</client-version><client-mode>sync</client-mode><dongle-version major="%(M)d" minor="%(m)d" /></client-info><tracker tracker-id="%(t_id)s"><data>%(b64dump)s</data></tracker></galileo-client>""" % {
    'id': GalileoClient.ID,
    'version': __version__,
    'M': D.major,
    'm': D.minor,
    't_id': T_ID,
    'b64dump': d.toBase64()})
            self.assertEqual(headers['Content-Type'], 'text/xml')
            return requestResponse('')

        galileo.net.requests.post = mypost
        gc = GalileoClient(URL)
        self.assertRaises(SyncError, gc.sync, D, T_ID, d)

    def testNoData(self):
        URL = 'some_url'
        T_ID = 'aaaa'
        D = MyDongle(-2, 42)
        d = MyMegaDump('base64Dump')
        def mypost(url, data, headers):
            self.assertEqual(url, URL)
            self.assertEqual(data, """\
<?xml version='1.0' encoding='UTF-8'?>
<galileo-client version="2.0"><client-info><client-id>%(id)s</client-id><client-version>%(version)s</client-version><client-mode>sync</client-mode><dongle-version major="%(M)d" minor="%(m)d" /></client-info><tracker tracker-id="%(t_id)s"><data>%(b64dump)s</data></tracker></galileo-client>""" % {
    'id': GalileoClient.ID,
    'version': __version__,
    'M': D.major,
    'm': D.minor,
    't_id': T_ID,
    'b64dump': d.toBase64()})
            self.assertEqual(headers['Content-Type'], 'text/xml')
            return requestResponse('<tracker tracker-id="abcd" type="megadumpresponse"></tracker>')

        galileo.net.requests.post = mypost
        gc = GalileoClient(URL)
        self.assertRaises(SyncError, gc.sync, D, T_ID, d)

    def testNotData(self):
        URL = 'some_other_url'
        T_ID = 'aaaabbbbccccdddd'
        D = MyDongle(-2, 42)
        d = MyMegaDump('base64Dump')
        def mypost(url, data, headers):
            self.assertEqual(url, URL)
            self.assertEqual(data, """\
<?xml version='1.0' encoding='UTF-8'?>
<galileo-client version="2.0"><client-info><client-id>%(id)s</client-id><client-version>%(version)s</client-version><client-mode>sync</client-mode><dongle-version major="%(M)d" minor="%(m)d" /></client-info><tracker tracker-id="%(t_id)s"><data>%(b64dump)s</data></tracker></galileo-client>""" % {
    'id': GalileoClient.ID,
    'version': __version__,
    'M': D.major,
    'm': D.minor,
    't_id': T_ID,
    'b64dump': d.toBase64()})
            self.assertEqual(headers['Content-Type'], 'text/xml')
            return requestResponse('<tracker tracker-id="abcd" type="megadumpresponse"><not_data /></tracker>')

        galileo.net.requests.post = mypost
        gc = GalileoClient(URL)
        self.assertRaises(SyncError, gc.sync, D, T_ID, d)
