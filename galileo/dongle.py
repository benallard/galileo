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
        pass


class DataMessage(object):
    length = 32

    def __init__(self, data, out=True):
        if out:  # outgoing
            if len(data) > 31:
                raise ValueError('data %s (%d) too big' % (data, len(data)))
            self.data = data
            self.len = len(data)
        else:  # incoming
            if len(data) != 32:
                raise ValueError('data %s with wrong length' % data)
            # last byte is length
            self.len = data[-1]
            self.data = list(data[:self.len])

    def asList(self):
        return self.data + [0] * (31 - self.len) + [self.len]

    def __str__(self):
        return ' '.join(['[', a2x(self.data), ']', '-', str(self.len)])

DM = DataMessage


def isATimeout(excpt):
    if excpt.errno == errno.ETIMEDOUT:
        return True
    elif excpt.errno is None and excpt.args == ('Operation timed out',):
        return True
    else:
        return False


class NoDongleException(Exception): pass


class TimeoutError(Exception): pass


class DongleWriteException(Exception): pass


class PermissionDeniedException(Exception): pass

def isStatus(data, msg=None):
    if data[:2] != [0x20, 1]:
        return False
    if msg is None:
        return True
    return a2s(data[2:]) == msg

class FitBitDongle(USBDevice):
    VID = 0x2687
    PID = 0xfb01

    def __init__(self):
        USBDevice.__init__(self, self.VID, self.PID)

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

        cfg = self.dev.get_active_configuration()
        self.DataIF = cfg[(0, 0)]
        self.CtrlIF = cfg[(1, 0)]
        self.dev.set_configuration()

    def ctrl_write(self, data, timeout=2000):
        logger.debug('--> %s', a2x(data))
        l = self.dev.write(0x02, data, self.CtrlIF.bInterfaceNumber, timeout)
        if l != len(data):
            logger.error('Bug, sent %d, had %d', l, len(data))
            raise DongleWriteException

    def ctrl_read(self, timeout=2000, length=32):
        try:
            data = self.dev.read(0x82, length, self.CtrlIF.bInterfaceNumber,
                                 timeout)
        except usb.core.USBError, ue:
            if isATimeout(ue):
                raise TimeoutError
            raise
        data = list(data)
        if isStatus(data):
            logger.debug('<-- %s %s', a2x(data[:2]), a2s(data[2:]))
        else:
            logger.debug('<-- %s', a2x(data, shorten=True))
        return data

    def data_write(self, msg, timeout=2000):
        logger.debug('==> %s', msg)
        l = self.dev.write(0x01, msg.asList(), self.DataIF.bInterfaceNumber,
                           timeout)
        if l != 32:
            logger.error('Bug, sent %d, had 32', l)
            raise DongleWriteException

    def data_read(self, timeout=2000):
        try:
            data = self.dev.read(0x81, 32, self.DataIF.bInterfaceNumber,
                                 timeout)
        except usb.core.USBError, ue:
            if isATimeout(ue):
                raise TimeoutError
            raise
        msg = DM(data, out=False)
        logger.debug('<== %s', msg)
        return msg
