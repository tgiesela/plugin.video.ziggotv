import xbmcgui
import xbmcaddon
from xbmcgui import Action, Control

from resources.lib.channel import ChannelList
from resources.lib.programevent import ProgramEventGrid
from resources.lib.utils import ProxyHelper, check_service
from resources.lib.webcalls import LoginSession
from resources.lib.windows.basewindow import BaseWindow

class EpgWindow(BaseWindow):
    # pylint: disable=too-many-instance-attributes
    """
    Class representing Epg Window defined in screen-epg.xml.
    Ids used in this file correspond to the .xml file
    """

    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, args[0], args[1])

    def __init__(self, xmlFilename: str, scriptPath: str, my_addon: xbmcaddon.Addon):
        super().__init__(xmlFilename, scriptPath)
        self.initDone = False
        self.grid: ProgramEventGrid = None
        self.currentFocusedNode = None
        self.epgDatetime = None  # date in local timezone
        self.epgEndDatetime = None  # last date in local timezone
        self.addon = my_addon
        self.helper = ProxyHelper(my_addon)
        self.channels = None
        self.__initialize_session()
        self.channelList = ChannelList(self.channels, self.entitlements)
        self.channelList.entitledOnly = my_addon.getSettingBool('allowed-channels-only')
        self.channelList.apply_filter()
        self.mediaFolder = self.addon.getAddonInfo('path') + 'resources/skins/Default/media/'

    # Private methods
    def __initialize_session(self):
        self.channels = self.helper.dynamic_call(LoginSession.get_channels)
        self.entitlements = self.helper.dynamic_call(LoginSession.get_entitlements)

    # Callbacks

    # pylint: disable=useless-parent-delegation
    def show(self) -> None:
        super().show()

    # pylint: enable=useless-parent-delegation

    def onControl(self, control: Control) -> None:
        self.grid.onControl(control)

    def onFocus(self, controlId: int) -> None:
        self.grid.onFocus(controlId)

    def onClick(self, controlId: int) -> None:
        super().onClick(controlId)
        self.grid.onClick(controlId)

    def onInit(self):
        if not self.initDone:
            self.grid = ProgramEventGrid(self,
                                            channels=self.channelList,
                                            mediaFolder=self.mediaFolder,
                                            addon=self.addon)
        self.grid.build()
        self.grid.show()
        self.initDone = True

    def onAction(self, action: Action) -> None:
        super().onAction(action)

        if self.grid.is_at_first_row():
            #  Set control to header to select date or back to grid
            if action.getId() == xbmcgui.ACTION_MOVE_UP:
                self.setFocusId(1010)
            elif (action.getId() == xbmcgui.ACTION_MOVE_DOWN and
                  self.getFocusId() in [1016, 1017, 1018, 1020]):
                self.grid.set_focus()
            elif (action.getId() in [xbmcgui.ACTION_MOVE_LEFT, xbmcgui.ACTION_MOVE_RIGHT] and
                  self.getFocusId() in [1016, 1017, 1018, 1020]):
                pass  # Action handled via .xml <onleft> <onright>
            else:
                self.grid.onAction(action)
        else:
            self.grid.onAction(action)

    def options_selected(self):
        """
        called when options were selected in the side window
        """
        self.onInit()

def load_epgwindow(addon:xbmcaddon.Addon):
    """
    Function to create, populate and display the epg form
    
    :param addon: the addon for which the form is created
    :type addon: xbmcaddon.Addon
    """
    # pylint: disable=import-outside-toplevel
    from resources.lib.utils import invoke_debugger
    invoke_debugger(False, 'vscode')
    check_service(addon)
    window = EpgWindow('screen-epg.xml', addon.getAddonInfo('path'), addon)
    window.doModal()

    # epgwindow = epgWindow('test-screen-epg.xml', CWD, defaultRes='1080i',addon=addon)
    # epgwindow.showepg()
    # epgwindow.doModal()