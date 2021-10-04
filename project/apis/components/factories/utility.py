
'''
You can use this class  your class to create Singleton class:
	class ProducerQueue(object):
    	__metaclass__ = SingletonBaseClass
    	....
    	....
'''

class SingletonBaseClass(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonBaseClass, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
'''
class SingletonBaseClass(type):
    def __init__(cls, name, bases, attrs, **kwargs):
        super().__init__(name, bases, attrs)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__call__(*args, **kwargs)
        return cls._instance


    # _instances = {}
    # def __call__(cls, *args, **kwargs):
    #     if cls not in cls._instances:
    #         cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
    #     return cls._instances[cls]
    
'''