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
