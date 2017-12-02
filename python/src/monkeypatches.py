# No imports of code that isn't in androidbridge or libpython27.so allowed until noted
import androidbridge
import sys
import marshal
import imp

ModuleType = type(sys)

dirname = "cheap_hella_gobi_PyBridge"

def load_bytecode(fname):
    return marshal.loads(androidbridge.load_asset('%s/%s' % (dirname, fname))[8:])

lib_path = androidbridge.lib_path()

for modulename in ['_ctypes', '_socket', '_sqlite3', 'select', 'pyexpat', 'unicodedata']:
    fullpath = '%s/lib%s.so' % (lib_path, modulename)
    androidbridge.log(fullpath)
    try:
        imp.load_dynamic(modulename, fullpath)
    except Exception, e:
        androidbridge.log(str(type(e)))
        androidbridge.log(str(e))

class ModuleLoader(object):

    def __init__(self):
        self.fnames = androidbridge.asset_filenames()

    def generate_fname(self, fullname, path=None):
        base = fullname.replace('.', '_')
        mod = '%s.pyc' % base
        print fullname, path, mod
        if mod in self.fnames:
            return mod
        pkg = '%s___init__.pyc' % base
        if pkg in self.fnames:
            return pkg
        return None

    def find_module(self, fullname, path=None):
        fname = self.generate_fname(fullname, path)
        if fname is None:
            return None
        else:
            return self

    def load_module(self, name):
        if name in sys.modules:
            return sys.modules[name]
        fname = self.generate_fname(name)
        if fname is None:
            raise ImportError('file does not exist')
        try:
            data = load_bytecode(fname)
        except:
            raise ImportError('failed to load file')
        mod = sys.modules.setdefault(name, ModuleType(name))
        mod.__file__ = '/android_asset/%s/%s' % (dirname, fname)
        mod.__loader__ = self
        if fname.endswith('__init__.pyc'):
            mod.__path__ = []
            mod.__package__ = name
        else:
            mod.__package__ = name.rpartition('.')[0]
        exec(data, mod.__dict__)
        return mod

    def get_data(self, path):
        try:
            return androidbridge.load_asset(str(path))
        except:
            raise IOError()

sys.meta_path = [ModuleLoader()]

import os
for f in os.listdir(lib_path):
    androidbridge.log(f)

# we get 'LookupError: no codec search functions registered: can't find encoding' if we don't do this
import encodings

# Normal imports allowed after this point

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
        if self.buffer:
            androidbridge.log(self.buffer)
        self.buffer = ''

logger = AndroidLogFile()
sys.stdout = logger
sys.stderr = logger

import bootstrap
bootsrap.run()
