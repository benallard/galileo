
import argparse
import datetime
import os
import sys
import time

import logging
logger = logging.getLogger(__name__)

import requests

from . import __version__
from .config import Config
from .dongle import (
    FitBitDongle, TimeoutError, NoDongleException, PermissionDeniedException
)
from .net import GalileoClient, SyncError, BackOffException
from .tracker import FitbitClient
from .utils import a2x


DEFAULT_RCFILE_NAME = "~/.galileorc"


def syncAllTrackers(config):
    logger.debug('%s initialising', os.path.basename(sys.argv[0]))
    dongle = FitBitDongle()
    try:
        dongle.setup()
    except NoDongleException:
        logger.error("No dongle connected, aborting")
        return (0, 0, 0)

    fitbit = FitbitClient(dongle)

    galileo = GalileoClient('https://client.fitbit.com/tracker/client/message')

    fitbit.disconnect()

    fitbit.getDongleInfo()

    logger.info('Discovering trackers to synchronize')
    try:
        trackers = [t for t in fitbit.discover()]
    except TimeoutError:
        logger.debug('Timeout trying to discover trackers')
        trackers = []

    trackerssyncd = 0
    trackersskipped = 0
    trackercount = len(trackers)
    logger.info('%d trackers discovered', trackercount)
    for tracker in trackers:
        logger.debug('Discovered tracker with ID %s', a2x(tracker.id, delim=""))

    for tracker in trackers:

        trackerid = a2x(tracker.id, delim="")

        # Skip this tracker based on include/exclude lists.
        if config.shouldSkip(tracker):
            logger.info('Tracker %s is to be skipped due to configuration; skipping', trackerid)
            trackersskipped += 1
            continue

        logger.info('Attempting to synchronize tracker %s', trackerid)

        logger.debug('Connecting to Fitbit server and requesting status')
        try:
            galileo.requestStatus()
        except requests.exceptions.ConnectionError:
            # No internet connection or fitbit server down
            logger.error('Not able to connect to the Fitbit server. Check your internet connection')
            return

        logger.debug('Establishing link with tracker')
        try:
            fitbit.establishLink(tracker)
            fitbit.enableTxPipe()
            fitbit.initializeAirlink()
        except TimeoutError:
            trackersskipped += 1
            logger.debug('Timeout while trying to establish link with tracker')
            logger.warning('Unable to establish link with tracker %s. Skipping it.', trackerid)
            continue

        logger.info('Getting data from tracker')
        dump = fitbit.getDump()

        if config.keepDumps:
            # Write the dump somewhere for archiving ...
            dirname = os.path.expanduser(os.path.join(config.dumpDir, trackerid))
            if not os.path.exists(dirname):
                logger.debug("Creating non-existent directory for dumps %s", dirname)
                os.makedirs(dirname)

            filename = os.path.join(dirname, 'dump-%d.txt' % int(time.time()))
            dump.toFile(filename)
        else:
            logger.debug("Not dumping anything to disk")

        if not config.doUpload:
            logger.info("Not uploading, as asked ...")
        else:
            logger.info('Sending tracker data to Fitbit')
            try:
                response = galileo.sync(fitbit, trackerid, dump)

                if config.keepDumps:
                    logger.debug("Appending answer from server to %s", filename)
                    with open(filename, 'at') as dumpfile:
                        dumpfile.write('\n')
                        for i in range(0, len(response), 20):
                            dumpfile.write(a2x(response[i:i + 20]) + '\n')

                # Even though the next steps might fail, fitbit has accepted
                # the data at this point.
                trackerssyncd += 1
                logger.info('Successfully sent tracker data to Fitbit')

                logger.info('Passing Fitbit response to tracker')
                try:
                    fitbit.uploadResponse(response)
                except TimeoutError:
                    logger.warning('Timeout error while trying to give Fitbit response to tracker %s', trackerid)

            except SyncError, e:
                logger.error('Fitbit server refused data from tracker %s, reason: %s', trackerid, e.errorstring)

        logger.debug('Disconnecting from tracker')
        try:
            fitbit.disableTxPipe()
            fitbit.terminateAirlink()
        except TimeoutError:
            logger.warning('Timeout while trying to disconnect from tracker %s', trackerid)

    return (trackercount, trackerssyncd, trackersskipped)

PERMISSION_DENIED_HELP = """
To be able to run the fitbit utility as a non-privileged user, you first
should install a 'udev rule' that lower the permissions needed to access the
fitbit dongle. In order to do so, as root, create the file
/etc/udev/rules.d/99-fitbit.rules with the following content (in one line):

SUBSYSTEM=="usb", ATTR{idVendor}=="%(VID)x", ATTR{idProduct}=="%(PID)x", SYMLINK+="fitbit", MODE="0666"

The dongle must then be removed and reinserted to receive the new permissions.""" % {
    'VID': FitBitDongle.VID, 'PID': FitBitDongle.PID}


def version(verbose, delim='\n'):
    s = ['%s: %s' % (sys.argv[0], __version__)]
    if verbose:
        import usb
        import platform
        from .config import yaml
        # To get it on one line
        s.append('Python: %s' % ' '.join(sys.version.split()))
        s.append('Platform: %s' % ' '.join(platform.uname()))
        s.append('pyusb: %s' % usb.__version__)
        s.append('requests: %s' % requests.__version__)
        if hasattr(yaml, '__with_libyaml__'):
            # Genuine PyYAML
            s.append('yaml: %s (%s libyaml)' % (
                yaml.__version__,
                yaml.__with_libyaml__ and 'with' or 'without'))
        else:
            # Custom version
            s.append('yaml: own version')
    return delim.join(s)


def sync(config):
    try:
        total, success, skipped = syncAllTrackers(config)
    except BackOffException, boe:
        print "The server requested that we come back between %d and %d"\
            " minutes." % (boe.min / 60*1000, boe.max / 60*1000)
        later = datetime.datetime.now() + datetime.timedelta(
            microseconds=boe.getAValue()*1000)
        print "I suggest waiting until %s" % later
        return
    except PermissionDeniedException:
        print PERMISSION_DENIED_HELP
        return
    print '%d trackers found, %d skipped, %d successfully synchronized' % (
        total, skipped, success)


def daemon(config):
    goOn = True
    while goOn:
        try:
            # TODO: Extract the initialization part, and do it once for all
            try:
                syncAllTrackers(config)
            except BackOffException, boe:
                logger.warning("Received a back-off notice from the server,"
                               " waiting for a bit longer.")
                time.sleep(boe.getAValue())
            else:
                logger.info("Sleeping for %d seconds before next sync", config.daemonPeriod / 1000)
                time.sleep(config.daemonPeriod / 1000.)
        except KeyboardInterrupt:
            print "Ctrl-C, caught, stopping ..."
            goOn = False


def main():
    """ This is the entry point """
    # Define and parse command-line arguments.
    argparser = argparse.ArgumentParser(description="synchronize Fitbit trackers with Fitbit web service",
                                        epilog="""Access your synchronized data at http://www.fitbit.com.""")
    argparser.add_argument("-V", "--version",
                           action="store_true", dest='version',
                           help="show version and exit")
    argparser.add_argument("-c", "--config",
                           metavar="FILE", dest="rcconfigname",
                           help="use alternative configuration file (defaults to '%s')" % DEFAULT_RCFILE_NAME)
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
    cmdlineargs = argparser.parse_args()

    # If an alternative config filename was provided then use it.
    if cmdlineargs.rcconfigname:
        rcconfigname = os.path.expanduser(cmdlineargs.rcconfigname)
    else:
        rcconfigname = os.path.expanduser(DEFAULT_RCFILE_NAME)

    # Load the configuration.
    config = Config()
    if os.path.exists(rcconfigname):
        logger.debug("Trying to load config file: %s", rcconfigname)
        logger.debug("Config before load = %s", config)
        try:
            config.load(rcconfigname)
        except IOError:
            logger.warning('Unable to load configuration file: %s', rcconfigname)

    # Override rcfile-provided values with those on the command-line.

    # Logging
    if cmdlineargs.verbose:
        config.logLevel = 'verbose'
    elif cmdlineargs.debug:
        config.logLevel = 'debug'
    elif cmdlineargs.quiet:
        config.logLevel = 'default'

    # Basic logging configuration.
    logging.basicConfig(format='%(asctime)s:%(levelname)s: %(message)s',
                        level=config.logLevel)
    # --- All logger actions from now on will be effective ---

    logger.info("Running in mode: %s", cmdlineargs.mode)
    logger.debug("Config after load before cmdline overrides = %s", config)

    # Sleep time when in daemon mode
    if cmdlineargs.daemon_period is not None:
        config.daemonPeriod = cmdlineargs.daemon_period

    # Includes
    if cmdlineargs.include:
        config.includeTrackers = cmdlineargs.include

    # Excludes
    if cmdlineargs.exclude:
        config.excludeTrackers = cmdlineargs.exclude

    # Keep dumps (or not)
    if cmdlineargs.no_dump:
        config.keepDumps = False
    elif cmdlineargs.dump:
        config.keepDumps = True

    # Dump directory
    if cmdlineargs.dump_dir:
        config.dumpDir = cmdlineargs.dump_dir

    # Upload data (or not)
    if cmdlineargs.no_upload:
        config.doUpload = False
    elif cmdlineargs.upload:
        config.doUpload = True

    # Force (or not)
    if cmdlineargs.no_force:
        config.forceSync = False
    elif cmdlineargs.force:
        config.forceSync = True

    logger.debug("Config after cmdline ovverides = %s", config)

    if cmdlineargs.version:
        print version(config.logLevel in (logging.INFO, logging.DEBUG))
        return

    try:
        {
            'sync': sync,
            'daemon': daemon,
        }[cmdlineargs.mode](config)
    except:
        print "# A serious error happened, which is probably due to a"
        print "# programming error. Please open a new issue with the following"
        print "# information on the galileo bug tracker:"
        print "#    https://bitbucket.org/benallard/galileo/issues/new"
        print '#', version(True, '\n# ')
        raise
