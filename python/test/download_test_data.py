import sys, os


if __name__ == '__main__':
    here = os.path.abspath('/'.join(__file__.split('/')[:-1]))
    if not here:
        here = '.'
    sys.path.insert(0, here)
    sys.path.insert(0, '%s/../src' % here)

    from protobuf import *
    import ydl
    import json
    import traceback

    urls = []
    for extractor in extractors:
        try:
            tests = extractor._TESTS
        except AttributeError:
            try:
                tests = [extractor._TEST]
            except AttributeError:
                continue
        for test in tests:
            if test and 'url' in test:
                urls.append((extractor, test['url']))

    import random
    import gevent
    from gevent import monkey
    from gevent.queue import Queue
    from gevent.pool import Pool

    random.shuffle(urls)

    monkey.patch_all()

    pool = Pool(20)


    outf = open('test_data.jsons', 'a+')

    for extractor, url in urls:
        extractor.set_downloader(ydl.downloader)

    def downloader((extractor, url)):
        print url
        with gevent.Timeout(120, False):
            try:
                res = extractor.extract(url)
            except:
                traceback.print_exc()
                return
            try:
                outf.write('%s\n' % json.dumps({
                    'url':url,
                    'extractor':extractor.IE_NAME,
                    'res':res
                }))
            except TypeError:
                for row in res:
                    outf.write('%s\n' % json.dumps({
                        'url':url,
                        'extractor':extractor.IE_NAME,
                        'res':row
                    }))

            outf.flush()

    for url in urls:
        pool.spawn(downloader, url)

    pool.join()
    outf.close()
