# pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring
import xbmcaddon
import xbmcgui
import xbmc

class Addon(xbmcaddon.Addon):
    """
        Class to support use of setting/getting the addon settings
        Very primitive.
    """

    def __init__(self, name):
        super().__init__(name)
        self.settings = {}

    # pylint: disable=redefined-builtin
    def setSetting(self, id: str, value: str) -> None:
        self.settings.update({id: value})

    def setSettingNumber(self, id: str, value: float) -> None:
        self.settings.update({id: value})

    def setSettingBool(self, id: str, value: bool) -> None:
        self.settings.update({id: value})

    def getSetting(self, id: str) -> str:
        return self.settings[id]

    def getSettingBool(self, id: str) -> bool:
        return bool(self.settings[id])

    def getSettingInt(self, id: str) -> int:
        return int(self.settings[id])

    def getSettingNumber(self, id: str) -> float:
        return float(self.settings[id])
    # pylint: enable=redefined-builtin

class ListItem(xbmcgui.ListItem):
    """
        Class to support use of xbmcgui.ListItem in tests.
        Very primitive.
    """
    class InfoTagVideo(xbmc.InfoTagVideo):
        def __init__(self):
            super().__init__()
            self.uniqueIDs = {}
            self.defaultuniqueid = ''

        def setUniqueIDs(self, uniqueIDs: dict, defaultuniqueid: str = '') -> None:
            for key, value in uniqueIDs.items():
                self.uniqueIDs.update({key: value})
            self.defaultuniqueid = defaultuniqueid

        def getUniqueID(self,key) -> dict:
            return self.uniqueIDs[key]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.videoInfoTag = self.InfoTagVideo()
        self.label = kwargs.get('label', '')

    def getVideoInfoTag(self):
        return self.videoInfoTag

    def getLabel(self):
        return self.label
