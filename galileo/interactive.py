"""\
This is the implementation of the interactive mode

This is the same idea as ifitbit I wrote for libfitbit some years ago

https://bitbucket.org/benallard/libfitbit/src/tip/python/ifitbit.py?at=default

"""

from __future__ import print_function

try:
    # Override the input from python2 with raw_input
    input = raw_input
except NameError:
    pass

#---------------------------
# The engine

import readline
import traceback
import sys

exit = None

cmds = {}
helps = {}
config = None

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
    print('Bye !')
    global exit
    exit = True


@command('?', 'Print possible commands')
def print_help():
    for cmd in sorted(helps.keys()):
        print('%s\t%s' % (cmd, helps[cmd]))
    print("""Note:
 - You can enter multiple commands separated by ';'
 - To establish a link with the tracker, enter the following command:
      s ; d ; c (setup the bluetooth connection, discover the trackers, and connect)
""")

def main(_config):
    global exit
    exit = False
    global config
    config = _config
    print_help()
    while not exit:
        orders = input('> ').strip()
        if ';' in orders:
            orders = orders.split(';')
        else:
            orders = [orders]
        for order in orders:
            order = order.strip().split(' ')
            try:
                f = cmds[order[0]]
            except KeyError:
                if order[0] == '':
                    continue
                print('Command %s not known' % order[0])
                print_help()
                continue
            try:
                f(*order[1:])
            except TypeError as te:
                print("Wrong number of argument given: %s" % te)
            except Exception as e:
                # We need that to be able to close the connection nicely
                print("BaD bAd BAd", e)
                traceback.print_exc(file=sys.stdout)
                return


#---------------------------
# The commands

from .ble import DM
from .dongle import CM
from .utils import x2a

import uuid

fitbit = None
trackers = []
tracker = None

@command('s', "Setup the bluetooth connection")
def connect():
    global fitbit
    fitbit = config.bluetoothConn(0)
    fitbit.setup()
    print('Ok')


def needfitbit(fn):
    def wrapped(*args):
        if fitbit is None:
            print("No connection, connect (c) first")
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
    fitbit.ctrl_write(m)

@command('<-', "Receive once on the control channel")
@needfitbit
def receive_ctrl(param='1'):
    if param == '-':
        goOn = True
        while goOn:
            goOn = fitbit.ctrl_read() is not None
    else:
        for i in range(int(param)):
            fitbit.ctrl_read()

@command('=>', "Send on the bluetooth channel")
@needfitbit
def send_data(*payload):
    m = DM(x2a(' '.join(payload)))
    fitbit._writeData(m)

@command('<=', "Receive once on the bluetooth channel")
@needfitbit
def receive_data(param='1'):
    if param == '-':
        goOn = True
        while goOn:
            goOn = fitbit._readData() is not None
    else:
        for i in range(int(param)):
            fitbit._readData()

@command('d', "Discovery")
@needfitbit
def discovery(UUID="{ADAB0000-6E7D-4601-BDA2-BFFAA68956BA}", service="0xfb00", read="0xfb01", write=0xfb02, minRSSI="-255", timeout="4000"):
    UUID = uuid.UUID(UUID)
    global trackers
    trackers = [t for t in fitbit.discover(UUID, int(service, 0), int(read, 0), int(write, 0), int(minRSSI, 0), int(timeout, 0))]


def needtrackers(fn):
    def wrapped(*args):
        if not trackers:
            print("No trackers, run a discovery (d) first")
            return
        return fn(*args)
    return wrapped

@command('c', "Connect to the given tracker (default 0)")
@needtrackers
def establishLink(idx='0'):
    global tracker
    tracker = trackers[int(idx)]
    if fitbit.connect(tracker):
        print('Ok')
    else:
        tracker = None

def needtracker(fn):
    def wrapped(*args):
        if tracker is None:
            print("No tracker, establish a Link (l) first")
            return
        return fn(*args)
    return wrapped

@command('C', "disconnect to the connected tracker")
@needtracker
def disconnect():
    if not fitbit.disconnect(tracker):
        print('Bad')
    else:
        print('Ok')

@command('tx', "toggle Tx Pipe")
@needfitbit
def toggleTxPipe(on):
    if fitbit.toggleTxPipe(bool(int(on))):
        print('Ok')

@command('D', 'getDump')
@needfitbit
def getDump(type="13"):
    fitbit.getDump(int(type))

@command('R', 'uploadResponse')
@needfitbit
def uploadResponse(*response):
    response = x2a(' '.join(response))
    fitbit.uploadResponse(response)
