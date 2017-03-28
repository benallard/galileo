import logging
logger = logging.getLogger(__name__)

try:
    import pydbus
except ImportError:
    pydbus = None

from . import API

class PyDBUS(API):
    def __init__(self, logsize):
        pass

    def _getObject(self, klass, properties=None):
        for path, obj in self.manager.GetManagedObjects().items():
            if klass in obj:
                if properties is None:
                    yield path
                    continue
                for k, v in properties:
                    if obj.get(k) != v:
                        continue
                yield path

    def setup(self):
        if pydbus is None:
            return False
        self.bus = pydbus.SystemBus()
        self.manager = self.bus.get('org.bluez', '/')['org.freedesktop.DBus.ObjectManager']
        adapterpaths = list(self._getObject('org.bluez.Adapter1'))
        if len(adapterpaths) == 0:
            logger.error("No bluetooth adapters found")
            return False
        logger.info('Found adapter: %s', adapterpaths)
        self.adapter = self.bus.get('org.bluez', adapterpaths[0])['org.bluez.Adapter1']
        return True

    def disconnectAll(self):
        return True

