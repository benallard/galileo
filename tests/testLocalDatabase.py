import unittest
import tempfile
import os

from galileo.databases.local import LocalDatabase
from galileo.tracker import Tracker

class MyLocalDatabase(LocalDatabase):
    def __init__(self):
        self.tempDir = tempfile.TemporaryDirectory()
        self.dirname = self.tempDir.name
        keysDir = os.path.join(self.dirname, 'keys')
        os.mkdir(keysDir)

@unittest.skipIf(not hasattr(tempfile, 'TemporaryDirectory'),"tempfile module does not have TemporaryDirectory, cannot run the tests.")
class TestLocalDatabase(unittest.TestCase):
    def setUp(self):
        self.tracker = Tracker.fromDiscovery([0x12, 0x34, 0x56, 0x78, 0x9A, 0x12, 0x01, 0xBC, 0x02, 0x05, 0x04, 0x03, 0x2C, 0x31, 0xF6, 0xD8, 0x58])
        self.dataBase = MyLocalDatabase()

        keyFileName = os.path.join(self.dataBase.dirname, "keys", self.tracker.getID())
        self.testKey = "12 34 56 78\n12 34 56 78\n12 34 56 78\n12 34 56 78\n"

        with open(keyFileName, 'w') as keyFile:
            keyFile.write(self.testKey)

    def testLoadKey(self):
        loadedKey = self.dataBase.loadKey(self.tracker.getID())
        expectedKey = bytes.fromhex(self.testKey.replace('\n', ''))
        self.assertEqual(loadedKey, expectedKey)

    def testGetDeviceDirectoryName(self):
        trackerDirname = self.dataBase.getDeviceDirectoryName(self.tracker.getID())
        self.assertTrue(trackerDirname.endswith(self.tracker.getID()))
