#pylint: disable=missing-module-docstring, missing-class-docstring, missing-function-docstring,invalid-name
from unittest import mock
from unittest.mock import patch

import xbmcaddon
from resources.lib.channel import Channel, ChannelList, SavedChannelsList
from resources.lib.utils import SharedProperties
from tests_pytest.xbmcclasses import ListItem

# pytest_plugins = [
#    "tests_pytest.fixtures"
#   ]

class TestChannels:
    def test_channels(self, activewebsession):
        activewebsession.session.refresh_channels()
        activewebsession.session.refresh_entitlements()
        channels = activewebsession.session.get_channels()
        entitlements = activewebsession.session.get_entitlements()
        cl = ChannelList(channels, entitlements)
        clByLcn: list[Channel] = cl.channels_by_lcn()
        print(f'First={clByLcn[0].logicalChannelNumber}-{clByLcn[0].name}: {clByLcn[0].resolution}')
        print(f'Second={clByLcn[1].logicalChannelNumber}-{clByLcn[1].name}: {clByLcn[1].resolution}')

        clByname: list[Channel] = cl.channels_by_name()
        print(f'First={clByname[0].logicalChannelNumber}-{clByname[0].name}: {clByname[0].resolution}')
        print(f'Second={clByname[1].logicalChannelNumber}-{clByname[1].name}: {clByname[1].resolution}')

        cl.hiddenSuppressed = False
        cl.entitledOnly = False
        cl.apply_filter()
        for x in cl:
            c: Channel = x
            if c.isHidden:
                print('Hidden channel: {0}'.format(c.name))
            if not cl.is_entitled(c):
                print('Channel not entitled: {0}'.format(c.name))
        cl.hiddenSuppressed = True
        cl.hiddenSuppressed = cl.hiddenSuppressed
        cl.apply_filter()
        cl.entitledOnly = True
        cl.entitledOnly = cl.entitledOnly
        cl.apply_filter()
        for x in cl:
            c: Channel = x
            assert not c.isHidden, f'Channel {c.name} is hidden but hiddenSuppressed is True'
            assert cl.is_entitled(c), f'Channel {c.name} is not entitled but entitledOnly is True'
                
        url, assetType = clByLcn[0].get_locator(False)
        assert url is not None
        assert assetType is not None
        url, assetType = clByLcn[0].get_locator(True)
        assert url is not None
        assert assetType is not None

        print(clByLcn[0].streamInfo.externalStreamingProtocols)
                    
    @patch.object(Channel, '_get_isa_max_resolution')
    @patch.object(xbmcaddon.Addon, 'getSettingBool')
    def test_channel_exceptions(self, mocked_setting_bool, mocked_get_isa_max_resolution, activewebsession):
        activewebsession.session.refresh_channels()
        activewebsession.session.refresh_entitlements()
        channels = activewebsession.session.get_channels()
        assert len(channels) > 0, "No channels found, please make sure there are channels available for the test account"
        _ = activewebsession.session.get_entitlements()
        channel = channels[0]
        mocked_setting_bool.return_value = True
        mocked_get_isa_max_resolution.return_value = 'auto'
        _, assettype = channel.get_locator(True)
        assert assettype == 'Orion-DASH'
        _, assettype = channel.get_locator(disableFullHD=False)
        assert assettype == 'Orion-DASH-HEVC'
        channel.locators.pop('Orion-DASH-HEVC')
        _, assettype = channel.get_locator(disableFullHD=False)
        assert assettype == 'Orion-DASH'
        channel.locators.pop('Orion-DASH')
        with mock.patch.object(xbmcaddon.Addon,'getSetting', return_value=True) as mock_addon:
            val = xbmcaddon.Addon().getSetting('disableFullHD')
            print(f'Value of disableFullHD: {val}')
            mock_addon.assert_called_with('disableFullHD')

        with mock.patch.object(xbmcaddon.Addon,'getSettingBool', wraps=self.AddonGetSetting):
            val = xbmcaddon.Addon().getSettingBool('full-hd')
            print(f'Value of full-hd: {val}')
            channel = channels[1]
            channel.get_locator(disableFullHD=False)

    def AddonGetSetting(self, setting_name):
        print(f'AddonGetSetting called with: {setting_name}')
        if setting_name == 'full-hd':
            return 'auto'
        return None
    
    def test_channellist(self, activewebsession):
        activewebsession.session.refresh_channels()
        activewebsession.session.refresh_entitlements()
        channels = activewebsession.session.get_channels()
        entitlements = activewebsession.session.get_entitlements()

        cl = ChannelList(channels, entitlements)
        clByLcn: list[Channel] = cl.channels_by_lcn()
        assert len(clByLcn) > 0

        print('First={0}-{1}'.format(clByLcn[0].logicalChannelNumber, clByLcn[0].name))
        print('Second={0}-{1}'.format(clByLcn[1].logicalChannelNumber, clByLcn[1].name))
        cl.hiddenSuppressed = True
        cl.entitledOnly = True
        cl.apply_filter()
        _ = cl.supports_record()
        for channel in cl:
            c: Channel = channel
            if c.isHidden:
                print('Hidden channel: {0}'.format(c.name))
            if not cl.is_entitled(c) or not cl.is_playable(c):
                print('Channel not entitled or playable: {0}'.format(c.name))
            if not cl.supports_replay(channel):
                print('Channel does not support replay: {0}'.format(c.name))

        clByName: list[Channel] = cl.channels_by_name()
        assert len(clByName) > 0
        
        channel = cl.channels[0]
        found_channel = cl.find_channel_by_id(channel.id)
        assert found_channel is not None
        assert found_channel.id == channel.id
        found_channel = cl.find_channel_by_number(channel.logicalChannelNumber)
        assert found_channel is not None
        assert found_channel.logicalChannelNumber == channel.logicalChannelNumber
        found_channel = cl.find_channel_by_id('Unknown')
        assert found_channel is None
        found_channel = cl.find_channel_by_number(-1)
        assert found_channel is None

        for channel in cl:
            nextchannel = cl.get_next_channel(channel)
            assert nextchannel is not None

        for channel in cl:
            prevchannel = cl.get_prev_channel(channel)
            assert prevchannel is not None

    def test_savedchannellist(self, activewebsession, addon):
        activewebsession.session.refresh_channels()
        activewebsession.session.refresh_entitlements()
        channels = activewebsession.session.get_channels()
        entitlements = activewebsession.session.get_entitlements()

        cl = ChannelList(channels, entitlements)
        clByLcn: list[Channel] = cl.channels_by_lcn()
        assert len(clByLcn) > 0

        savedChannelsList = SavedChannelsList(addon)
        savedChannelsList.reload()
        savedChannelsList.add(clByLcn[0].id, clByLcn[0].name)
        savedChannelsList.add(clByLcn[1].id, clByLcn[1].name)
        savedChannelsList.save()
        assert len(savedChannelsList.get_all()) == 2
        
    def test_channel_sort(self, activewebsession):
        activewebsession.session.refresh_channels()
        activewebsession.session.refresh_entitlements()
        channels = activewebsession.session.get_channels()
        entitlements = activewebsession.session.get_entitlements()

        cl = ChannelList(channels, entitlements)
        listing = []
        for channel in cl:
            c: Channel = channel
            item = ListItem(label=c.name)
            item.getVideoInfoTag().setUniqueIDs(
                {'ziggochannelid': channel.id, 
                 'ziggochannelnumber': channel.logicalChannelNumber}, defaultuniqueid='ziggochannelnumber')
            listing.append(item)
            print(f'Channel {c.logicalChannelNumber} - {c.name}')
        cl.sort_listitems(listing, sortby=SharedProperties.TEXTID_NAME, sortorder=SharedProperties.TEXTID_ASCENDING)
        channel = cl.find_channel_by_listitem(listing[0])
        print(f'First channel after sorting by name: {channel.name}')
        cl.sort_listitems(listing, sortby=SharedProperties.TEXTID_NUMBER, sortorder=SharedProperties.TEXTID_ASCENDING)
        channel = cl.find_channel_by_listitem(listing[0])
        print(f'First channel after sorting by number: {channel.logicalChannelNumber}')
        cl.sort_listitems(listing, sortby=SharedProperties.TEXTID_NAME, sortorder=SharedProperties.TEXTID_DESCENDING)
        channel = cl.find_channel_by_listitem(listing[0])
        print(f'First channel after sorting by name: {channel.name}')
        cl.sort_listitems(listing, sortby=SharedProperties.TEXTID_NUMBER, sortorder=SharedProperties.TEXTID_DESCENDING)
        channel = cl.find_channel_by_listitem(listing[0])
        print(f'First channel after sorting by number: {channel.logicalChannelNumber}')
