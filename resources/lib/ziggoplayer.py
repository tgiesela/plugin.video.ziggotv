"""
Module with classes for playing videos
"""
import xbmc
from resources.lib.utils import WebException, ZiggoKeyMap

class ZiggoPlayer(xbmc.Player):
    """
    class extending the default VideoPlayer.
    """

    def __init__(self):
        super().__init__()
        self.prePadding = None
        xbmc.log("ZIGGOPLAYER CREATED", xbmc.LOGDEBUG)
        self.replay = False
        self.stopCallback = None
        self.keymap: ZiggoKeyMap = None

    def __del__(self):
        if self.stopCallback is not None:
            self.stopCallback()
        xbmc.log("ZIGGOPLAYER DELETED", xbmc.LOGDEBUG)

    def onPlayBackStopped(self) -> None:
        if self.stopCallback is not None:
            self.stopCallback()
        xbmc.log("ZIGGOPLAYER PLAYBACK STOPPED", xbmc.LOGDEBUG)

    def onPlayBackPaused(self) -> None:
        xbmc.log("ZIGGOPLAYER PAUSED", xbmc.LOGDEBUG)

    def onAVStarted(self) -> None:
        xbmc.log("ZIGGOPLAYER AVSTARTED", xbmc.LOGDEBUG)
        if self.replay:
            xbmc.log("ZIGGOPLAYER POSITIONED TO BEGINNING", xbmc.LOGDEBUG)
            self.seekTime(self.prePadding / 1000)

    def onPlayBackEnded(self) -> None:
        xbmc.log("ZIGGOPLAYER PLAYBACKENDED", xbmc.LOGDEBUG)
        if self.stopCallback is not None:
            self.stopCallback()

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

    def set_stop_callback(self, callback):
        """
        Function to set a callback function that will be called when playback stops
        
        :param self: 
        :param callback: callback function
        """
        self.stopCallback = callback
