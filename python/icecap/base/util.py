import os

def appRoot():
    return os.path.abspath(__file__).rsplit('/', 4)[0]

