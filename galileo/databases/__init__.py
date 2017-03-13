class Database(object):
    def sync(self, trackerId, megadump, dongle):
        raise NotImplementedError("This is a method of an abstract class!")


class SyncError(Exception):
    def __init__(self, errorstring='Undefined'):
        self.errorstring = errorstring
