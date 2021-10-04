from django.core.exceptions import ImproperlyConfigured

METHOD_NOT_FOUND = "METHOD_NOT_FOUND"


def executeMethod(obj, method_name, **kwargs):
    handler = getattr(obj, method_name, METHOD_NOT_FOUND)
    if handler == METHOD_NOT_FOUND:
        raise ImproperlyConfigured("Method named '%s'not found in class '%s'." % (method_name, type(obj).__name__))
    return handler(**kwargs)


def getMethodHandler(obj, method_name):
    handler = getattr(obj, method_name, METHOD_NOT_FOUND)
    if handler == METHOD_NOT_FOUND:
        return False, None
    return True, handler


def isMethodExist(obj, method_name):
    handler = getattr(obj, method_name, METHOD_NOT_FOUND)
    if handler == METHOD_NOT_FOUND:
        return False
    return True
