import pickle
import traceback
from socket import socket
from urllib.parse import urlparse, parse_qs, unquote

import json
import typing

import socketserver
import http.server

from http.server import BaseHTTPRequestHandler
from http.client import HTTPConnection
from http.client import HTTPSConnection

from xml.dom import minidom
from resources.lib.urltools import UrlTools
from resources.lib.webcalls import LoginSession, WebException
import xbmc
import xbmcaddon


class HTTPRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, request: socket, client_address: typing.Tuple[str, int], server: socketserver.BaseServer):
        super().__init__(request, client_address, server)

    def log_request(self, code='-', size='-'):
        if code == 200:
            pass
        else:
            xbmc.log('HTTPRequestHandler log_request({0},{1})'.format(code, size), xbmc.LOGERROR)

    # pylint: disable=invalid-name
    def do_GET(self):
        """Handle http get requests, used for manifest and all streaming calls"""
        proxy: ProxyServer = self.server
        proxy.handle_get(self)

    def do_POST(self):
        """Handle http post requests, used for license"""
        proxy: ProxyServer = self.server
        proxy.handle_post(self)

    def do_OPTIONS(self):
        proxy: ProxyServer = self.server
        proxy.handle_options(self)

    def do_HEAD(self):
        proxy: ProxyServer = self.server
        proxy.handle_head(self)
    # pylint: enable=invalid-name


class ProxyServer(http.server.HTTPServer):
    """
        Proxyserver for processing license and manifest request.
        Contains some functions to maintain state because HttpRequestHandler is instantiated
        for every new call
    """

    def __init__(self, addon, server_address, lock):
        http.server.HTTPServer.__init__(self, server_address, HTTPRequestHandler)
        self.lock = lock
        self.addon = addon
        self.session = LoginSession(xbmcaddon.Addon())
        self.urlTools = UrlTools(addon)
        xbmc.log("ProxyServer created", xbmc.LOGINFO)

    def set_streaming_token(self, token):
        with self.lock:
            self.session.streamingToken = token
            xbmc.log('Setting streaming token to: {0}'.format(token), xbmc.LOGDEBUG)

    def get_streaming_token(self):
        with self.lock:
            return self.session.streamingToken

    def get_manifest_url(self, url: str, streamingToken: str):
        return self.urlTools.get_manifest_url(proxyUrl=url, streamingToken=streamingToken)

    def update_redirection(self, proxyUrl, actualUrl, baseURL):
        self.urlTools.update_redirection(proxyUrl, actualUrl, baseURL)

    def replace_baseurl(self, url, streamingToken):
        return self.urlTools.replace_baseurl(url, streamingToken)

    def handle_manifest(self, request, type='get'):
        parsedUrl = urlparse(request.path)
        qs = parse_qs(parsedUrl.query)
        if 'path' in qs and 'hostname' in qs and 'token' in qs:
            origToken = qs['token'][0]
            streamingToken = self.get_streaming_token()
            if streamingToken is None:
                # This can occur at the first call. The notification with the token is not
                # sent immediately
                xbmc.log("Using original token", xbmc.LOGDEBUG)
                self.set_streaming_token(origToken)
                streamingToken = origToken
            manifestUrl = self.get_manifest_url(request.path, streamingToken)
            with self.lock:
                if type == 'get':
                    response = self.session.get_manifest(manifestUrl)
                    manifestBaseurl = self.baseurl_from_manifest(response.content)
                elif type == 'head':
                    response = self.session.do_head(manifestUrl)
                    manifestBaseurl = None
            self.update_redirection(request.path, response.url, manifestBaseurl)
            request.send_response(response.status_code)
            request.end_headers()
            request.wfile.write(response.content)

        else:
            request.send_response(404)
            request.end_headers()

    def handle_default(self, request):
        url = self.replace_baseurl(request.path, self.get_streaming_token())
        parsedDestUrl = urlparse(url)
        if parsedDestUrl.scheme == 'https':
            connection = HTTPConnection(parsedDestUrl.hostname, timeout=10)
        else:
            connection = HTTPSConnection(parsedDestUrl.hostname, timeout=10)
        connection.request("GET", parsedDestUrl.path)
        response = connection.getresponse()
        request.send_response(response.status)
        chunked = False
        for header in response.headers:
            if header.lower() == 'transfer-encoding':
                if response.headers[header].lower() == 'chunked':
                    #  We don't know the length upfront
                    chunked = True
            request.send_header(header, response.headers[header])
        request.end_headers()
        lenProcessed = 0
        if chunked:  # process the same chunks as received
            response.chunked = False
            blockLen = response.readline()
            length = int(blockLen, 16)
            while length > 0:
                lenProcessed += length
                block = response.read(length)
                blockToWrite = bytearray(blockLen)
                blockToWrite.extend(block + b'\r\n')
                request.wfile.write(blockToWrite)
                response.readline()
                blockLen = response.readline()
                length = int(blockLen, 16)
            blockToWrite = bytearray(blockLen)
            blockToWrite.extend(b'\r\n')
            request.wfile.write(blockToWrite)
        else:
            expectedLen = int(response.headers['Content-Length'])
            block = response.read(8192)
            while lenProcessed < expectedLen:
                lenProcessed += len(block)
                written = request.wfile.write(block)
                if written != len(block):
                    xbmc.log('count-written ({0})<>len(block)({1})'.format(written, len(block)))
                    return
                block = response.read(8192)

    def handle_get(self, request):
        path = request.path  # Path with parameters received from request e.g. "/manifest?id=234324"
        xbmc.log('HTTP GET Request received: {0}'.format(unquote(path)), xbmc.LOGDEBUG)
        try:
            if '/manifest' in path:
                self.handle_manifest(request)
            elif '/function' in path:
                self.handle_function(request)
            else:
                self.handle_default(request)

            xbmc.log('HTTP GET Request processed: {0}'.format(unquote(path)), xbmc.LOGDEBUG)
        except ConnectionResetError as exc:
            xbmc.log('Connection reset during processing: {0}'.format(exc), xbmc.LOGERROR)
            xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
        except ConnectionAbortedError as exc:
            xbmc.log('Connection aborted during processing: {0}'.format(exc), xbmc.LOGERROR)
            xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
        except Exception as exc:
            xbmc.log('Exception in handle_get(): {0}'.format(exc), xbmc.LOGERROR)
            xbmc.log(traceback.format_exc(), xbmc.LOGDEBUG)
            request.send_response(500)
            request.end_headers()

    def handle_post(self, request):
        path = request.path  # Path with parameters received from request e.g. "/license?id=234324"
        xbmc.log('HTTP POST request received: {0}'.format(unquote(path)), xbmc.LOGDEBUG)
        if '/license' not in path:
            request.send_response(404)
            request.end_headers()
            return
        try:
            length = int(request.headers.get('content-length', 0))
            receivedData = request.rfile.read(length)

            parsedUrl = urlparse(request.path)
            contentId = parse_qs(parsedUrl.query)['ContentId'][0]

            with self.lock:
                self.session.load_cookies()
            hdrs = {}
            for key in request.headers:
                hdrs[key] = request.headers[key]
            with self.lock:
                response = self.session.get_license(contentId, receivedData, hdrs)
            for key in response.headers:
                request.headers.add_header(key, response.headers[key])
                if key.lower() == 'x-streaming-token':
                    self.set_streaming_token(response.headers[key])
            request.send_response(response.status_code)
            request.end_headers()
            request.wfile.write(response.content)
            xbmc.log('HTTP POST request processed: {0}'.format(unquote(path)), xbmc.LOGDEBUG)
        except ConnectionResetError as exc:
            xbmc.log('Connection reset during processing: {0}'.format(exc), xbmc.LOGERROR)
        except ConnectionAbortedError as exc:
            xbmc.log('Connection aborted during processing: {0}'.format(exc), xbmc.LOGERROR)
        except Exception as exc:
            xbmc.log('Exception in do_post(): {0}'.format(exc), xbmc.LOGERROR)
            request.send_response(500)
            request.end_headers()

    @staticmethod
    def handle_options(request):
        request.send_response(200, "ok")
        request.send_header('Access-Control-Allow-Origin', '*')
        request.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        request.send_header('access-control-allow-headers', 'Accept-Charset')
        request.send_header('access-control-allow-headers', 'Accept-Encoding')
        request.send_header('access-control-allow-headers', 'Access-Control-Request-Headers')
        request.send_header('access-control-allow-headers', 'Access-Control-Request-Method')
        request.send_header('access-control-allow-headers', 'Authorization')
        request.send_header('access-control-allow-headers', 'Cache-Control')
        request.send_header('access-control-allow-headers', 'Connection')
        request.send_header('access-control-allow-headers', 'Content-Encoding')
        request.send_header('access-control-allow-headers', 'Content-Type')
        request.send_header('access-control-allow-headers', 'Content-Length')
        request.send_header('access-control-allow-headers', 'Cookie')
        request.send_header('access-control-allow-headers', 'DNT')
        request.send_header('access-control-allow-headers', 'Date')
        request.send_header('access-control-allow-headers', 'Host')
        request.send_header('access-control-allow-headers', 'If-Modified-Since')
        request.send_header('access-control-allow-headers', 'Keep-Alive, Origin')
        request.send_header('access-control-allow-headers', 'Referer')
        request.send_header('access-control-allow-headers', 'Server')
        request.send_header('access-control-allow-headers', 'TokenIssueTime')
        request.send_header('access-control-allow-headers', 'Transfer-Encoding')
        request.send_header('access-control-allow-headers', 'User-Agent')
        request.send_header('access-control-allow-headers', 'Vary')
        request.send_header('access-control-allow-headers', 'X-CustomHeader')
        request.send_header('access-control-allow-headers', 'X-Requested-With')
        request.send_header('access-control-allow-headers', 'password')
        request.send_header('access-control-allow-headers', 'username')
        request.send_header('access-control-allow-headers', 'x-request-id')
        request.send_header('access-control-allow-headers', 'x-ratelimit-app')
        request.send_header('access-control-allow-headers', 'x-guest-token')
        request.send_header('access-control-allow-headers', 'X-HTTP-Method-Override')
        request.send_header('access-control-allow-headers', 'x-oesp-username')
        request.send_header('access-control-allow-headers', 'x-oesp-token')
        request.send_header('access-control-allow-headers', 'x-cus')
        request.send_header('access-control-allow-headers', 'x-dev')
        request.send_header('access-control-allow-headers', 'X-Client-Id')
        request.send_header('access-control-allow-headers', 'X-Device-Code')
        request.send_header('access-control-allow-headers', 'X-Language-Code')
        request.send_header('access-control-allow-headers', 'UserRole')
        request.send_header('access-control-allow-headers', 'x-session-id')
        request.send_header('access-control-allow-headers', 'x-entitlements-token')
        request.send_header('access-control-allow-headers', 'x-go-dev')
        request.send_header('access-control-allow-headers', 'x-profile')
        request.send_header('access-control-allow-headers', 'x-api-key')
        request.send_header('access-control-allow-headers', 'nv-authorizations')
        request.send_header('access-control-allow-headers', 'X-Viewer-Id')
        request.send_header('access-control-allow-headers', 'x-oesp-profile-id')
        request.send_header('access-control-allow-headers', 'x-streaming-token')
        request.send_header('access-control-allow-headers', 'x-streaming-token-refresh-interval')
        request.send_header('access-control-allow-headers', 'x-drm-device-id')
        request.send_header('access-control-allow-headers', 'x-profile-id')
        request.send_header('access-control-allow-headers', 'x-ui-language')
        request.send_header('access-control-allow-headers', 'deviceName')
        request.send_header('access-control-allow-headers', 'x-drm-schemeId')
        request.send_header('access-control-allow-headers', 'x-refresh-token')
        request.send_header('access-control-allow-headers', 'X-Username')
        request.send_header('access-control-allow-headers', 'Location')
        request.send_header('access-control-allow-headers', 'x-tracking-id')
        request.end_headers()

    def handle_function(self, request):
        parsedUrl = urlparse(request.path)
        method = parsedUrl.path[10:]
        qs = parse_qs(parsedUrl.query)
        if 'args' in qs:
            args = json.loads(qs['args'][0])
            try:
                callableMethod = getattr(self.session, method)
                with self.lock:
                    retval = callableMethod(**args)
                request.send_response(200)
                if retval is None:
                    request.send_header('content-type', 'text/html')
                    request.end_headers()
                else:
                    request.send_header('content-type', 'application/octet-stream')
                    request.end_headers()
                    request.wfile.write(pickle.dumps(retval))
            except WebException as exc:
                request.send_response(exc.get_status())
                request.send_header('content-type', 'text/html')
                request.end_headers()
                request.wfile.write(exc.get_response())
        else:
            request.send_response(400)
            request.end_headers()

    def handle_head(self, request):
        #  We should forward this to real server, but for now we will respond with code 501
        path = request.path  # Path with parameters received from request e.g. "/license?id=234324"
        xbmc.log('HTTP HEAD request received: {0}'.format(unquote(path)), xbmc.LOGDEBUG)
        if '/manifest' in path:
            self.handle_manifest(request, 'head')
        else:
            request.send_response(501)
            request.end_headers()

    @staticmethod
    def baseurl_from_manifest(manifest):
        document = minidom.parseString(manifest)
        for parent in document.getElementsByTagName('MPD'):
            periods = parent.getElementsByTagName('Period')
            for period in periods:
                baseURL = period.getElementsByTagName('BaseURL')
                if baseURL.length == 0:
                    return None
                return baseURL[0].childNodes[0].data
        return None
