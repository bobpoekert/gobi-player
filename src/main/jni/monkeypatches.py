import sys
import androidbridge

class AndroidLogFile(object):

    def __init__(self):
        self.buffer = ''

    def write(self, s):
        self.buffer += s
        lines = self.buffer.split('\n')
        for line in lines[:-1]:
            androidbridge.log(line)
        self.buffer = lines[-1]

    def flush(self):
        return

logger = AndroidLogFile()
sys.stdout = logger
sys.stderr = logger

class ModuleLoader(object):

    def __init__(self):
        return

    def find_module(self, fullname, path=None):
        return

    def load_module(self, name):
        return

    def get_data(self, path):
        return androidbridge.load_asset(str(path))

sys.meta_path = [ModuleLoader()]
