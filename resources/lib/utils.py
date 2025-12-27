"""
module with utility functions
"""
import sys
import binascii
import inspect
import traceback
from datetime import datetime
from enum import IntEnum
import threading
import time
from typing import Any
import json
import pickle
import uuid
import requests

import xbmc
import xbmcaddon
import xbmcgui
from requests import Response


def hexlify(barr):
    """
    get a hex string from a byte array
    @param barr:
    @return:
    """
    binascii.hexlify(bytearray(barr))


def ah2b(s):
    """
    get a byte array from a hex-string
    @param s:
    @return:
    """
    return bytes.fromhex(s)


def b2ah(barr):
    """
    get a hex-string from a byte array
    @param barr:
    @return:
    """
    return barr.hex()


def atoh(barr):
    """
    get a hex-string from an ascii-string
    @param barr:
    @return:
    """
    return "".join("{:02x}".format(ord(c)) for c in barr)


class ServiceStatus(IntEnum):
    """
    Enum for the service status
    """
    STARTING = 1
    STOPPING = 2
    STARTED = 3
    STOPPED = 4


class SharedProperties:
    """
    class to share properties between service and addon/scripts
    """
    TEXTID_ASCENDING=21430
    TEXTID_DESCENDING=21431
    TEXTID_NAME=551
    TEXTID_NUMBER=549
    TEXTID_DATE=552
    TEXTID_SIZE=553

    def __init__(self, addon: xbmcaddon.Addon):
        self.addon: xbmcaddon.Addon = addon
        self.window: xbmcgui.Window = xbmcgui.Window(10000)
        self.kodiVersion = xbmc.getInfoLabel('System.BuildVersionShort')
        if self.kodiVersion == '':
            self.kodiVersion = '21.0'
        digits = self.kodiVersion.split('.')
        self.kodiVersionMajor = digits[0]
        if (digits[1].isnumeric()):
            self.kodiVersionMinor = digits[1]
        else:
            self.kodiVersionMinor = digits[1].split('-')[0]

    def set_service_status(self, status: ServiceStatus):
        """set the service status"""
        self.window.setProperty(self.addon.getAddonInfo('id') + 'ServiceStatus', str(status.value))

    def is_service_active(self) -> bool:
        """check if service is active"""
        return self.window.getProperty(
            self.addon.getAddonInfo('id') + 'ServiceStatus') == str(ServiceStatus.STARTED.value)

    def set_uuid(self):
        """generate a unique uuid for the device"""
        hexNode = hex(uuid.getnode())
        hexNodeNoPrefix = hexNode[2:]
        hexNodeFull = hexNodeNoPrefix.zfill(12) * 2 + '00000000'
        self.window.setProperty(self.addon.getAddonInfo('id') + 'UUID',
                                str(uuid.UUID(hex=hexNodeFull)))

    def get_uuid(self):
        """get the uuid"""
        return self.window.getProperty(self.addon.getAddonInfo('id') + 'UUID')

    def get_kodi_version_major(self) -> int:
        """return the major version number of Kodi"""
        return int(self.kodiVersionMajor)

    def get_kodi_version_minor(self) -> int:
        """return the minor version number of Kodi"""
        return int(self.kodiVersionMinor)
    
    def get_sort_options(self):
        """get the current sort options from kodi"""
        sortby = self.window.getProperty('ziggotv.SortMethod')
        sortorder = self.window.getProperty('ziggotv.SortOrder')
        return sortby, sortorder

    def set_sort_options(self, sortby: str=None, sortorder: str=None):
        """set the sort options in kodi"""
        if sortby is not None:
            self.window.setProperty('ziggotv.SortMethod', sortby)
        if sortorder is not None:
            self.window.setProperty('ziggotv.SortOrder', sortorder)

class Timer(threading.Thread):
    """
    timer class
    """

    def __init__(self, interval, callback_function=None):
        self.timerRuns = threading.Event()
        self.timerRuns.set()
        self.interval = interval
        self.callbackFunction = callback_function
        super().__init__()

    def run(self):
        expiredSecs = 0
        while self.timerRuns.is_set():
            time.sleep(1)
            expiredSecs += 1
            if expiredSecs >= self.interval:
                self.timer()
                expiredSecs = 0

    def stop(self):
        """stop the timer"""
        self.timerRuns.clear()
        self.join()

    def timer(self):
        """calls the callback function"""
        self.callbackFunction()


class DatetimeHelper:
    """
    class with some helper functions for datetime handling
    """

    @staticmethod
    def from_unix(unixTime: int, tz: datetime.tzinfo = None) -> datetime:
        """
        Creates datetime from unixtime. There are two formats of unixtime in seconds or milliseconds.
        The function attempts to figure out which one it received in unixTime.
        @param unixTime: unix time in seconds or milliseconds
        @param tz: optional timezone to add to datetime
        @return:
        """
        dateTimeMax = datetime(2035, 12, 31, 0, 0)
        maxUnixTimeInSecs = time.mktime(dateTimeMax.timetuple())
        if unixTime > maxUnixTimeInSecs:
            return datetime.fromtimestamp(unixTime / 1000, tz)
        return datetime.fromtimestamp(unixTime, tz)

    @staticmethod
    def now(tz: datetime.tzinfo = None) -> datetime:
        """
        current datetime with timezone
        @param tz: optional timezone
        @return:
        """
        return datetime.now(tz)

    @staticmethod
    def to_unix(dt: str, dtFormat: str):
        """
        converts datetime string (dt) with format dtFormat to unix time in seconds
        @param dt:
        @param dtFormat: format of the datetime in dt. See strptime.
        @return:
        """
        return int(time.mktime(datetime.strptime(dt, dtFormat).timetuple()))

    @staticmethod
    def unix_datetime(dt: datetime):
        """
        create a unix timestamp in seconds from a datetime
        @param dt:
        @return:
        """
        return int(time.mktime(dt.timetuple()))


class WebException(Exception):
    """
    Exception used when web-calls fail. Carries status code, response and calling function where error occurs
    """

    def __init__(self, response: Response):
        funcName = inspect.stack()[1].function
        message = 'Unexpected response status in {0}: {1}'.format(funcName, response.status_code)
        super().__init__(message)
        self._response = response

    @property
    def response(self):
        """
        get the response content received via a requests call
        @return:
        """
        return self._response.content

    @property
    def status(self):
        """
        gets the status-code of the requests call
        @return:
        """
        return self._response.status_code


class ProxyHelper:
    """
    class with functions to call function of LoginSession via the http-proxy
    """

    # pylint: disable=too-few-public-methods
    def __init__(self, addon: xbmcaddon.Addon):
        self.port = addon.getSetting('proxy-port')
        self.ip = addon.getSetting('proxy-ip')
        self.host = 'http://{0}:{1}/'.format(self.ip, self.port)
        self.dataTimeout = addon.getSettingNumber('data-timeout')

    def dynamic_call(self, method, **kwargs) -> Any:
        """
        Helper function to call a function in the service which is running.
        If successful, the response will be the response from the called function.
        On failure, a WebException will be raised, which contains the response from
        the server.

        method: the function to be called e.g. LoginSession.login
        kwargs: the named arguments of the function to be called.

        example: helper.dynamicCall(LoginSession.login,username='a',password='b'
        """
        try:
            if kwargs is None:
                arguments = {}
            else:
                arguments = kwargs
            response = requests.get(
                url=self.host + 'function/{method}'.format(method=method.__qualname__),
                params={'args': json.dumps(arguments)},
                timeout=self.dataTimeout)
            if response.status_code != 200:
                raise WebException(response)
            contentType = response.headers.get('content-type')
            if contentType == 'text/html':
                return response.content
            if contentType == 'application/octet-stream':
                result = pickle.loads(response.content)
                return result
            return None
        except WebException as exc:
            raise exc
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            xbmc.log('Exception during dynamic call: {0} {1}'.format(method, exc), xbmc.LOGERROR)
            xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
            raise exc


class KodiLock:
    """
    Note: we are using the [2] entry from the stack, because we always use 'with'
        if [1] is used one would always see __enter or __exit
    """
    def __init__(self):
        self._lock = threading.Lock()

    def acquire(self):
        """
        Function called to acquire lock
        @return:
        """
        # xbmc.log('KODILOCK acquire {0}'.format(inspect.stack()[2].function), xbmc.LOGDEBUG)
        # traceback.print_tb
        # pylint: disable=consider-using-with
        self._lock.acquire()
        # xbmc.log('KODILOCK acquired {0}'.format(inspect.stack()[2].function), xbmc.LOGDEBUG)

    def release(self):
        """
        Function called to release lock
        @return:
        """
        # xbmc.log('KODILOCK release {0}'.format(inspect.stack()[2].function), xbmc.LOGDEBUG)
        # traceback.print_tb
        self._lock.release()
        # xbmc.log('KODILOCK released {0}'.format(inspect.stack()[2].function), xbmc.LOGDEBUG)

    def __enter__(self):
        self.acquire()

    def __exit__(self, _type, value, _traceback):
        self.release()

def invoke_debugger(enable_debug: bool, debug_type:str):
    """
        debug_type: one of 'vscode', 'eclipse', 'web'
    """
    if enable_debug:
        try:
            if debug_type == 'eclipse':
                try:
                    # sys.path.append('E:\Eclipse IDE\eclipse\plugins\org.python.pydev.core_10.2.1.202307021217\pysrc')
                    # or add pydevd as a dependency (update addon.xml and install the script.module.pydevd)
                    import pydevd
                    pydevd.settrace('localhost', stdoutToServer=True, stderrToServer=True)
                except:
                    sys.stderr.write("Error: " + "You must add org.python.pydev.debug.pysrc to your PYTHONPATH")
                    sys.stderr.write("Error: " + "Debug not available")
            elif debug_type == 'vscode': # debugpy
                try:
                    # add debugpy as a dependency (update addon.xml and install the plugin.script.debugpy)
                    import debugpy
                    # 5678 is the default attach port in the VS Code debug configurations. Unless a host and port are specified, host defaults to 127.0.0.1
                    if not debugpy.is_client_connected():
                        debugpy.connect(('localhost', 5678))
                    debugpy.breakpoint()
                except:
                    sys.stderr.write("Error: " + "You must add debugpy to your PYTHONPATH or install the addon script.module.debugpy")
                    sys.stderr.write("Error: " + "Debug not available")
            elif debug_type == 'web':
                import web_pdb # type: ignore
                web_pdb.set_trace()
        except Exception as exc:
            xbmc.log('Could not connect to debugger: {0}'.format(exc), xbmc.LOGERROR)
    return

def check_service(addon: xbmcaddon.Addon):
    """
    Function to check if the Ziggo service is running
    @return:
    """
    home: SharedProperties = SharedProperties(addon=addon)
    if home.is_service_active():
        return
    secondsToWait = 30
    timeWaiting = 0
    interval = 0.5
    dlg = xbmcgui.DialogProgress()
    dlg.create('ZiggoTV', 'Waiting for service to start...')
    while (not home.is_service_active() and
           timeWaiting < secondsToWait and not home.is_service_active() and not dlg.iscanceled()):
        xbmc.sleep(int(interval * 1000))
        timeWaiting += interval
        dlg.update(int(timeWaiting / secondsToWait * 100), 'Waiting for service to start...')
    dlg.close()
    if not home.is_service_active():
        raise RuntimeError('Service did not start in time')

if __name__ == '__main__':
    pass
