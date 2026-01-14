"""
Module with a collection of url functions
"""
from collections import namedtuple
from urllib.parse import urlparse, parse_qs, urlunparse, urlencode

import xbmc
import xbmcaddon


class UrlTools:
    """
    class implementing all kind of functions to manipulate the urls
    """
    def __init__(self, addon: xbmcaddon.Addon):
        self.addon = addon

    def build_url(self, streamingToken, locator) -> str:
        """
        function to build an url to pass to ISA
        @param streamingToken:
        @param locator:
        @return:
        """
        useProxy = self.addon.getSettingBool('use-proxy')
        if useProxy:
            xbmc.log('Using proxy server', xbmc.LOGINFO)
            o = urlparse(locator)
            Components = namedtuple(
                typename='Components',
                field_names=['scheme', 'netloc', 'path', 'url', 'query', 'fragment']
            )

            queryParams = {
                'path': o.path,
                'token': streamingToken,
                'hostname': o.hostname,
            }
            origParams = parse_qs(o.query)
            for param, value in origParams.items():
                queryParams.update({param: value[0]})
            port = self.addon.getSetting('proxy-port')
            ip = self.addon.getSetting('proxy-ip')
            url = urlunparse(
                Components(
                    scheme='http',
                    netloc='{0}:{1}'.format(ip, port),
                    query=urlencode(queryParams),
                    path='manifest',
                    url='',
                    fragment=''
                )
            )
            xbmc.log('BUILD URL: {0}'.format(url), xbmc.LOGDEBUG)
            return url
        if '/dash' in locator:
            return locator.replace("/dash", "/dash,vxttoken=" + streamingToken).replace("http://", "https://")
        if '/sdash' in locator:
            return locator.replace("/sdash", "/sdash,vxttoken=" + streamingToken).replace("http://", "https://")
        if '/live' in locator:
            return locator.replace("/live", "/live,vxttoken=" + streamingToken).replace("http://", "https://")
        return locator
