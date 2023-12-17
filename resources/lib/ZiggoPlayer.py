from collections import namedtuple

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

import json

from resources.lib.globals import G


class ZiggoPlayer(xbmc.Player):

    def onPlayBackStopped(self) -> None:
        xbmc.log("VIDEO PLAYER STOPPED", xbmc.LOGINFO)

    def onPlayBackPaused(self) -> None:
        xbmc.log("VIDEO PLAYER PAUSED", xbmc.LOGINFO)

    def onAVStarted(self) -> None:
        xbmc.log("VIDEO PLAYER AVSTARTED", xbmc.LOGINFO)


class VideoHelpers:
    def __init__(self, addon: xbmcaddon.Addon, session):
        self.session = session
        self.addon = addon

    def __get_widevine_license(self, addon_name):
        addon_path = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        with open(addon_path + "widevine.json", mode="r") as cert_file:
            contents = cert_file.read()

        return contents

    def __send_notification(self, item: xbmcgui.ListItem, token, locator):
        tag: xbmc.InfoTagVideo = item.getVideoInfoTag()
        uniqueid = tag.getUniqueID('ziggochannelid')
        params = {'sender': self.addon.getAddonInfo('id'),
                  'message': tag.getTitle(),
                  'data': {'command': 'play_video',
                           'command_params': {'uniqueId': uniqueid, 'streamingToken': token, 'locator': locator}
                           },
                  }

        command = json.dumps({'jsonrpc': '2.0',
                              'method': 'JSONRPC.NotifyAll',
                              'params': params,
                              'id': 1,
                              })
        result = xbmc.executeJSONRPC(command)

    def listitem_from_url(self, requesturl, streaming_token, drmContentId) -> xbmcgui.ListItem:
        li = xbmcgui.ListItem(path=requesturl)
        li.setProperty('IsPlayable', 'true')
        rslt = li.getProperty('isplayable')
        tag: xbmc.InfoTagVideo = li.getVideoInfoTag()
        tag.setMediaType('video')
        li.setMimeType('application/dash+xml')
        li.setContentLookup(False)
        li.setProperty(
            key='inputstream',
            value='inputstream.adaptive')
        li.setProperty(
            key='inputstream.adaptive.license_flags',
            value='persistent_storage')
        li.setProperty(
            key='inputstream.adaptive.manifest_type',
            value=G.PROTOCOL)
        li.setProperty(
            key='inputstream.adaptive.license_type',
            value=G.DRM)
        license_headers = dict(G.CONST_BASE_HEADERS)
        # 'Content-Type': 'application/octet-stream',
        license_headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0',
            'Host': 'prod.spark.ziggogo.tv',
            'x-streaming-token': streaming_token,
            'X-cus': self.session.customer_info['customerId'],
            'x-go-dev': '214572a3-2033-4327-b8b3-01a9a674f1e0',  # Dummy? TBD: Generate one
            'x-drm-schemeId': 'edef8ba9-79d6-4ace-a3c8-27dcd51d21ed',
            'deviceName': 'Firefox'
        })
        for key in self.session.extra_headers:
            license_headers.update({key: self.session.extra_headers[key]})

        from urllib.parse import urlencode
        use_license_proxy = True
        if use_license_proxy:
            url = 'http://127.0.0.1:6969/license'
            params = {'ContentId': drmContentId,
                      'addon': self.addon.getAddonInfo('id')}
            url = (url + '?' + urlencode(params) +
                   '|' + urlencode(license_headers) +
                   '|R{SSM}'
                   '|')
        else:
            cookies = self.session.cookies.get_dict()
            url = G.license_URL
            params = {'ContentId': drmContentId}
            url = (url + '?' + urlencode(params) +
                   '|' + urlencode(license_headers) +
                   'Cookie=ACCESSTOKEN={0};CLAIMSTOKEN={1}'.format(cookies['ACCESSTOKEN'], cookies['CLAIMSTOKEN']) +
                   '|R{SSM}'
                   '|')
        # Prefix for request {SSM|SID|KID|PSSH}
        # R - The data will be kept as is raw
        # b - The data will be base64 encoded
        # B - The data will be base64 encoded and URL encoded
        # D - The data will be decimal converted (each char converted as integer concatenated by comma)
        # H - The data will be hexadecimal converted (each character converted as hexadecimal and concatenated)
        # Prefix for response
        # -  Not specified, or, R if the response payload is in binary raw format
        # B if the response payload is encoded as base64
        # J[license tokens] if the response payload is in JSON format. You must specify the license tokens
        #    names to allow inputstream.adaptive searches for the license key and optionally the HDCP limit.
        #    The tokens must be separated by ;. The first token must be for the key license, the second one,
        #    optional, for the HDCP limit. The HDCP limit is the result of resolution width multiplied for
        #    its height. For example to limit until to 720p: 1280x720 the result will be 921600.
        # BJ[license tokens] same meaning of J[license tokens] but the JSON is encoded as base64.
        # HB if the response payload is after two return chars \r\n\r\n in binary raw format.

        li.setProperty(
            key='inputstream.adaptive.license_key',
            value=url)
        # Test
        # server certificate to be used to encrypt messages to the license server. Should be encoded as Base64
        widevine_certificate = self.__get_widevine_license(self.addon.getAddonInfo('id'))
        li.setProperty(
            key='inputstream.adaptive.server_certificate',
            value=widevine_certificate)
        self.__send_notification(li, streaming_token, url)  # send the streaming-token to the Service

        return li
