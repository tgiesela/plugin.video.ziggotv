# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
from urllib.parse import unquote

from resources.lib.avstream import AvStream, StreamSession
from resources.lib.channel import Channel, ChannelList
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.urltools import UrlTools
from resources.lib.utils import ProxyHelper

class TestVideoPlayer:
    def create_stream(self, zender: Channel, activewebsession) -> AvStream:
        stream:AvStream = ProxyHelper(activewebsession.addon).dynamic_call(
            StreamSession.define_stream,
            streamItem=zender,
            suppressHD=False)
        return stream

    def delete_stream(self, stream: AvStream, activewebsession):
        stream:AvStream = ProxyHelper(activewebsession.addon).dynamic_call(
            StreamSession.stop_stream,
            streamid=stream.id)

    def test_widevine_license(self, activewebsession):
        activewebsession.session.refresh_widevine_license()

    def test_buildurl(self, activewebsession):
        # pylint: disable=too-many-statements, too-many-locals
        urlHelper = UrlTools(activewebsession.addon)
        helpers = ListitemHelper(activewebsession.addon)
        activewebsession.session.refresh_widevine_license()
        activewebsession.session.get_customer_info()

        # Test for play channels

        activewebsession.session.refresh_channels()
        channels = activewebsession.session.get_channels()
        entitlements = activewebsession.session.get_entitlements()
        cl = ChannelList(channels, entitlements)
        zender:Channel = cl.find_channel_by_number(1)

        stream:AvStream = self.create_stream(zender, activewebsession)

        url = 'http://wp-obc1-live-nl-prod.prod.cdn.dmdsdp.com/dash/go-dash-hdready-avc/NL_000001_019401/manifest.mpd'
        expectedUrl = ('http://127.0.0.1:6868/manifest?'
                       'path=%2Fdash%2Fgo-dash-hdready-avc%2FNL_000001_019401%2Fmanifest.mpd&'
                       'hostname=wp-obc1-live-nl-prod.prod.cdn.dmdsdp.com')
        expectedManifestUrl = ('https://wp-obc1-live-nl-prod.prod.cdn.dmdsdp.com/dash,'
                              f'vxttoken={stream.streamInfo.token}/go-dash-hdready-avc'
                               '/NL_000001_019401/manifest.mpd')
        redirectedUrl = (
            'https://da-d436304820010b88000108000000000000000008.id.cdn.upcbroadband.com/dash,'
           f'vxttoken={stream.streamInfo.token}/go-dash-hdready-avc/NL_000001_019401/manifest.mpd')
        createdUrl = urlHelper.build_proxy_url(url)

        assert createdUrl == expectedUrl, 'URL not as expected'
        s = createdUrl.find('/manifest')
        manifestUrl = stream.get_manifest_url(createdUrl[s:])
        assert manifestUrl == expectedManifestUrl, 'URL not as expected'
        print(manifestUrl)
        stream.update_redirection(createdUrl[s:], redirectedUrl)
        manifestUrl = stream.get_manifest_url(createdUrl[s:])
        assert manifestUrl == redirectedUrl, 'URL not as expected'
        videoUrl = (
            '/private1/Header.m4s')
        expectedVideoUrl = (
            'https://da-d436304820010b88000108000000000000000008.id.cdn.upcbroadband.com/dash,'
           f'vxttoken={stream.streamInfo.token}/go-dash-hdready-avc/NL_000001_019401/private1/Header.m4s')
        baseurl = stream.replace_baseurl(videoUrl, stream.streamInfo.token)
        assert expectedVideoUrl == baseurl, 'URL not as expected'

        li = helpers.listitem_from_url(url, stream.streamInfo.token, 'content')
        print(li.getLabel())

        # Tests for replay
        self.delete_stream(stream, activewebsession)
        stream:AvStream = self.create_stream(zender, activewebsession)

        url = ('http://wp-pod3-replay-vxtoken-nl-prod.prod.cdn.dmdsdp.com/sdash/LIVE$NL_000001_019401/index.mpd'
               '/Manifest?device=AVC-OTT-DASH-PR-WV&start=2023-12-15T14%3A16%3A00Z&end=2023-12-15T14%3A51%3A00Z')
        expectedUrl = ('http://127.0.0.1:6868/manifest?path=%2Fsdash%2FLIVE%24NL_000001_019401%2Findex.mpd%2FManifest'
                       '&hostname=wp-pod3-replay-vxtoken-nl-prod.prod.cdn.dmdsdp.com'
                       '&device=AVC-OTT-DASH-PR-WV&start=2023-12-15T14%3A16%3A00Z&end=2023-12-15T14%3A51%3A00Z')
        expectedManifestUrl = (
            'https://wp-pod3-replay-vxtoken-nl-prod.prod.cdn.dmdsdp.com/sdash,'
           f'vxttoken={stream.streamInfo.token}/LIVE$NL_000001_019401/index.mpd'
            '/Manifest?device=AVC-OTT-DASH-PR-WV&start=2023-12-15T14%3A16%3A00Z&end=2023-12-15T14%3A51%3A00Z')
        redirectedUrl = (
            'https://da-d436304820010b88000108000000000000000008.id.cdn.upcbroadband.com/wp/wp-pod3-replay-vxtoken-nl'
           f'-prod.prod.cdn.dmdsdp.com/sdash,vxttoken={stream.streamInfo.token}/LIVE$NL_000001_019401/index.mpd/'
            'Manifest'
        )
        createdUrl = urlHelper.build_proxy_url(url)

        assert createdUrl == expectedUrl, 'URL not as expected'
        s = createdUrl.find('/manifest')
        manifestUrl = stream.get_manifest_url(createdUrl[s:])
        assert manifestUrl == expectedManifestUrl, 'URL not as expected'
        print(manifestUrl)
        # Now update redirection and then create the manifest URL again. it should be identical to the redirected URL
        stream.update_redirection(createdUrl[s:], redirectedUrl)
        manifestUrl = stream.get_manifest_url(createdUrl[s:])
        assert manifestUrl == redirectedUrl, 'URL not as expected'

        li = helpers.listitem_from_url(url, stream.streamInfo.token, 'content')

        videoUrl = (
            '/S!d2ESQVZDLU9UVC1EQVNILVBSLVdWEgJDeAz7ykSIKfvKFgSf/QualityLevels(128000,'
            'Level_params=dxADIeIBnw..)/Fragments(audio_482_dut=Init)')
        expectedVideoUrl = (
            'https://da-d436304820010b88000108000000000000000008.id.cdn.upcbroadband.com/'
            'wp/wp-pod3-replay-vxtoken-nl-prod.prod.cdn.dmdsdp.com/sdash,'
           f'vxttoken={stream.streamInfo.token}/LIVE$NL_000001_019401/index.mpd/S'
            '!d2ESQVZDLU9UVC1EQVNILVBSLVdWEgJDeAz7ykSIKfvKFgSf/QualityLevels(128000,'
            'Level_params=dxADIeIBnw..)/Fragments(audio_482_dut=Init)')
        baseurl = stream.replace_baseurl(videoUrl, stream.streamInfo.token)
        assert expectedVideoUrl == baseurl, 'URL not as expected'

        # Test for video-on-demand urls
        self.delete_stream(stream, activewebsession)
        stream:AvStream = self.create_stream(zender, activewebsession)

        url = (
            'https://wp-pod1-vod-vxtoken-nl-prod.prod.cdn.dmdsdp.com/sdash'
            '/0e378a707155514f39851ab1e45b6560_734142457f0da3caf957ba97e73249e6/index.mpd/Manifest?device=BR-AVC-DASH')
        expectedUrl = ('http://127.0.0.1:6868/manifest?path=%2Fsdash'
                       '%2F0e378a707155514f39851ab1e45b6560_734142457f0da3caf957ba97e73249e6%2Findex.mpd%2FManifest'
                       '&hostname=wp-pod1-vod-vxtoken-nl-prod.prod.cdn.dmdsdp.com&device=BR'
                       '-AVC-DASH')
        expectedManifestUrl = (
            'https://wp-pod1-vod-vxtoken-nl-prod.prod.cdn.dmdsdp.com/sdash,'
           f'vxttoken={stream.streamInfo.token}/0e378a707155514f39851ab1e45b6560_734142457f0da3caf957ba97e73249e6/'
           'index.mpd/Manifest?device=BR-AVC-DASH')
        redirectedUrl = (
            'https://da-d436304820010b88000108000000000000000008.id.cdn.upcbroadband.com/wp/wp-pod3-replay-vxtoken-nl'
           f'-prod.prod.cdn.dmdsdp.com/sdash,vxttoken={stream.streamInfo.token}/LIVE$NL_000001_019401/index.mpd/'
           'Manifest'
        )
        createdUrl = urlHelper.build_proxy_url(url)

        assert createdUrl == expectedUrl, 'URL not as expected'
        s = createdUrl.find('/manifest')
        manifestUrl = stream.get_manifest_url(createdUrl[s:])
        assert manifestUrl == expectedManifestUrl, 'URL not as expected'
        print(manifestUrl)

        # Now update redirection and then create the manifest URL again. it should be identical to the redirected URL
        stream.update_redirection(createdUrl[s:], redirectedUrl)
        manifestUrl = stream.get_manifest_url(createdUrl[s:])
        assert manifestUrl == redirectedUrl, 'URL not as expected'

        self.delete_stream(stream, activewebsession)
        stream:AvStream = self.create_stream(zender, activewebsession)
        url = ('http://wp4-vxtoken-anp-g05060506-hzn-nl.t1.prd.dyncdn.dmdsdp.com/live/disk1/'
               'NL_000011_019563/go-dash-hdready-avc/NL_000011_019563.mpd')
        expectedUrl = ('http://127.0.0.1:6868/manifest?path=/live/disk1/NL_000011_019563/go-dash-hdready-avc/'
                       'NL_000011_019563.mpd&'
                       'hostname=wp4-vxtoken-anp-g05060506-hzn-nl.t1.prd.dyncdn.dmdsdp.com')
        expectedManifestUrl = (
            'https://wp4-vxtoken-anp-g05060506-hzn-nl.t1.prd.dyncdn.dmdsdp.com/'
           f'live,vxttoken={stream.streamInfo.token}/disk1/'
            'NL_000011_019563/go-dash-hdready-avc/NL_000011_019563.mpd')
        redirectedUrl = (
            'https://da-d436304520010b88000108000000000000000005.id.cdn.upcbroadband.com/wp/'
           f'wp4-vxtoken-anp-g05060506-hzn-nl.t1.prd.dyncdn.dmdsdp.com/live,vxttoken={stream.streamInfo.token}/disk1/'
            'NL_000011_019563/go-dash-hdready-avc/NL_000011_019563.mpd'
        )
        createdUrl = urlHelper.build_proxy_url(url)
        assert unquote(createdUrl) == expectedUrl, 'URL not as expected'
        s = createdUrl.find('/manifest')
        manifestUrl = stream.get_manifest_url(createdUrl[s:])
        assert manifestUrl == expectedManifestUrl, 'URL not as expected'
        print(manifestUrl)
        # Now update redirection and then create the manifest URL again. it should be identical to the redirected URL
        stream.update_redirection(createdUrl[s:], redirectedUrl, '../_shared_a997aca19aa594f6aba2bcbd76c87946/')
        manifestUrl = stream.get_manifest_url(createdUrl[s:])
        assert manifestUrl == redirectedUrl, 'URL not as expected'
        videoUrl = ('http://127.0.0.1:6868/_shared_a997aca19aa594f6aba2bcbd76c87946/NL_000011_019563-mp4a_128000_nld'
                    '=20000-init.mp4')
        expectedUrl = (
            'https://da-d436304520010b88000108000000000000000005.id.cdn.upcbroadband.com/wp/'
           f'wp4-vxtoken-anp-g05060506-hzn-nl.t1.prd.dyncdn.dmdsdp.com/live,vxttoken={stream.streamInfo.token}/disk1/'
            'NL_000011_019563/_shared_a997aca19aa594f6aba2bcbd76c87946/NL_000011_019563-mp4a_128000_nld=20000-init.mp4')
        defaultUrl = stream.replace_baseurl(videoUrl, stream.streamInfo.token)
        assert expectedUrl == defaultUrl, 'URL not as expected'
        print(defaultUrl)
        self.delete_stream(stream, activewebsession)
        activewebsession.session.close()

# if __name__ == '__main__':
#     unittest.main()
