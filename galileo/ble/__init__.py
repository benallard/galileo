from ..utils import a2x

class API(object):
    def setup(self):
        raise NotImplementedError
    def disconnectAll(self):
        pass
    def getHardwareInfo(self):
        pass
    def discover(self, UUID):
        raise NotImplementedError
    def connect(self, tracker):
        raise NotImplementedError
    def getDump(self):
        raise NotImplementedError
    def uploadResponse(self, dump):
        raise NotImplementedError
    def disconnect(self, tracker):
        raise NotImplementedError


class DataMessage(object):
    """ A message that get communicated over the BLE link """
    LENGTH = 32

    def __init__(self, data, out=True):
        if out:  # outgoing
            if len(data) > (self.LENGTH - 1):
                raise ValueError('data %s (%d) too big' % (data, len(data)))
            self.data = bytearray(data)
            self.len = len(data)
        else:  # incoming
            if len(data) == self.LENGTH:
                # last byte is length
                self.len = data[-1]
                self.data = bytearray(data[:self.len])
            else:
                # Same as outgoing actually
                self.__init__(data)

    def asList(self):
        return self.data + b'\x00' * (self.LENGTH - 1 - self.len) + bytearray([self.len])

    def __eq__(self, other):
        if other is None: return False
        return self.data == other.data

    def __ne__(self, other):
        return not self == other

    def __str__(self):
        return ' '.join(['[', a2x(self.data), ']', '-', str(self.len)])

DM = DataMessage
