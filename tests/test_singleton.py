"""
Test for singleton approach (may be an option for a future refactor)
"""
import xbmcaddon
from resources.lib import utils
from resources.lib.channel import ChannelList
from resources.lib.globals import G
from resources.lib.listitemhelper import ListitemHelper
from resources.lib.utils import ProxyHelper, SharedProperties, ZiggoKeyMap
from resources.lib.webcalls import LoginSession
from resources.lib.ziggoplayer import ZiggoPlayer
from tests.test_base import TestBase
from tests.testinputstreamhelper import Helper

class VideoHelperSingleton():
    """
    Singleton class example
    """
    _INSTANCE = None
    _INITIALIZED = False

    def __new__(cls, *args, **kwargs):
        if cls._INSTANCE is None:
            cls._INSTANCE = super(VideoHelperSingleton, cls).__new__(cls)
        return cls._INSTANCE

    def __init__(self, addon: xbmcaddon.Addon):
        if self._INITIALIZED:
            return
        self.addon = addon
        self.helper = ProxyHelper(addon)
        self.player: ZiggoPlayer = None
        self.liHelper: ListitemHelper = ListitemHelper(addon)
        self.customerInfo = self.helper.dynamic_call(LoginSession.get_customer_info)
        self.entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)
        self.channels = ChannelList(self.helper.dynamic_call(LoginSession.get_channels), self.entitlements)
        self.uuId = SharedProperties(addon=self.addon).get_uuid()
        self.keymap = ZiggoKeyMap(self.addon)
        isHelper = Helper(G.PROTOCOL, drm=G.DRM)
        isHelper.check_inputstream()
        # Used for updating events when playing a live channel
        self.updateeventsignal: utils.TimeSignal = None
        self.currentchannel = None
        # This can be set to call a function when the videoplayer stops
        self.requestorCallbackStop = None
        self._INITIALIZED = True


class TestVideoPlayer(TestBase):
    """
    Test class for singleton approach (may be an option for a future refactor)
    """
    def test_singleton(self):
        """
        The actual test
        
        :param self: 
        """

        player1 = VideoHelperSingleton(self.addon)
        player2 = VideoHelperSingleton(self.addon)

        self.assertIs(player1, player2)
        self.assertIs(player1.channels.channels[0].name, player2.channels.channels[0].name)
