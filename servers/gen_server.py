import sys
from icecap.base.env import Env
from icecap.base.util import importSymbol

env = Env()

setupFunc = importSymbol(sys.argv[1])
setupFunc(env)

env.serve()
