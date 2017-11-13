from youtube_dl.downloader.common import FileDownloader
from youtube_dl.YoutubeDL import YoutubeDL
from contextlib import contextmanager

ydl = YoutubeDL(auto_init=False)

class Downloader(FileDownloader):

    params = {}

    def __init__(self):
        self.ydl = ydl
        self.urlopen = self.ydl.urlopen

    def to_screen(self, message, skip_eol=False):
        print message

    def to_stderr(self, message):
        print message

    def to_console_title(self, message):
        print message

    def trouble(self, message=None, tb=None):
        if message:
            print message

    def report_warning(self, message):
        print message

    def report_error(self, message, tb=None):
        print message

@contextmanager
def login_context(username, password):
    if username is not None and password is not None:
        old_username = Downloader.params.get('username')
        old_password = Downloader.params.get('password')

        Downloader.params['username'] = username
        Downloader.params['password'] = password

        yield

        Downloader.params['username'] = old_username
        Downloader.params['password'] = old_password
    else:
        yield


downloader = Downloader()
