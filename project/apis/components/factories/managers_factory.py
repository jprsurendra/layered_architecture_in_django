from apis.components.base.base_manager import BaseModelManager
from apis.components.factories.utility import SingletonBaseClass


class ManagersFactory(metaclass=SingletonBaseClass):
    # __metaclass__ = SingletonBaseClass

    self_obj = None

    def __init__(self):
        self.managers_dic = {}
        self.manager_type = "FILE"

    @staticmethod
    def get_instance():
        """ Static access method. """
        if ManagersFactory.self_obj is None:
            ManagersFactory.self_obj = ManagersFactory()
        return ManagersFactory.self_obj

    @staticmethod
    def register(objManager, managerName=None):
        instance = ManagersFactory.get_instance()

        if managerName == None:
            handler = getattr(objManager, "get_manager_name", "MethodNotFound")
            if handler == "MethodNotFound":
                raise NotImplementedError("Method 'get_manager_name' not found.")
            managerName = handler()

        managerName_upper = managerName.upper()

        if not managerName_upper in instance.managers_dic:
            instance.managers_dic[managerName_upper] = objManager

    def get_manager(self, managerName):
        managerName_upper = managerName.upper()
        if not managerName_upper in self.managers_dic:
            raise NotImplemented()
        #     raise Exception('Getter for "%s" Not Implemented in ManagersFactory'%(managerName))
        return self.managers_dic[managerName_upper]

    get_manager.__annotations__ = {'return': BaseModelManager}

    # Register all Managers to this Factory
    def register_all_managers(self):
        from apis.common.managers import CommonManager
        common_manager = CommonManager()
        self.register(common_manager, CommonManager.get_manager_name())

    def get_common_manager(self):
        from apis.common.managers import CommonManager
        manager = self.get_manager(CommonManager.get_manager_name())
        return manager
