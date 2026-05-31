"""
Test for singleton approach (may be an option for a future refactor)
"""
from resources.lib.videohelpers import VideoHelpers

class TestVideoPlayer:
    """
    Test class for singleton approach (may be an option for a future refactor)
    """
    def test_singleton(self, activewebsession):
        """
        The actual test
        
        :param self: 
        """

        player1 = VideoHelpers(activewebsession.addon)
        player2 = VideoHelpers(activewebsession.addon)

        assert player1 == player2
        assert player1.channels.channels[0].name == player2.channels.channels[0].name
