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

    def build_proxy_url(self, locator) -> str:
        """
        function to build an url to pass to ISA
        @param streamingToken:
        @param locator:
        @return:
        """
        xbmc.log('Using proxy server', xbmc.LOGDEBUG)
        o = urlparse(locator)
        Components = namedtuple(
            typename='Components',
            field_names=['scheme', 'netloc', 'path', 'url', 'query', 'fragment']
        )

        queryParams = {
            'path': o.path,
#           'token': streamingToken,
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

