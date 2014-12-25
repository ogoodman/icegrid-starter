import os

def appRoot():
    """Returns the top-level application directory."""
    return os.path.abspath(__file__).rsplit('/', 4)[0]

def importSymbol(import_name):
    """Dynamically imports the specified object.

    :param import_name: the dotted import path
    """
    mod_name, symbol = import_name.rsplit('.', 1)
    module = __import__(mod_name, fromlist = [symbol])
    return getattr(module, symbol)
