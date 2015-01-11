import errno

import logging
logger = logging.getLogger(__name__)

try:
    import usb.core
except ImportError, ie:
    # if ``usb`` is there, but not ``usb.core``, a pre-1.0 version of pyusb
    # is installed.
    try:
        import usb
    except ImportError:
        pass
    else:
        print "You have an older pyusb version installed. This utility needs"
        print "at least version 1.0.0a2 to work properly."
        print "Please upgrade your system to a newer version."
    raise ie

from .utils import a2x, a2s


class USBDevice(object):
    def __init__(self, vid, pid):
        self.vid = vid
        self.pid = pid
        self._dev = None

    @property
    def dev(self):
        if self._dev is None:
            self._dev = usb.core.find(idVendor=self.vid, idProduct=self.pid)
        return self._dev

    def __del__(self):
        if self._dev is not None:
            self._dev.reset()


class CtrlMessage(object):
    """ A message that get communicated over the ctrl link """
    def __init__(self, INS, data=[]):
        if INS is None:  # incoming
            self.len = data[0]
            self.INS = data[1]
            self.payload = data[2:self.len]
        else:  # outgoing
            self.len = len(data) + 2
            self.INS = INS
            self.payload = data

    def asList(self):
        return [self.len, self.INS] + self.payload

    def __str__(self):
        d = []
        if self.payload:
            d = ['(', a2x(self.payload), ')']
        return ' '.join(['%02X' % self.INS] + d + ['-', str(self.len)])

CM = CtrlMessage


class DataMessage(object):
    """ A message that get communicated over the data link """
    LENGTH = 32

    def __init__(self, data, out=True):
        if out:  # outgoing
            if len(data) > (self.LENGTH - 1):
                raise ValueError('data %s (%d) too big' % (data, len(data)))
            self.data = data
            self.len = len(data)
        else:  # incoming
            if len(data) != self.LENGTH:
                raise ValueError('data %s with wrong length' % data)
            # last byte is length
            self.len = data[-1]
            self.data = list(data[:self.len])

    def asList(self):
        return self.data + [0] * (self.LENGTH - 1 - self.len) + [self.len]

    def __str__(self):
        return ' '.join(['[', a2x(self.data), ']', '-', str(self.len)])

DM = DataMessage


def isATimeout(excpt):
    if excpt.errno == errno.ETIMEDOUT:
        return True
    elif excpt.errno is None and excpt.args == ('Operation timed out',):
        return True
    elif excpt.errno is None and excpt.strerror == 'Connection timed out':
        return True
    else:
        return False


class NoDongleException(Exception): pass


class TimeoutError(Exception): pass


class DongleWriteException(Exception): pass


class PermissionDeniedException(Exception): pass


def isStatus(data, msg=None, logError=True):
    if data.INS != 1:
        if logError:
            logging.warning("Message is not a status message: %x", data.INS)
        return False
    if msg is None:
        return True
    message = a2s(data.payload)
    if not message.startswith(msg):
        if logError:
            logging.warning("Message '%s' (received) is not '%s' (expected)",
                            message, msg)
        return False
    return True


class FitBitDongle(USBDevice):
    VID = 0x2687
    PID = 0xfb01

    def __init__(self):
        USBDevice.__init__(self, self.VID, self.PID)
        self.newerPyUSB = None

    def setup(self):
        if self.dev is None:
            raise NoDongleException()

        try:
            if self.dev.is_kernel_driver_active(0):
                self.dev.detach_kernel_driver(0)
            if self.dev.is_kernel_driver_active(1):
                self.dev.detach_kernel_driver(1)
        except usb.core.USBError, ue:
            if ue.errno == errno.EACCES:
                logger.error('Insufficient permissions to access the Fitbit'
                             ' dongle')
                raise PermissionDeniedException
            raise
        except NotImplementedError, nie:
            logger.error("Hit some 'Not Implemented Error': '%s', moving on ...", nie)

        cfg = self.dev.get_active_configuration()
        self.DataIF = cfg[(0, 0)]
        self.CtrlIF = cfg[(1, 0)]
        self.dev.set_configuration()

    def write(self, endpoint, data, timeout):
        if self.newerPyUSB:
            params = (endpoint, data, timeout)
        else:
            interface = {0x02: self.CtrlIF.bInterfaceNumber,
                         0x01: self.DataIF.bInterfaceNumber}[endpoint]
            params = (endpoint, data, interface, timeout)
        try:
            return self.dev.write(*params)
        except TypeError:
            if self.newerPyUSB is not None:
                # Already been there, something else is happening ...
                raise
            logger.debug('Switching to a newer pyusb compatibility mode')
            self.newerPyUSB = True
            return self.write(endpoint, data, timeout)
        except usb.core.USBError, ue:
            if ue.errno != errno.EIO:
                raise
        logger.info('Caught an I/O Error while writing, trying again ...')
        # IO Error, try again ...
        return self.dev.write(*params)

    def read(self, endpoint, length, timeout):
        if self.newerPyUSB:
            params = (endpoint, length, timeout)
        else:
            interface = {0x82: self.CtrlIF.bInterfaceNumber,
                         0x81: self.DataIF.bInterfaceNumber}[endpoint]
            params = (endpoint, length, interface, timeout)
        try:
            return self.dev.read(*params)
        except TypeError:
            if self.newerPyUSB is not None:
                # Already been there, something else is happening ...
                raise
            logger.debug('Switching to a newer pyusb compatibility mode')
            self.newerPyUSB = True
            return self.read(endpoint, length, timeout)
        except usb.core.USBError, ue:
            if isATimeout(ue):
                raise TimeoutError
            raise

    def ctrl_write(self, msg, timeout=2000):
        logger.debug('--> %s', msg)
        l = self.write(0x02, msg.asList(), timeout)
        if l != msg.len:
            logger.error('Bug, sent %d, had %d', l, msg.len)
            raise DongleWriteException

    def ctrl_read(self, timeout=2000, length=32):
        data = self.read(0x82, length, timeout)
        msg = CM(None, list(data))
        if isStatus(msg, logError=False):
            logger.debug('<-- %s', a2s(msg.payload))
        else:
            logger.debug('<-- %s', msg)
        return msg

    def data_write(self, msg, timeout=2000):
        logger.debug('==> %s', msg)
        l = self.write(0x01, msg.asList(), timeout)
        if l != msg.LENGTH:
            logger.error('Bug, sent %d, had %d', l, msg.LENGTH)
            raise DongleWriteException

    def data_read(self, timeout=2000):
        data = self.read(0x81, DM.LENGTH, timeout)
        msg = DM(data, out=False)
        logger.debug('<== %s', msg)
        return msg
