"""
    module containing classes to maintain stream state
"""
import typing
from enum import IntEnum

import xbmc
import xbmcaddon

from resources.lib.utils import Timer, WebException, ProxyHelper
from resources.lib.webcalls import LoginSession


class StreamSession:
    """
    Class implementing functions needed for adding and deleting streams
    """
    def __init__(self, loginSession: LoginSession):
        """
        Initializer for StreamSession. It uses LoginSession to create AvStream objects
        @param loginSession: Reference to a LoginSession which is already signed in
        """
        self.streamList: AVStreamList = AVStreamList()
        self.loginSession = loginSession

    def start_stream(self, token: str):
        """
        Function to start/register a stream
        @param token: the stream-token for the stream on startup
        @return: None
        """
        stream = AvStream(self.loginSession, token)
        self.streamList.add_stream(stream)

    def find_stream(self, token):
        """
        Function to locate a stream
        @param token: the stream-token for the stream on startup
        @return: stream or none
        """
        stream: AvStream
        for stream in self.streamList:
            if stream.token == token:
                return stream
        return None

    def stop_stream(self, token: str):
        """
        Function to end playing stream
        @param token: the stream-token for the stream in startup
        @return:
        """
        stream = self.find_stream(token)
        if stream is not None:
            stream.stop()
            self.streamList.stop_stream(stream)


class AvStream:
    """
        Class to hold information for current playing channel or video
    """

    class AVStreamStatus(IntEnum):
        """
        Enum for the ACstream status
        """
        DEFINED = 1
        PLAYING = 2
        STOPPED = 3

    def __init__(self, loginsession: LoginSession, token: str):
        self.addon = xbmcaddon.Addon()
        self.loginsession = loginsession
        self.helper = ProxyHelper(self.addon)
        self.state = self.AVStreamStatus.DEFINED
        self.token = token
        self.latestToken = token
        self.tokenTimer = Timer(60, self.update_token)
        self.tokenTimer.start()

    def __del__(self):
        if self.tokenTimer is not None:
            self.tokenTimer.stop()

    def stop(self):
        """
        Function to stop streaming. It will stop the timer to refresh the token and delete the token
        @return:
        """
        self.state = self.AVStreamStatus.STOPPED
        if self.tokenTimer is None:
            return
        self.tokenTimer.stop()
        try:
            self.loginsession.delete_token(streamingId=self.latestToken)
        except WebException as webExc:
            xbmc.log('Could not delete token. {0}'.format(webExc), xbmc.LOGERROR)
            xbmc.log('Response from server: status {0} content: {1}'.format(webExc.status, webExc.response),
                     xbmc.LOGERROR)

    def update_token(self):
        """
        function to update the streaming token. The token has to be updated periodically
        @return:
        """
        xbmc.log("Refresh token interval expired", xbmc.LOGDEBUG)
        try:
            self.latestToken = self.loginsession.update_token(streamingToken=self.latestToken)
        except WebException as webExc:
            xbmc.log('Could not update token. {0}'.format(webExc), xbmc.LOGERROR)
            xbmc.log('Response from server: status {0} content: {1}'.format(webExc.status, webExc.response),
                     xbmc.LOGERROR)


class AVStreamList:
    """
    Class to maintain a list of currently playing or stopping streams
    """
    def __init__(self):
        self.inx = 0
        self.streams: typing.List[AvStream] = []

    def __iter__(self):
        self.inx = 0
        return self

    def __next__(self):
        if self.inx < len(self.streams):
            s = self.streams[self.inx]
            self.inx += 1
            return s
        raise StopIteration

    def add_stream(self, stream: AvStream):
        """
        Function to register a stream
        @param stream: the stream to add (AvStream)
        @return:
        """
        self.streams.append(stream)
        xbmc.log('AVSTREAMLIST SIZE is now {0}'.format(len(self.streams)), xbmc.LOGDEBUG)

    def stop_stream(self, stream: AvStream):
        """
        Function to deregister the stream
        @param stream: the stream to remove (AvStream)
        @return:
        """
        self.streams.remove(stream)
