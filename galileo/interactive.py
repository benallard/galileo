"""\
This is the implementation of the interactive mode

This is the same idea as ifitbit I wrote for libfitbit some years ago

https://bitbucket.org/benallard/libfitbit/src/tip/python/ifitbit.py?at=default

"""

#---------------------------
# The engine

import traceback
import sys

exit = None

cmds = {}
helps = {}

def command(cmd, help):
    def decorator(fn):
        cmds[cmd] = fn
        helps[cmd] = help
        def wrapped(*args):
            return fn(*args)
        return wrapped
    return decorator


@command('x', "Quit")
def quit():
    print 'Bye !'
    global exit
    exit = True


@command('?', 'Print possible commands')
def print_help():
    for cmd in sorted(helps.keys()):
        print '%s\t%s' % (cmd, helps[cmd])


def main(config):
    global exit
    exit = False
    print_help()
    while not exit:
        input = raw_input('> ').strip()
        input = input.split(' ')
        try:
            f = cmds[input[0]]
        except KeyError:
            if input[0] == '':
                continue
            print 'Command %s not known' % input[0]
            print_help()
            continue
        try:
            f(*input[1:])
        except TypeError, te:
            print "Wrong number of argument given: %s" % te
        except Exception, e:
            # We need that to be able to close the connection nicely
            print "BaD bAd BAd", e
            traceback.print_exc(file=sys.stdout)
            exit = True


#---------------------------
# The commands

from .dongle import FitBitDongle, CM, DM
from .tracker import FitbitClient
from .utils import x2a

import uuid

dongle = None
fitbit = None
trackers = []
tracker = None

@command('c', "Connect")
def connect():
    global dongle
    dongle = FitBitDongle()
    if dongle.setup() != True:
        print "No dongle connected, aborting"
        quit()
    global fitbit
    fitbit = FitbitClient(dongle)
    print 'Ok'


def needfitbit(fn):
    def wrapped(*args):
        if dongle is None:
            print "No connection, connect (c) first"
            return
        return fn(*args)
    return wrapped

@command('->', "Send on the control channel")
@needfitbit
def send_ctrl(INS, *payload):
    if payload:
        payload = x2a(' '.join(payload))
    else:
        payload = []
    m = CM(int(INS, 16), payload)
    dongle.ctrl_write(m)

@command('<-', "Receive once on the control channel")
@needfitbit
def receive_ctrl(param='1'):
    if param == '-':
        goOn = True
        while goOn:
            goOn = dongle.ctrl_read() is not None
    else:
        for i in range(int(param)):
            dongle.ctrl_read()

@command('=>', "Send on the control channel")
@needfitbit
def send_data(*payload):
    m = DM(x2a(' '.join(payload)))
    dongle.data_write(m)

@command('<=', "Receive once on the control channel")
@needfitbit
def receive_data(param='1'):
    if param == '-':
        goOn = True
        while goOn:
            goOn = dongle.data_read() is not None
    else:
        for i in range(int(param)):
            dongle.data_read()

@command('d', "Discovery")
@needfitbit
def discovery(UUID="{ADAB0000-6E7D-4601-BDA2-BFFAA68956BA}"):
    UUID = uuid.UUID(UUID)
    global trackers
    trackers = [t for t in fitbit.discover(UUID)]


def needtrackers(fn):
    def wrapped(*args):
        if not trackers:
            print "No trackers, run a discovery (d) first"
            return
        return fn(*args)
    return wrapped

@command('l', "establishLink")
@needtrackers
def establishLink(idx='0'):
    global tracker
    tracker = trackers[int(idx)]
    if fitbit.establishLink(tracker):
        print 'Ok'
    else:
        tracker = None

def needtracker(fn):
    def wrapped(*args):
        if tracker is None:
            print "No tracker, establish a Link (l) first"
            return
        return fn(*args)
    return wrapped

@command('tx', "toggle Tx Pipe")
@needfitbit
def toggleTxPipe(on):
    if fitbit.toggleTxPipe(bool(int(on))):
        print 'Ok'

@command('al', "initialise airLink")
@needtracker
def initialiseAirLink():
    if fitbit.initializeAirlink(tracker):
        print 'Ok'

@command('AL', "terminate airLink")
@needfitbit
def terminateairLink():
    if fitbit.terminateAirlink():
        print 'Ok'

@command('D', 'getDump')
@needfitbit
def getDump():
    fitbit.getDump()

@command('R', 'uploadResponse')
@needfitbit
def uploadResponse(*response):
    response = x2a(' '.join(response))
    fitbit.uploadResponse(response)
