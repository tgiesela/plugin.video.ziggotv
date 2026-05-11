import datetime
import json
import os
import xbmcaddon
import xbmcvfs
from resources.lib import utils

class BaseSavedStateList:
    """
    class to keep the state of played recording. This is used to resume a recording at the point where
    playback was stopped the last time
    """
    def __init__(self, addon: xbmcaddon.Addon, fileName: str):
        self.addon = addon
        self.addonPath = xbmcvfs.translatePath(self.addon.getAddonInfo('profile'))
        self.fileName = self.addonPath + fileName
        self.states = {}
        targetdir = os.path.dirname(self.fileName)
        if targetdir == '':
            targetdir = os.getcwd()
        if not os.path.exists(targetdir):
            os.makedirs(targetdir)
        if not os.path.exists(self.fileName):
            with open(self.fileName, 'w', encoding='utf-8') as file:
                json.dump(self.states, file)
        self.__load()

    def __load(self):
        with open(self.fileName, 'r+', encoding='utf-8') as file:
            self.states = json.load(file)
        for item in self.states:
            if 'datePlayed' in self.states[item]:
                self.states[item].update({'dateAdded': self.states[item]['datePlayed']})
                del self.states[item]['datePlayed']

    def save(self):
        """
        function to save the states to disk
        @return:
        """
        with open(self.fileName, 'w', encoding='utf-8') as file:
            json.dump(self.states, file)

    def delete(self, itemId):
        """
        function to delete the recording from the state list
        @param itemId:
        @return:
        """
        if itemId in self.states:
            self.states.pop(itemId)

    def get(self, itemId):
        """
       function to find a recording by its id
       @param itemId:
       @return:
        """
        for item in self.states:
            if item == itemId:
                return self.states[item]
        return None

    def cleanup(self, daysToKeep=365, itemsToKeep=0):
        """
        function to clean up saved channels
        @param daysToKeep: 
        @return: 
        """
        expDate = datetime.datetime.now() - datetime.timedelta(days=daysToKeep)
        sortedStates = dict(sorted(self.states.items(), key=lambda x: x[1]['dateAdded'], reverse=True))
        itemsKept = 0
        for item in list(sortedStates):
            if sortedStates[item]['dateAdded'] < utils.DatetimeHelper.unix_datetime(expDate):
                if itemsKept < itemsToKeep:
                    itemsKept += 1
                else:
                    self.delete(item)
        self.save()

    def reload(self):
        """
        function to reload the saved states from file
        @return:
        """
        self.__load()
