import logging
logger = logging.getLogger(__name__)
import time
import uuid

try:
    import pydbus
except ImportError:
    pydbus = None

from ..tracker import Tracker
from ..utils import x2a
from . import API

class DbusTracker(Tracker):
    def __init__(self, id, path):
        Tracker.__init__(self, id)
        self.path = path

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
        self.manager = self.bus.get('org.bluez', '/')['org.freedesktop.DBus.ObjectManager']
        adapterpaths = list(self._getObjects('org.bluez.Adapter1'))
        if len(adapterpaths) == 0:
            logger.error("No bluetooth adapters found")
            return False
        logger.info('Found adapter: %s', adapterpaths)
        self.adapter = self.bus.get('org.bluez', adapterpaths[0][0])['org.bluez.Adapter1']
        if not self.adapter.Powered:
            logger.info("Adapter wasn't powered, powering it up.")
            self.adapter.Powered = True
        return True

    def disconnectAll(self):
        return True

    def discover(self, service):
        service = list(service.fields)
        service[0] |= 0xfb00
        service = str(uuid.UUID(fields=service))

        self.adapter.StartDiscovery()
        time.sleep(5)
        self.adapter.StopDiscovery()

        for path, obj in self._getObjects('org.bluez.Device1', lambda obj: service in obj['UUIDs']):
            logger.info("Found: %s", obj)

            yield DbusTracker(x2a(obj['Address']), path)

    def connect(self, tracker):
        self.tracker = self.bus.get('org.bluez', tracker.path)#['org.bluez.Device1']
        logger.debug(dir(self.tracker))
        if not self.tracker.Connected:
            logger.info("Connecting to tracker")
            self.tracker.Connect()
            #pass
        if not self.tracker.Paired:
            logger.info("Pairing with tracker")
            self.tracker.Pair()
        #self.tracker.GetAll('org.bluez.Device1')
        for path, obj in self._getObjects('org.bluez.GattService1'):#, lambda obj: obj['UUID'] == 'adabfb00-6e7d-4601-bda2-bffaa68956ba'):
            logger.debug(path, obj)
        logger.debug(self.tracker.GattServices)
        self.tracker.Disconnect()
        return True

    def disconnect(self, tracker):
        if self.tracker is not None:
            self.tracker.Disconnect()
            self.tracker = None

    def getDump(self):
        raise NotImplementedError

    def uploadResponse(self, dump):
        raise NotImplementedError

