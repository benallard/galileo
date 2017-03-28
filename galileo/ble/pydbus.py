import logging
logger = logging.getLogger(__name__)
import time
import uuid

try:
    import pydbus
except ImportError:
    pydbus = None

from . import API

class PyDBUS(API):
    def __init__(self, logsize):
        pass

    def _getObjects(self, klass, filter=None):
        for path, obj in self.manager.GetManagedObjects().items():
            if klass in obj:
                if filter is None:
                    yield path
                    continue
                logger.debug(obj)
                if not filter(obj):
                    logger.info("Filter excluded %s", path)
                    continue
                yield path

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
        self.adapter = self.bus.get('org.bluez', adapterpaths[0])['org.bluez.Adapter1']
        return True

    def disconnectAll(self):
        return True

    def discover(self, service):
        service = list(service.fields)
        logger.debug(service[0])
        service[0] |= 0xfb00
        service = str(uuid.UUID(fields=service))
        logger.debug(service)
        self.adapter.StartDiscovery()

        time.sleep(5)
        self.adapter.StopDiscovery()

        for obj in self._getObjects('org.bluez.Device1', lambda obj: service in obj['org.bluez.Device1']['UUIDs']):
            logger.info("Found: %s", obj)
            yield obj
