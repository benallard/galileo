import logging
logger = logging.getLogger(__name__)
import time
import uuid

try:
    import pydbus
except ImportError:
    pydbus = None

from ..tracker import Tracker
from ..utils import x2a, a2x
from . import API, DM

class DbusTracker(Tracker):
    def __init__(self, id, path):
        Tracker.__init__(self, id)
        self.path = path

def maskUUID(base, mask):
    """ returns a UUID with the mask OR'd to the first field """
    base = list(base.fields)
    base[0] |= mask
    return uuid.UUID(fields=base)

class PyDBUS(API):
    def __init__(self, logsize):
        self.tracker = None

    def _getObjects(self, classtype=None, filter_=None):
        for path, obj in self.manager.GetManagedObjects().items():
            logger.debug('object %s has the following classes: %s', path, ', '.join(obj))
            if classtype is None or classtype in obj:
                if classtype is not None:
                    obj = obj[classtype]
                if filter_ is not None and not filter_(obj):
                    logger.info("Filter excluded %s", path)
                    continue
                yield path, obj

    def setup(self):
        if pydbus is None:
            return False
        self.bus = pydbus.SystemBus()
        self.manager = self.bus.get('org.bluez', '/')#['org.freedesktop.DBus.ObjectManager']
        adapterpaths = list(self._getObjects('org.bluez.Adapter1'))
        if len(adapterpaths) == 0:
            logger.error("No bluetooth adapters found")
            return False
        logger.info('Found adapter: %s', adapterpaths)
        self.adapter = self.bus.get('org.bluez', adapterpaths[0][0])
        if not self.adapter.Powered:
            logger.info("Adapter wasn't powered, powering it up.")
            self.adapter.Powered = True
        return True

    def disconnectAll(self):
        return True

    def discover(self, service):
        self.serviceUUID = maskUUID(service, 0xfb00)
        service = str(self.serviceUUID)

        self.adapter.StartDiscovery()
        time.sleep(5)
        self.adapter.StopDiscovery()

        for path, obj in self._getObjects('org.bluez.Device1', lambda obj: service in obj['UUIDs']):
            logger.info("Found: %s", obj)

            yield DbusTracker(x2a(obj['Address']), path)

    def connect(self, tracker):
        self.tracker = self.bus.get('org.bluez', tracker.path)#['org.bluez.Device1']
        logger.debug(dir(self.tracker))
        if not self.tracker.Paired:
            logger.info("Pairing with tracker")
            self.tracker.Pair()
        if not self.tracker.Connected:
            logger.info("Connecting to tracker")
            self.tracker.Connect()
        # Now, wait for ServicesResolved to turn 'True'

        read = str(maskUUID(self.serviceUUID, 0x01))
        write = str(maskUUID(self.serviceUUID, 0x02))
        for path, obj in self._getObjects('org.bluez.GattCharacteristic1', lambda obj: obj['UUID'] in (read, write)):
            if obj['UUID'] == read:
                self.read = self.bus.get('org.bluez', path)
            else:
                self.write = self.bus.get('org.bluez', path)
        # init airlink
        self._dataWrite(DM([0xC0, 0x0A, 0x0A, 0x00, 0x06, 0x00, 0x06, 0x00, 0x00, 0x00, 0xC8, 0x00]))
        self._dataRead()
        # display code
        self._dataWrite(DM([0xc0, 6]))
        self._dataRead()
        return True

    def _dataWrite(self, data):
        logger.debug('=> %s', data)
        self.write.WriteValue(data.data, {})

    def _dataRead(self):
        data = DM(bytearray(self.read.ReadValue({})), False)
        logger.debug('<= %s', data)
        return data

    def disconnect(self, tracker):
        if self.tracker is not None:
            self.tracker.Disconnect()
            self.tracker = None

    def getDump(self):
        raise NotImplementedError

    def uploadResponse(self, dump):
        raise NotImplementedError
