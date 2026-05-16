"""
Test for singleton approach (may be an option for a future refactor)
"""
from resources.lib.videohelpers import VideoHelpers
from tests.test_base import TestBase

class TestVideoPlayer(TestBase):
    """
    Test class for singleton approach (may be an option for a future refactor)
    """
    def test_singleton(self):
        """
        The actual test
        
        :param self: 
        """

        player1 = VideoHelpers(self.addon)
        player2 = VideoHelpers(self.addon)

        self.assertIs(player1, player2)
        self.assertIs(player1.channels.channels[0].name, player2.channels.channels[0].name)
