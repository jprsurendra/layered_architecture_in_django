import traceback
import logging
import requests

from django.conf import settings

from apis.components.base.base_manager import BaseModelManager
from apis.components.factories.utility import SingletonBaseClass


class CommonManager(BaseModelManager, metaclass = SingletonBaseClass):
    # __metaclass__ = SingletonBaseClass

    def __init__(self):
        super(CommonManager, self).__init__(None, None)

    @staticmethod
    def get_manager_name():
        return "CommonManager"


    # def retrieve_currency(self, id_value=None, **kwargs):
    #     self.Model = Currency
    #     if id_value:
    #         obj = self.Model.objects.filter(id=id_value)
    #         return obj[0] if obj else None
    #     else:
    #         obj = self.Model.objects.get(**kwargs)
    #         return obj


class SystemSettingsManager(BaseModelManager, metaclass = SingletonBaseClass):
    # __metaclass__ = SingletonBaseClass

    def __init__(self):
        super(SystemSettingsManager, self).__init__('common', "GenericSystemSettings")

    @staticmethod
    def get_manager_name():
        return "SystemSettingsManager"

    def refresh_system_settings(self, params=None, **kwargs):
        lst = self.list(params=params, **kwargs)
        if lst and lst.get('count',0)>0:
            for item in lst['data']:
                prop_value = item.prop_value
                prop_type = item.prop_type
                if prop_type and prop_type.upper() == 'EMAIL' and "," in prop_value:
                    prop_value = prop_value.split(",")
                    prop_value = [x.strip() for x in prop_value if x]
                else:
                    prop_value = prop_value.strip()
                setattr(settings, item.prop_key, prop_value)
        return lst

