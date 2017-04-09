import logging
logger = logging.getLogger(__name__)
import time
import uuid

try:
    import pydbus
    from gi.repository import GLib
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
        self.read = None
        self.readqueue = []

    def _getObjects(self, classtype=None, filter_=None):
        for path, obj in self.manager.GetManagedObjects().items():
            if classtype is None or classtype in obj:
                if classtype is not None:
                    obj = obj[classtype]
                if filter_ is not None and not filter_(obj):
                    logger.debug("Filter excluded %s", path)
                    continue
                yield path, obj

    def setup(self):
        if pydbus is None:
            return False
        self.loop = GLib.MainLoop()
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
        # Remove all not-connected devices from the managed objects
        for path, obj in self._getObjects('org.bluez.Device1', lambda obj: not obj['Connected']):
            self.adapter.RemoveDevice(path)
        return True

    def discover(self, baseUUID, service1, read, write, minRSSI, timeout):
        service = str(maskUUID(baseUUID, service1))
        self.readUUID = str(maskUUID(baseUUID, read))
        self.writeUUID = str(maskUUID(baseUUID, write))

        trackers = []
        def new_iface(*args):
            logger.debug("Discovered: %s", args)
            trackers.append(args[0])

        def stop_discovery():
            self.adapter.StopDiscovery()
            self.loop.quit()
            logger.info("Discovery done, found %d trackers", len(trackers))
            return False

        # listen for InterfaceAdded
        self.manager.onInterfacesAdded = new_iface
        # add a timeout stop function
        GLib.timeout_add(timeout, stop_discovery)
        # Start the discovery
        self.adapter.SetDiscoveryFilter({'UUIDs': GLib.Variant('as', [service]), 'Transport': GLib.Variant('s', 'le')})
        self.adapter.StartDiscovery()
        # run the loop
        self.loop.run()
        # Deregister our event listener
        self.manager.onInterfacesAdded = None

        # Go through the one that have actually been added
        for path, obj in self._getObjects('org.bluez.Device1', lambda obj: service in obj['UUIDs']):
            if path not in trackers:
                # Old one, was not discovered this round
                continue
            logger.info("Found: %s", obj)
            tracker_id = x2a(obj['Address'])
            # Somehow, the Address is the inverse of what fitbit calls the tracker_id.
            tracker_id.reverse()
            yield DbusTracker(tracker_id, path)

    def connect(self, tracker):
        self.tracker = self.bus.get('org.bluez', tracker.path)#['org.bluez.Device1']
        logger.debug(dir(self.tracker))
        if not self.tracker.Paired:
            logger.info("Pairing with tracker")
            self.tracker.Pair()
        if not self.tracker.Connected:
            logger.info("Connecting to tracker")
            self.tracker.Connect()
        # listen for PropertiesChanged
        # Now, wait for ServicesResolved to turn 'True' or some kind of timeout
        # continue.

        # We should make sure that we are selecting the one from the device we want to connect to ...
        for path, obj in self._getObjects('org.bluez.GattCharacteristic1', lambda obj: obj['UUID'] in (self.readUUID, self.writeUUID)):
            if obj['UUID'] == self.readUUID:
                self.read = self.bus.get('org.bluez', path)
            else:
                self.write = self.bus.get('org.bluez', path)

        def received(iface, changed, invalidated):
            logger.debug("received: %s", list(changed))
            value = changed.get('Value', [])
            if len(value) <= 1:
                logger.debug("Discarding %s", a2x(value))
                return
            logger.debug('received: %s', changed)
            self.readqueue.append(changed['Value'])

        self.read.onPropertiesChanged = received
        self.read.StartNotify()

        if not self._initializeAirlink(tracker):
            return False
        return True

    def _writeData(self, data):
        logger.debug('=> %s', data)
        self.write.WriteValue(data.data, {})


    def _readData(self, timeout=3000):
        """ So, read data only empty the queue """
        while not self.readqueue:
            if timeout <= 0:
                logger.debug("<= ...")
                return None
            timeout -= 100
            time.sleep(.1)
            self.loop.get_context().iteration(False)

        data = DM(bytearray(self.readqueue.pop(0)), False)
        logger.debug('<= %s', data)
        return data

    def disconnect(self, tracker):
        if self.read is not None:
            self.read.StopNotify()
            # unroll the loop
            context = self.loop.get_context()
            while context.pending():
                context.iteration(False)
            self.read.onPropertiesChanged = None
            self.read = None
        if self.readqueue:
            logger.warning("read queue not empty while disconecting.: %d", len(self.readqueue))
        if self.tracker is not None:
            logger.info("Disconnecting from tracker %s", tracker.id)
            self.tracker.Disconnect()
            self.tracker = None
        self.adapter.RemoveDevice(tracker.path)
        return True

    def info(self):
        return "BLE (via pydbus)"
