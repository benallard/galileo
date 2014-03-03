import argparse
import logging
logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    from . import parser as yaml

from .utils import a2x


class Config(object):
    """Class holding the configuration to be applied during synchronization.
    The configuration can be loaded from a file in which case the defaults
    can be overridden; loading from multiple files allows the settings from
    later files to override those defined in earlier files. Finally, each
    configuration option can also be set directly, which is used to allow
    overriding of file-based configuration settings with those explicitly
    specified on the command line.
    """

    DEFAULT_RCFILE_NAME = "~/.galileorc"
    DEFAULT_DUMP_DIR = "~/.galileo"
    DEFAULT_DAEMON_PERIOD = 15000  # 15 seconds

    def __init__(self):
        self.__logLevelMap = {'default': logging.WARNING,
                              'verbose': logging.INFO,
                              'debug': logging.DEBUG}
        self.__logLevelMapReverse = {}
        for key, value in self.__logLevelMap.iteritems():
            self.__logLevelMapReverse[value] = key
        self.__logLevel = logging.WARNING
        self._includeTrackers = None
        self._excludeTrackers = set()
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
        if self._includeTrackers is None:
            self._includeTrackers = set()
        if isinstance(value, basestring):
            value = value.split(',')
        # Now make sure the list of trackers is all in upper-case to
        # make comparisons easier later.
        value = [x.upper() for x in value]
        self._includeTrackers.update(value)

    @property
    def excludeTrackers(self):
        """List of trackers to avoid synchronizing. Can be set via a
        comma-separated list string or from a list.

        """
        return self._excludeTrackers

    @excludeTrackers.setter
    def excludeTrackers(self, value):
        if isinstance(value, basestring):
            value = value.split(',')
        # Now make sure the list of trackers is all in upper-case to
        # make comparisons easier later.
        value = [x.upper() for x in value]
        self._excludeTrackers.update(value)

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

    def parse_args(self):
        # Define and parse command-line arguments.
        argparser = argparse.ArgumentParser(description="synchronize Fitbit trackers with Fitbit web service",
                                            epilog="""Access your synchronized data at http://www.fitbit.com.""")
        argparser.add_argument("-V", "--version",
                               action="store_true", dest='version',
                               help="show version and exit")
        argparser.add_argument("-c", "--config",
                               metavar="FILE", dest="rcconfigname",
                               help="use alternative configuration file (defaults to '%s')" % self.DEFAULT_RCFILE_NAME)
        argparser.add_argument("--dump-dir",
                               metavar="DIR", dest="dump_dir",
                               help="directory for storing dumps (defaults to '%s')" % Config.DEFAULT_DUMP_DIR)
        argparser.add_argument("--daemon-period",
                               metavar="PERIOD", dest="daemon_period", type=int,
                               help="sleep time in msec between sync runs when in daemon mode (defaults to '%d')" %
                               (Config.DEFAULT_DAEMON_PERIOD))
        verbosity_arggroup = argparser.add_argument_group("progress reporting control")
        verbosity_arggroup2 = verbosity_arggroup.add_mutually_exclusive_group()
        verbosity_arggroup2.add_argument("-v", "--verbose",
                                         action="store_true",
                                         help="display synchronization progress")
        verbosity_arggroup2.add_argument("-d", "--debug",
                                         action="store_true",
                                         help="show internal activity (implies verbose)")
        verbosity_arggroup2.add_argument("-q", "--quiet",
                                         action="store_true",
                                         help="only show errors and summary (default)")
        force_arggroup = argparser.add_argument_group("force synchronization control")
        force_arggroup2 = force_arggroup.add_mutually_exclusive_group()
        force_arggroup2.add_argument("--force",
                                     action="store_true",
                                     help="synchronize even if tracker reports a recent sync")
        force_arggroup2.add_argument("--no-force",
                                     action="store_true", dest="no_force",
                                     help="do not synchronize if tracker reports a recent sync (default)")
        dump_arggroup = argparser.add_argument_group("dump control")
        dump_arggroup2 = dump_arggroup.add_mutually_exclusive_group()
        dump_arggroup2.add_argument("--dump",
                                    action="store_true",
                                    help="enable saving of the megadump to file (default)")
        dump_arggroup2.add_argument("--no-dump",
                                    action="store_true", dest="no_dump",
                                    help="disable saving of the megadump to file")
        upload_arggroup = argparser.add_argument_group("upload control")
        upload_arggroup2 = upload_arggroup.add_mutually_exclusive_group()
        upload_arggroup2.add_argument("--upload",
                                      action="store_true",
                                      help="upload the dump to the server (default)")
        upload_arggroup2.add_argument("--no-upload",
                                      action="store_true", dest="no_upload",
                                      help="do not upload the dump to the server")
        argparser.add_argument("-I", "--include",
                               nargs="+", metavar="ID",
                               help="list of tracker IDs to sync (all if not specified)")
        argparser.add_argument("-X", "--exclude",
                               nargs="+", metavar="ID",
                               help="list of tracker IDs to not sync")
        argparser.add_argument('mode', default='sync', nargs='?',
                               choices=['sync', 'daemon'], metavar="MODE",
                               help="The mode to run (default to 'sync')")
        return argparser.parse_args()

    def apply_cmdlineargs(self, cmdlineargs):
        """ Override rcfile-provided values with those on the command-line. """

        # Logging
        if cmdlineargs.verbose:
            self.logLevel = 'verbose'
        elif cmdlineargs.debug:
            self.logLevel = 'debug'
        elif cmdlineargs.quiet:
            self.logLevel = 'default'

        # Basic logging configuration.
        logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s',
                            level=self.logLevel)
        # --- All logger actions from now on will be effective ---

        logger.info("Running in mode: %s", cmdlineargs.mode)
        logger.debug("Config after load before cmdline overrides = %s", self)

        # Sleep time when in daemon mode
        if cmdlineargs.daemon_period is not None:
            self.daemonPeriod = cmdlineargs.daemon_period

        # Includes
        if cmdlineargs.include:
            self.includeTrackers = cmdlineargs.include

        # Excludes
        if cmdlineargs.exclude:
            self.excludeTrackers = cmdlineargs.exclude

        # Keep dumps (or not)
        if cmdlineargs.no_dump:
            self.keepDumps = False
        elif cmdlineargs.dump:
            self.keepDumps = True

        # Dump directory
        if cmdlineargs.dump_dir:
            self.dumpDir = cmdlineargs.dump_dir

        # Upload data (or not)
        if cmdlineargs.no_upload:
            self.doUpload = False
        elif cmdlineargs.upload:
            self.doUpload = True

        # Force (or not)
        if cmdlineargs.no_force:
            self.forceSync = False
        elif cmdlineargs.force:
            self.forceSync = True

        logger.debug("Config after cmdline ovverides = %s", self)

    def shouldSkip(self, tracker):
        """Method to check, based on the configuration, whether a particular
        tracker should be skipped and not synchronized. The
        includeTrackers and excludeTrackers properties are checked to
        determine this.

        Arguments:
        - `tracker`: Tracker (object), to check.

        """
        trackerid = a2x(tracker.id, delim='')

        # If a list of trackers to sync is configured then was
        # provided then ignore this tracker if it's not in that list.
        if (self._includeTrackers is not None) and (trackerid not in self._includeTrackers):
            logger.info("Include list not empty, and tracker %s not there, skipping.", trackerid)
            return True

        # If a list of trackers to avoid syncing is configured then
        # ignore this tracker if it is in that list.
        if trackerid in self._excludeTrackers:
            logger.info("Tracker %s in exclude list, skipping.", trackerid)
            return True

        if tracker.syncedRecently:
            if not self.forceSync:
                logger.info('Tracker %s was recently synchronized; skipping for now', trackerid)
                return True
            logger.info('Tracker %s was recently synchronized, but forcing synchronization anyway', trackerid)

        return False

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
