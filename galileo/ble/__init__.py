class API(object):
    """ This is the general class to subclass in order to implement a bluetooth
    API """
    def __init__(self, logSize):
        """ the logsize parameter indicates how  many of the communication
        should be displayed """
        raise NotImplementedError

    def setup(self):
        """This returns a boolean indicating the success of the operation"""
        raise NotImplementedError
