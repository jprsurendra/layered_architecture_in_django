from apis.common.models import GenericSystemSettings
from django.conf import settings

class GenericConfiguration:
    __instance = None

    def __init__(self):
        """ Virtually private constructor. """
        if GenericConfiguration.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            self.system_settings_dict = dict(GenericSystemSettings.objects.values_list('prop_key', 'prop_value'))
            GenericConfiguration.__instance = self


    @staticmethod
    def get_instance():
        """ Static access method. """
        if GenericConfiguration.__instance == None:
            GenericConfiguration()
        return GenericConfiguration.__instance

    def refresh_system_settings_dict(self):
        self.system_settings_dict = dict(GenericSystemSettings.objects.values_list('prop_key', 'prop_value'))

    def fetch_value(self, key):
         if key in self.system_settings_dict:
             return self.system_settings_dict[key]
         return eval('settings.'+ key)