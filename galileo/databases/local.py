import logging
logger = logging.getLogger(__name__)
import os
import time

from . import Database

from ..dump import DumpResponse
from ..megadumpDecrypter import decrypt

class UnknownDumpTypeError(Exception):
    def __init__(self, dumptype):
        self.message = dumptype
    def __str__(self):
        return "Encountered unknown type of dump: "+self.message

class LocalDatabase(Database):

    def __init__(self, dumpDir):
        self.dirname = os.path.expanduser(dumpDir)
        if not os.path.exists(self.dirname):
            logger.debug("Creating non-existent directory for dumps %s",
                         self.dirname)
            os.makedirs(self.dirname)

    def loadKey(self, trackerId):
        keyFileName = os.path.join(self.dirname, "keys", trackerId)
        with open(keyFileName, 'r') as file:
            key = file.read()
            key = key.replace('\n', '')
            return bytes.fromhex(key)

    def getDeviceDirectoryName(self, trackerId):
        deviceDirectoryName = os.path.join(self.dirname, trackerId)
        if not os.path.exists(deviceDirectoryName):
            logger.debug("Directory for dumps for this tracker does not yet exist. Creating a new one at:  %s", deviceDirectoryName)
            os.makedirs(deviceDirectoryName)
        return deviceDirectoryName

    def sync(self, trackerID, dump, dongle):

        if dump.encryption == 1:
            try:
                key = self.loadKey(trackerID)
            except IOError:
                logger.error('Could not find the key necessary to decrypt megadumps of tracker '+trackerID+' in '+os.path.join(self.dirname,'keys'))
                raise

        if dump.megadumpType != '2E':
            raise NotImplementedError("This is not implemented yet.see issue #322 on bitbucket.")
            response = self.createResponse(dump)
            dump = decrypt(dump, key)
        else:
            raise UnknownDumpTypeError(dump.megadumpType)

        dumpDirectoryName = self.getDeviceDirectoryName(trackerID)
        filename = os.path.join(dumpDirectoryName, 'dump-%d_dec.txt' % int(time.time()))
        dump.toFile(filename)

        return response

    def createResponse(self):
        raise NotImplementedError("This is not implemented yet.")
        data, length = 0
        return DumpResponse(data, length)
