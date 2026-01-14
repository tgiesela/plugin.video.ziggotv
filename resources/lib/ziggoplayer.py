"""
Module with classes for playing videos
"""
import xbmc
from resources.lib.utils import WebException, ZiggoKeyMap
from resources.lib.videohelpers import VideoItem

class ZiggoPlayer(xbmc.Player):
    """
    class extending the default VideoPlayer.
    """

    def __init__(self):
        super().__init__()
        self.item = None
        self.prePadding = None
        xbmc.log("ZIGGOPLAYER CREATED", xbmc.LOGDEBUG)
        self.replay = False
        self.keymap: ZiggoKeyMap = None

    def __del__(self):
        if self.item is not None:
            try:
                self.item.stop()
            except WebException as exc:
                xbmc.log("ZIGGOPLAYER WEBEXC {0}".format(exc))
            xbmc.log("ZIGGOPLAYER DELETED item " + self.item.url, xbmc.LOGDEBUG)
            self.item = None
        xbmc.log("ZIGGOPLAYER DELETED", xbmc.LOGDEBUG)

    def onPlayBackStopped(self) -> None:
        if self.item is not None:
            try:
                self.item.stop()
            except WebException as exc:
                xbmc.log("ZIGGOPLAYER WEBEXC {0}".format(exc))
            xbmc.log("ZIGGOPLAYER STOPPED item ", xbmc.LOGDEBUG)
            self.item = None

        if self.keymap is not None:
            self.keymap.deactivate()
            self.keymap = None
        xbmc.log("ZIGGOPLAYER STOPPED", xbmc.LOGDEBUG)

    def onPlayBackPaused(self) -> None:
        xbmc.log("ZIGGOPLAYER PAUSED", xbmc.LOGDEBUG)

    def onAVStarted(self) -> None:
        xbmc.log("ZIGGOPLAYER AVSTARTED", xbmc.LOGDEBUG)
        if self.replay:
            xbmc.log("ZIGGOPLAYER POSITIONED TO BEGINNING", xbmc.LOGDEBUG)
            self.seekTime(self.prePadding / 1000)

    def onPlayBackEnded(self) -> None:
        xbmc.log("ZIGGOPLAYER PLAYBACKENDED", xbmc.LOGDEBUG)
        if self.keymap is not None:
            self.keymap.deactivate()
            self.keymap = None

    def onAVChange(self) -> None:
        xbmc.log("ZIGGOPLAYER AVCHANGE", xbmc.LOGDEBUG)

    def onPlayBackStarted(self) -> None:
        xbmc.log("ZIGGOPLAYER PLAYBACK STARTED", xbmc.LOGDEBUG)

    def onPlayBackError(self) -> None:
        xbmc.log("ZIGGOPLAYER PLAYBACK ERROR", xbmc.LOGDEBUG)

    def set_replay(self, isReplay, time=0):
        """
        method to set that the video is for replay and set an optional start time to position the video
        @param isReplay:
        @param time:
        @return:
        """
        self.replay = isReplay
        self.prePadding = time

    def set_item(self, item: VideoItem):
        """
        Function to set the listitem of the current playing video
        
        :param self: 
        :param item: Description
        """
        self.item = item

    def set_keymap(self, keymap: ZiggoKeyMap):
        """
        Function to set the keymap. The player will activate/deactive when video stop/starts
        
        :param self: 
        :param keymap: keymap object
        :type keymap: ZiggoKeyMap
        """
        self.keymap = keymap
        self.keymap.activate()
