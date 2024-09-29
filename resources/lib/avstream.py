"""
    module containing classes to maintain stream state
"""
import typing
from enum import IntEnum
from collections import namedtuple
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode, unquote

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
            del stream


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
        xbmc.log('AVSTREAM CREATED {0}'.format(token), xbmc.LOGDEBUG)
        self.origHostname = None
        self.origPath = None
        self.redirectedUrl = None
        self.baseUrl = None
        self.proxyUrl = None
        self.addon = xbmcaddon.Addon()
        self.loginsession = loginsession
        self.helper = ProxyHelper(self.addon)
        self.state = self.AVStreamStatus.DEFINED
        self.token = token
        self.latestToken = token
        self.tokenTimer = Timer(60, self.__update_token)
        self.tokenTimer.start()

    def __del__(self):
        xbmc.log('AVSTREAM DELETE {0}'.format(self.token))
        if self.tokenTimer is not None:
            self.tokenTimer.stop()

    def stop(self):
        """
        Function to stop streaming. It will stop the timer to refresh the token and delete the token
        @return:
        """
        xbmc.log('AVSTREAM STOP {0}'.format(self.token), xbmc.LOGDEBUG)
        self.state = self.AVStreamStatus.STOPPED
        if self.tokenTimer is None:
            return
        self.tokenTimer.stop()
        try:
            self.loginsession.delete_token(streamingId=self.latestToken)
            xbmc.log('AVSTREAM TOKEN DELETED {0}'.format(self.token), xbmc.LOGDEBUG)
        except WebException as webExc:
            xbmc.log('Could not delete token. {0}'.format(webExc), xbmc.LOGERROR)
            xbmc.log('Response from server: status {0} content: {1}'.format(webExc.status, webExc.response),
                     xbmc.LOGERROR)

    def __update_token(self):
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

    @staticmethod
    def __insert_token(url, streamingToken: str):
        if '/dash' in url:
            return url.replace("/dash", "/dash,vxttoken=" + streamingToken)
        if '/sdash' in url:
            return url.replace("/sdash", "/sdash,vxttoken=" + streamingToken)
        if '/live' in url:
            return url.replace("/live", "/live,vxttoken=" + streamingToken)
        xbmc.log('token not inserted in url: {0}'.format(url))
        return url

    def update_redirection(self, proxyUrl: str, actualUrl: str, baseURL: str = None):
        """
        Results in setting:
            self.redirected_url to be used for manifests
            self.base_url to be used for video/audio requests

        @param proxyUrl:  URL send to the proxy
        @param actualUrl: URL after redirection
        @param baseURL: extracted from the manifest.mpd file
        @return:
        """
        if self.proxyUrl != proxyUrl:
            self.proxyUrl = proxyUrl
            self.baseUrl = None

        s = actualUrl.find(',vxttoken=')
        e = actualUrl.find('/', s)
        actualUrl = actualUrl[0:s] + actualUrl[e:]

        o = urlparse(actualUrl)
        if baseURL is not None:
            if baseURL.startswith('../'):  # it is a baseURL which strips some levels of the original url
                levels = o.path.split('/')
                levels.pop(len(levels) - 1)  # Always remove last level, because it contains a filename (manifest.mpd)
                cntToRemove = baseURL.count('../')
                for _ in range(cntToRemove):
                    levels.pop(len(levels) - 1)
                # Reconstruct the actual_url to be used as baseUrl
                path = '/'.join(levels)
                Components = namedtuple(
                    typename='Components',
                    field_names=['scheme', 'netloc', 'path', 'url', 'query', 'fragment']
                )
                updatedUrl = urlunparse(
                    Components(
                        scheme=o.scheme,
                        netloc=o.netloc,
                        path=path + '/',
                        url='',
                        query='',
                        fragment=''
                    )
                )
                self.baseUrl = updatedUrl
            else:
                self.baseUrl = baseURL
        else:
            self.baseUrl = actualUrl

        self.redirectedUrl = actualUrl

    def get_manifest_url(self, proxyUrl: str):
        """
        Function to create the manifest URL to the real host

        :param proxyUrl: URL received by the proxy to obtain the manifest
        :return: URL to the real host to be used to obtain the manifest
        """
        parsedUrl = urlparse(proxyUrl)
        origParams = parse_qs(parsedUrl.query)
        if self.proxyUrl is None:
            self.proxyUrl = proxyUrl
            self.origPath = unquote(origParams['path'][0])
            self.origHostname = unquote(origParams['hostname'][0])
            initialToken = unquote(origParams['token'][0])
            if initialToken != self.token:
                xbmc.log('token in manifest request not identical to initial token !!!', xbmc.LOGERROR)
            self.redirectedUrl = None

        if self.redirectedUrl is not None:
            #  We can simply use the redirected URL, because it remains unchanged
            return self.__insert_token(self.redirectedUrl, self.latestToken)
        Components = namedtuple(
            typename='Components',
            field_names=['scheme', 'netloc', 'path', 'url', 'query', 'fragment']
        )
        queryParams = {}
        skipParams = ['hostname', 'path', 'token']
        for param, value in origParams.items():
            if param not in skipParams:
                queryParams.update({param: value[0]})

        url = urlunparse(
            Components(
                scheme='https',
                netloc=self.origHostname,
                query=urlencode(queryParams),
                path=self.origPath,
                url='',
                fragment=''
            )
        )
        return self.__insert_token(url, self.latestToken)

    def replace_baseurl(self, url, streamingToken):
        """
        The url is updated with the name of the redirected host, if a token is still present, it will be
        removed.
        @param url:
        @param streamingToken:
        @return:
        """
        o = urlparse(url)
        redir = urlparse(self.baseUrl)
        actualPath = redir.path
        s = actualPath.find(',vxttoken=')
        e = actualPath.find('/', s)
        if s > 0 and e > 0:
            actualPath = actualPath[0:s] + actualPath[e:]
        pathDir = actualPath.rsplit('/', 1)[0]
        hostAndPath = redir.hostname + pathDir + o.path
        return redir.scheme + '://' + self.__insert_token(hostAndPath, streamingToken)


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
        xbmc.log('AVSTREAMLIST SIZE is now {0}'.format(len(self.streams)), xbmc.LOGDEBUG)
        del stream
