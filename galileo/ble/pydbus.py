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

class PyDBUS(API):
    def __init__(self, logsize):
        pass

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

        for _, obj in self._getObjects('org.bluez.Device1', lambda obj: service in obj['UUIDs']):
            logger.info("Found: %s", obj)

            yield Tracker(x2a(obj['Address']))
