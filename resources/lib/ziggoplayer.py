"""
Module with classes for playing videos
"""
import xbmc

from resources.lib.utils import WebException


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
            xbmc.log("ZIGGOPLAYER STOPPED item " + self.item.url, xbmc.LOGDEBUG)
            self.item = None
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

    def setItem(self, item):
        self.item = item
