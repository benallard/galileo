"""\
The conversationnal part between the server and the client ...
"""

import logging
logger = logging.getLogger(__name__)

from .dongle import FitBitDongle
from .net import GalileoClient
from .tracker import FitbitClient


class Conversation(object):
    def __init__(self, mode, ui):
        self.mode = mode
        self.ui = ui

    def __call__(self, config):
        dongle = FitBitDongle()
        if not dongle.setup():
            logger.error("No dongle connected, aborting")
            return

        fitbit = FitbitClient(dongle)

        galileo = GalileoClient('https', 'client.fitbit.com',
                                'tracker/client/message')

        fitbit.disconnect()

        if not fitbit.getDongleInfo():
            logger.warning('Failed to get connected Fitbit dongle information')

        action = ''
        uiresp = []

        while True:
            answ = galileo.post(self.mode, dongle, ('ui-response', {'action': action}, uiresp))
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
            if trackers:
                # First: Do what is asked
                pass
            if commands:
                # Prepare an answer for the server
                pass
            if action:
                # Get an answer from the ui
                uiresp = self.ui.request(action, html)
