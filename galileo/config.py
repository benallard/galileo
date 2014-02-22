
import logging
logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    from . import parser as yaml

class Config(object):
    """Class holding the configuration to be applied during synchronization.
    The configuration can be loaded from a file in which case the defaults
    can be overridden; loading from multiple files allows the settings from
    later files to override those defined in earlier files. Finally, each
    configuration option can also be set directly, which is used to allow
    overriding of file-based configuration settings with those explicitly
    specified on the command line.
    """

    DEFAULT_DUMP_DIR = "~/.galileo"
    DEFAULT_DAEMON_PERIOD = 15000 # 15 seconds

    def __init__(self):
        self.__logLevelMap = { 'default': logging.WARNING,
                               'verbose': logging.INFO,
                               'debug': logging.DEBUG }
        self.__logLevelMapReverse = {}
        for key, value in self.__logLevelMap.iteritems():
            self.__logLevelMapReverse[value] = key
        self.__logLevel = logging.WARNING
        self._includeTrackers = None
        self._excludeTrackers = []
        self._keepDumps = True
        self._dumpDir = self.DEFAULT_DUMP_DIR
        self._doUpload = True
        self._forceSync = False
        self._daemonPeriod = self.DEFAULT_DAEMON_PERIOD

    # Property accessors and definitions
    @property
    def logLevel(self):
        """Logging level. Values are as defined in Logging.setLevel() and can
        be set as an integer or string.

        """
        return self.__logLevel

    @logLevel.setter
    def logLevel(self, value):
        if isinstance(value, basestring):
            self.__logLevel = self.__logLevelMap[str(value).lower()]
        else:
            self.__logLevel = value

    @property
    def keepDumps(self):
        """Flag indicate data from tracker should be saved."""
        return self._keepDumps

    @keepDumps.setter
    def keepDumps(self, value): self._keepDumps = value

    @property
    def includeTrackers(self):
        """List of trackers to synchronize, or None for to synchronize all.
        Can be set via a comma-separated list string or from a list.

        """
        return self._includeTrackers

    @includeTrackers.setter
    def includeTrackers(self, value):
        if isinstance(value, basestring):
            self._includeTrackers = value.split(',')
        else:
            self._includeTrackers = value
        # Now make sure the list of trackers is all in upper-case to
        # make comparisons easier later.
        if self._includeTrackers is not None:
            self._includeTrackers = [str(x).upper() for x in self._includeTrackers]

    @property
    def excludeTrackers(self):
        """List of trackers to avoid synchronizing. Can be set via a
        comma-separated list string or from a list.

        """
        return self._excludeTrackers

    @excludeTrackers.setter
    def excludeTrackers(self, value):
        if isinstance(value, basestring):
            self._excludeTrackers = value.split(',')
        else:
            self._excludeTrackers = value
        # Now make sure the list of trackers is all in upper-case to
        # make comparisons easier later.
        if self._excludeTrackers is not None:
            self._excludeTrackers = [str(x).upper() for x in self._excludeTrackers]

    @property
    def dumpDir(self):
        """Directory where tracker data should be saved."""
        return self._dumpDir

    @dumpDir.setter
    def dumpDir(self, value): self._dumpDir = value

    @property
    def doUpload(self):
        """Flag indicating whether data from trackers should be uploaded."""
        return self._doUpload

    @doUpload.setter
    def doUpload(self, value): self._doUpload = value

    @property
    def forceSync(self):
        """Flag indicating whether trackers should be synchronized even if
        recently synchronized.

        """
        return self._forceSync

    @forceSync.setter
    def forceSync(self, value): self._forceSync = value

    @property
    def daemonPeriod(self):
        """Delay between successive synchronizations when running in daemon
        mode. Delay is specified in milliseconds (e.g. 15000=15s).

        """
        return self._daemonPeriod

    @daemonPeriod.setter
    def daemonPeriod(self, value): self._daemonPeriod = value

    def load(self, filename):
        """Load configuration settings from the named YAML-format
        configuration file. This configuration file can include a
        subset of possible parameters in which case only those
        parameters are changed by the load operation.

        Arguments:
        - `filename`: The name of the file to load parameters from.

        """
        if yaml is None:
            logger.warning("yaml package not found, not parsing %s", filename)
            return
        with open(filename, 'rt') as f:
            config = yaml.load(f)

        # Pick the settings out of the loaded configuration.
        if 'keep-dumps' in config:
            self.keepDumps = config['keep-dumps']
        if 'do-upload' in config:
            self.doUpload = config['do-upload']
        if 'dump-dir' in config:
            self.dumpDir = config['dump-dir']
        if 'logging' in config:
            self.logLevel = config['logging']
        if 'force-sync' in config:
            self.forceSync = config['force-sync']
        if 'include-trackers' in config:
            self.includeTrackers = config['include-trackers']
        if 'exclude-trackers' in config:
            self.excludeTrackers = config['exclude-trackers']
        if 'daemon-period' in config:
            self.daemonPeriod = config['daemon-period']

    def shouldSkipTracker(self, trackerid):
        """Method to check, based on the configuration, whether a particular
        tracker should be skipped and not synchronized. The
        includeTrackers and excludeTrackers properties are checked to
        determine this.

        Arguments:
        - `trackerid`: Tracker ID (hexadecimal string), to check.

        """

        shouldSkip = False

        # Make sure the tracker ID is in upper-case so that string
        # comparisons with our lists of tracker IDs work.
        trackerid = str(trackerid).upper()

        # If a list of trackers to sync is configured then was
        # provided then ignore this tracker if it's not in that list.
        if (self._includeTrackers is not None) and (trackerid not in self._includeTrackers):
            shouldSkip = True

        # If a list of trackers to avoid syncing is configured then
        # ignore this tracker if it is in that list.
        if trackerid in self._excludeTrackers:
            shouldSkip = True

        return shouldSkip

    def __str__(self):
        return ("Config: logLevel = %s, " +
                "keepDumps = %s, " +
                "includeTrackers = %s, " +
                "excludeTrackers = %s, " +
                "dumpDir = %s, " +
                "doUpload = %s, " +
                "forceSync = %s, " +
                "daemonPeriod = %d") % (
                    self.__logLevelMapReverse[self.__logLevel],
                    self._keepDumps,
                    self._includeTrackers,
                    self._excludeTrackers,
                    self._dumpDir,
                    self._doUpload,
                    self._forceSync,
                    self._daemonPeriod)
