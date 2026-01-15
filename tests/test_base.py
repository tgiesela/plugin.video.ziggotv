# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
import unittest
import os
import json
import threading
from time import sleep

import xbmcaddon

from resources.lib.globals import G
from resources.lib.servicemonitor import HttpProxyService
from resources.lib.webcalls import LoginSession


class Addon(xbmcaddon.Addon):
    """
        Class to support use of setting/getting the addon settings
        Very primitive.
    """

    def __init__(self, name):
        super().__init__(name)
        self.settings = {}

    # pylint: disable=redefined-builtin
    def setSetting(self, id: str, value: str) -> None:
        self.settings.update({id: value})

    def setSettingNumber(self, id: str, value: float) -> None:
        self.settings.update({id: value})

    def setSettingBool(self, id: str, value: bool) -> None:
        self.settings.update({id: value})

    def getSetting(self, id: str) -> str:
        return self.settings[id]

    def getSettingBool(self, id: str) -> bool:
        return bool(self.settings[id])

    def getSettingInt(self, id: str) -> int:
        return int(self.settings[id])

    def getSettingNumber(self, id: str) -> float:
        return float(self.settings[id])
    # pylint: enable=redefined-builtin


class TestBase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.addon = Addon('plugin.video.ziggotv')
        self.addon.setSettingBool('print-network-traffic', False)
        self.addon.setSetting('proxy-ip', '127.0.0.1')
        self.addon.setSetting('proxy-port', '6868')
        self.addon.setSettingBool('use-proxy', True)
        self.addon.setSettingBool('full-hd', True)
        self.addon.setSettingBool('print-response-content', False)
        self.addon.setSettingBool('print-request-content', False)
        self.addon.setSettingNumber('connection-timeout', 10)
        self.addon.setSettingNumber('data-timeout', 10)
        self.cleanup_all()
        self.session = LoginSession(self.addon)
        self.session.printNetworkTraffic = False
        self.svc = HttpProxyService(threading.Lock(), self.addon)
        self.svc.set_address((self.addon.getSetting('proxy-ip'), self.addon.getSettingInt('proxy-port')))
        sleep(1)

    def setUp(self):
        self.session = LoginSession(self.addon)
        self.svc.start_http_server()
        print("Executing setup",  self._testMethodName)

    def tearDown(self):
        print("Executing teardown", self._testMethodName)
        self.session.close()
        sleep(1)
        self.svc.stop_http_server()
        self.cleanup_all()

    @staticmethod
    def remove(file):
        if os.path.exists(file):
            os.remove(file)

    def cleanup_cookies(self):
        self.remove(G.COOKIES_INFO)

    def cleanup_channels(self):
        self.remove(G.CHANNEL_INFO)

    def cleanup_customer(self):
        self.remove(G.CUSTOMER_INFO)

    def cleanup_session(self):
        self.remove(G.SESSION_INFO)

    def cleanup_entitlements(self):
        self.remove(G.ENTITLEMENTS_INFO)

    def cleanup_widevine(self):
        self.remove(G.WIDEVINE_LICENSE)

    def cleanup_epg(self):
        self.remove(G.GUIDE_INFO)

    def cleanup_recordings(self):
        self.remove(G.RECORDINGS_INFO)

    def cleanup_playbackstates(self):
        self.remove(G.PLAYBACK_INFO)

    def cleanup_savechannelstates(self):
        self.remove(G.RECENTCHANNELS_INFO)

    def cleanup_all(self):
        self.cleanup_customer()
        self.cleanup_session()
        self.cleanup_channels()
        self.cleanup_cookies()
        self.cleanup_entitlements()
        self.cleanup_widevine()
        self.cleanup_epg()
        self.cleanup_recordings()
        self.cleanup_playbackstates()
        self.cleanup_savechannelstates()

    def do_login(self):
        with open('c:/temp/credentials.json', 'r', encoding='utf-8') as credfile:
            credentials = json.loads(credfile.read())
        self.session.login(credentials['username'], credentials['password'])
        self.assertFalse(len(self.session.customerInfo) == 0)
        # self.session.obtain_customer_info()
