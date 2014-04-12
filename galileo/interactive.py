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
    while not exit:
        input = raw_input('> ')
        input = input.split(' ')
        try:
            f = cmds[input[0]]
        except KeyError:
            print 'Command %s not known' % input[0]
            print_help()
            continue
        try:
            f(*input[1:])
        except Exception, e:
            # We need that to be able to close the connection nicely
            print "BaD bAd BAd", e
            traceback.print_exc(file=sys.stdout)
            exit = True


#---------------------------
# The commands

from .dongle import FitBitDongle, NoDongleException, CM, DM
from .tracker import FitbitClient
from .utils import x2a

dongle = None
fitbit = None

@command('c', "Connect")
def connect():
    global dongle
    dongle = FitBitDongle()
    try:
        dongle.setup()
    except NoDongleException:
        print "No dongle connected, aborting"
        global exit
        exit = True
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
def receive():
    dongle.ctrl_read()
