"""\
The conversationnal part between the server and the client ...
"""

import uuid

import logging
logger = logging.getLogger(__name__)

from .dongle import FitBitDongle
from .net import GalileoClient
from .tracker import FitbitClient
from .utils import a2x


FitBitUUID = uuid.UUID('{ADAB0000-6E7D-4601-BDA2-BFFAA68956BA}')


class Conversation(object):
    def __init__(self, mode, ui):
        self.mode = mode
        self.ui = ui

    def __call__(self, config):
        self.dongle = FitBitDongle(config.logSize)
        if not self.dongle.setup():
            logger.error("No dongle connected, aborting")
            return

        self.fitbit = FitbitClient(self.dongle)

        self.galileo = GalileoClient('https', 'client.fitbit.com',
                                'tracker/client/message')

        self.fitbit.disconnect()

        if not self.fitbit.getDongleInfo():
            logger.warning('Failed to get connected Fitbit dongle information')

        action = ''
        uiresp = []
        resp = [('ui-response', {'action': action}, uiresp)]

        while True:
            answ = self.galileo.post(self.mode, self.dongle, resp)
            print answ
            html = ''
            commands = None
            trackers = None
            for tple in answ:
                tag, attribs, childs, _ = tple
                if tag == "ui-request":
                    action = attribs['action']
                    for child in childs:
                        tag, attribs, _, body = child
                        if tag == "client-display":
                            if attribs.get('containsForm', False):
                                html = body
                elif tag == 'tracker':
                    trackers.append()
                elif tag == 'commands':
                    commands = childs
            resp = []
            if trackers:
                # First: Do what is asked
                for tracker in trackers:
                    self.do_tracker(tracker)
            if commands:
                # Prepare an answer for the server
                res = []
                for command in commands:
                    r = self.do_command(command)
                    print r
                    if r is not None:
                        res.append(r)
                resp.append(('command-response', {}, res))
            if action:
                # Get an answer from the ui
                resp.append(('ui-response', {'action': action}, self.ui.request(action, html)))

    #-------- The commands

    def do_command(self, cmd):
        tag, elems, childs, body = cmd
        f = {'pair-to-tracker': self._pair,
            'connect-to-tracker': self._connect,
            'list-trackers': self._list,
            'ack-tracker-data': self._ack}[tag]
        return f(*childs, **elems)

    def _pair(self, **params):
        """ :returns: nothing
        """
        displayCode = bool(params['displayCode'])
        waitForUserInput = bool(params['waitForUserInput'])
        trackerId = params['tracker-id']

    def _connect(self, **params):
        """ :returns: nothing
        """
        trackerId = params['tracker-id']
        if 'connection' in params:
            connection = params['connection'] == 'disconnect'
        elif 'response-data' in params:
            responseData = params['response-data']
        else:
            raise ValueError(params)

    def _list(self, *childs, **params):
        immediateRsi = int(params['immediateRsi'])
        minDuration = int(params['minDuration'])
        maxDuration = int(params['maxDuration'])

        res = []
        for tracker in self.fitbit.discover(FitBitUUID, minRSSI=immediateRsi,
                                             minDuration=minDuration):
            res.append(('available-tracker', {},
                        [('tracker-id', {}, [], a2x(tracker.id, delim="")), ('tracker-attributes', {}, [], a2x(tracker.attributes, delim="")), ('rsi', {} , [], str(tracker.RSSI))]))
        return ('list-trackers', {}, res)

    def _ack(self, **params):
        trackerId = params['tracker-id']


    # ------

    def do_tracker(self, tracker):
        pass
