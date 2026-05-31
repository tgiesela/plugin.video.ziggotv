#pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
import threading
import os
import json
from time import sleep

import pytest

import xbmcaddon
from resources.lib.globals import G
from resources.lib.proxyserver import ProxyServer
from resources.lib.servicemonitor import HttpProxyService
from resources.lib.utils import ProxyHelper
from resources.lib.webcalls import LoginSession
from tests_pytest.xbmcclasses import Addon

@pytest.fixture(scope="session",name="addon")
def fixture_addon():
    addon = Addon('plugin.video.ziggotv')
    addon.setSettingBool('print-network-traffic', True)
    addon.setSetting('proxy-ip', '127.0.0.1')
    addon.setSetting('proxy-port', '6868')
    addon.setSettingBool('full-hd', True)
    addon.setSettingBool('print-response-content', True)
    addon.setSettingBool('print-request-content', True)
    addon.setSettingNumber('connection-timeout', 100)
    addon.setSettingNumber('data-timeout', 100)
    addon.setSettingBool('adult-allowed', True)
    return addon

class Session:
    def __init__(self, addon):
        super().__init__()
        self.helper = ProxyHelper(addon)

    @staticmethod
    def remove(file):
        if os.path.exists(file):
            os.remove(file)

    def cleanup_cookies(self):
        self.remove(G.COOKIES_INFO)

    def cleanup_channels(self):
        self.remove(G.CHANNEL_INFO)

    def cleanup_movies(self):
        self.remove(G.MOVIE_INFO)

    def cleanup_series(self):
        self.remove(G.SERIES_INFO)

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
        self.cleanup_movies()
        self.cleanup_series()
        self.cleanup_entitlements()
        self.cleanup_widevine()
        self.cleanup_epg()
        self.cleanup_recordings()
        self.cleanup_playbackstates()
        self.cleanup_savechannelstates()

class LocalSession(Session):
    def __init__(self, addon):
        super().__init__(addon)
        self.addon = addon
        print("Creating LocalSession")
        self.session = LoginSession(addon)
        self.session.printNetworkTraffic = False

        self.svc = HttpProxyService(threading.Lock(), addon)
        self.svc.set_address((addon.getSetting('proxy-ip'), self.addon.getSettingInt('proxy-port')))
        self.proxyServer: ProxyServer = None
        self.helper = ProxyHelper(addon)

    def do_login(self):
        with open(os.path.expanduser('~/credentials.json'), 'r', encoding='utf-8') as credfile:
            credentials = json.loads(credfile.read())
        self.session.login(credentials['username'], credentials['password'])
        assert len(self.session.customerInfo) != 0
        self.session.refresh_entitlements()

    def start_proxy_server(self):
        # Note the proxy will always be in logged-in state.
        print("Starting proxy server")
        self.svc.start_http_server()
        self.svc.proxyServer.session.printNetworkTraffic = self.session.printNetworkTraffic
        with open(os.path.expanduser('~/credentials.json'), 'r', encoding='utf-8') as credfile:
            credentials = json.loads(credfile.read())
        _ = self.helper.dynamic_call(LoginSession.login, username=credentials['username'],
                                     password=credentials['password'])
        entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)
        if entitlements == {}:
            self.helper.dynamic_call(LoginSession.refresh_entitlements)
        sleep(1)
        print("Proxy server started and logged in")
        
    def stop_proxy_server(self):
        print("Stopping proxy server")
        self.svc.stop_http_server()
        sleep(1) # Give the server some time to stop
        print("Proxy server stopped")

# This fixture is used to create a session that can be used for testing.
# It will be used by the other fixtures to create a session that is logged in or not logged in.
# It will remain active for the entire module, so it will be created once and used for all
# tests in the module.
@pytest.fixture(name="websession",scope="module")
def fixture_websession(addon) -> LocalSession:
    return LocalSession(addon)

@pytest.fixture
def activewebsession(websession) -> LocalSession:
    websession.do_login()
    return websession

@pytest.fixture
def inactivewebsession(websession) -> LocalSession:
    return websession

@pytest.fixture(autouse=True, scope="function")
#pylint: disable=unused-argument
def run_around_tests(websession):
    print("\nThis will run before the test function")
    yield
    print("\nThis will run after the test function")

@pytest.fixture(autouse=True, scope="class")
def run_around_testclass(websession):
    print("\nThis will run before the test class")
    websession.start_proxy_server()
    yield
    print("\nThis will run after the test class")
    websession.stop_proxy_server()
    websession.cleanup_all()
