import inspect

def file_len(fname):
    with open(fname) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

def decallmethods(decorator, prefix='test_'):
    """
    decorates all methods in class which begin with prefix test_ to prevent
    accidental external HTTP requests.
    """
    def dectheclass(cls):
        for name, m in inspect.getmembers(cls, inspect.ismethod):
            if name.startswith(prefix):
                setattr(cls, name, decorator(m))

        return cls
    return dectheclass


