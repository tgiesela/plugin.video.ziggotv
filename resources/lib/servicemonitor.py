"""
module containing the service monitor to track all ongoing tasks of the plugin
"""
import datetime
import http.server
import json
import os
import shutil
import threading
from pathlib import Path

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

from resources.lib.channel import SavedChannelsList
from resources.lib.proxyserver import ProxyServer
from resources.lib.recording import SavedStateList
from resources.lib.utils import Timer, SharedProperties, ServiceStatus, ProxyHelper, WebException, KodiLock, ZiggoKeyMap
from resources.lib.webcalls import LoginSession


# pylint: disable=too-many-instance-attributes
class HttpProxyService:
    """
    class for maintaining state of the proxy-server
    """
    PROFILE_FOLDER = xbmcvfs.translatePath(xbmcaddon.Addon().getAddonInfo('profile'))

    def __init__(self, svcLock, addon: xbmcaddon.Addon):
        self.lock = svcLock
        self.addon = addon
        self.address = ''
        self.port = 80
        self.isShutDown = True
        self.httpServerThread = None
        self.proxyServer: http.server.HTTPServer = None  # started by me
        self.settingsChangeLock = threading.Lock()
        xbmc.log("Proxy service initialized", xbmc.LOGDEBUG)

    def set_address(self, addressAndPort):
        """
        funtion to set ip address and port
        :param addressAndPort: tuple containing address:str and port:int
        :return:
        """
        with self.lock:
            self.address, self.port = addressAndPort

    def restart_http_server(self):
        """restart the http server (not used)"""
        with self.settingsChangeLock:
            self.stop_http_server()
            self.start_http_server()

    def start_http_server(self):
        """start the http server"""
        self.isShutDown = False
        self.stop_http_server()
        try:
            self.proxyServer = ProxyServer(self.addon, (self.address, self.port), self.lock)
        except IOError:
            pass

        thread = threading.Thread(target=self.proxyServer.serve_forever)
        thread.start()
        self.httpServerThread = thread
        xbmc.log("ProxyService started listening on {0}-{1}".format(self.address,
                                                                    self.port), xbmc.LOGINFO)

    def stop_http_server(self):
        """stop the http server"""
        if self.proxyServer is not None:
            self.proxyServer.shutdown()
            xbmc.log("PROXY SERVER STOPPPED", xbmc.LOGDEBUG)
        if self.httpServerThread is not None:
            self.httpServerThread.join()
            self.httpServerThread = None
            xbmc.log("HTTP SERVER THREAD STOPPPED", xbmc.LOGDEBUG)
        self.isShutDown = True

    def clear_browser_lock(self):
        """Clears the pidfile in case the last shutdown was not clean"""
        browserLockPath = os.path.join(self.PROFILE_FOLDER, 'browser.pid')
        try:
            os.remove(browserLockPath)
        except OSError:
            pass


class ServiceMonitor(xbmc.Monitor):
    # pylint: disable=too-many-instance-attributes
    """
        Servicemonitor keeps data up to date.
        Starts the HTTP Proxy which is the central process to maintain session data.
        All methods of LoginSession are called via the dynamic procedure calls.

    """
    ADDON = xbmcaddon.Addon()

    def __init__(self):
        super().__init__()
        #self.lock = threading.Lock()
        self.lock = KodiLock()

        #  Start the HTTP Proxy server
        port = self.ADDON.getSettingNumber('proxy-port')
        ip = self.ADDON.getSetting('proxy-ip')
        self.proxyService = HttpProxyService(self.lock, self.ADDON)
        self.proxyService.set_address((ip, int(port)))
        self.proxyService.start_http_server()

        #  Set the status of this service to STARTING
        self.home = SharedProperties(addon=self.ADDON)
        self.home.set_uuid()
        self.home.set_service_status(ServiceStatus.STARTING)

        xbmc.log('Detected KODI-version {0}.{1}'.format(self.home.get_kodi_version_major(),
                                                        self.home.get_kodi_version_minor()),
                 xbmc.LOGINFO)

        self.helper = ProxyHelper(self.ADDON)
        self.tokenTimer = None
        self.refreshTimer = None
        self.licenseRefreshed = datetime.datetime.now() - datetime.timedelta(days=2)
        self.savedItemsUpdated = datetime.datetime.now() - datetime.timedelta(days=1)
        self.__initialize_session()

        #  Set the status of this service to STARTED
        self.home.set_service_status(ServiceStatus.STARTED)
        xbmc.log('SERVICEMONITOR initialized: ', xbmc.LOGDEBUG)
        keymap = ZiggoKeyMap(self.ADDON)
        keymap.install()

    def __initialize_session(self):
        addonPath = xbmcvfs.translatePath(self.ADDON.getAddonInfo('profile'))
        Path(addonPath).mkdir(parents=True, exist_ok=True)
        self.__refresh_session()
        self.refreshTimer = Timer(600, self.__refresh_session)
        self.refreshTimer.start()
        self.helper.dynamic_call(LoginSession.close)

    def __refresh_session(self):
        if self.ADDON.getSetting('username') == '':
            xbmcaddon.Addon().openSettings()
        if self.ADDON.getSetting('username') == '':
            xbmcgui.Dialog().ok('Error', 'Login credentials not set, exiting')
            raise RuntimeError('Login credentials not set')
        username = self.ADDON.getSetting('username')
        password = self.ADDON.getSetting('password')

        try:
            sessionInfo = self.helper.dynamic_call(LoginSession.login, username=username, password=password)
            if len(sessionInfo) == 0:
                raise RuntimeError("Login failed, check your credentials")
            # The Widevine license will only be refreshed once per day, because they do not change
            if (self.licenseRefreshed + datetime.timedelta(days=1)) <= datetime.datetime.now():
                self.licenseRefreshed = datetime.datetime.now()
                self.helper.dynamic_call(LoginSession.refresh_widevine_license)

            # Once a day we will cleanup watched channels (keep the most recent 10) and state of recordings
            if (self.savedItemsUpdated + datetime.timedelta(days=1)) <= datetime.datetime.now():
                self.savedItemsUpdated = datetime.datetime.now()
                SavedChannelsList(self.ADDON).cleanup(365,10)
                SavedStateList(self.ADDON).cleanup(365)

            self.helper.dynamic_call(LoginSession.close)
        except ConnectionResetError as exc:
            xbmc.log('Connection reset in __refresh_session, will retry later: {0}'.format(exc), xbmc.LOGERROR)
        except WebException as webExc:
            xbmc.log('WebException in __refresh_session{0}'.format(webExc), xbmc.LOGERROR)
            xbmc.log('Response from server: status {0} content: {1}'.format(webExc.status, webExc.response),
                     xbmc.LOGERROR)
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Unexpected exception in __refresh_session: {0}'.format(exc), xbmc.LOGERROR)

    def onNotification(self, sender: str, method: str, data: str) -> None:
        """
        Function to handle notification from Kodi
        @param sender:
        @param method:
        @param data:
        @return:
        """
        if self.proxyService.proxyServer is None:
            xbmc.log('SERVICEMONITOR ProxyServer not started yet', xbmc.LOGERROR)
            return
        xbmc.log("SERVICEMONITOR Notification: {0},{1},{2}".format(sender, method, data), xbmc.LOGDEBUG)

    def shutdown(self):
        """
        Function to shut down the service
        @return:
        """
#        self.keymap.deactivate()
        self.proxyService.stop_http_server()
        self.home.set_service_status(ServiceStatus.STOPPING)
        if self.tokenTimer is not None:
            self.tokenTimer.stop()
        if self.refreshTimer is not None:
            self.refreshTimer.stop()
        xbmc.log("SERVICE-MONITOR Timers stopped", xbmc.LOGDEBUG)
        self.home.set_service_status(ServiceStatus.STOPPED)
