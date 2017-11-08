#!/usr/bin/env python2.7


if __name__ == '__main__':
    import os
    from os.path import join
    import py_compile

    dirname = "org_schabi_newpipe_extractor_PyBridge"

    here = '/'.join(__file__.split('/')[:-1])

    asset_dir = '%s/../assets' % here

    for f in os.listdir('%s/%s' % (asset_dir, dirname)):
        os.unlink('%s/%s/%s' % (asset_dir, dirname, f))
    src_dirnames = ['%s/src' % here, '%/stdlib' % here]
    for src_dirname in src_dirnames:
        for root, dirs, files in os.walk(src_dirname, followlinks=True):
            for f in files:
                if not f.endswith('.py'):
                    continue
                fname = join(root, f)
                basename = f.split('.')[0]
                keyname = root[len(src_dirname):].replace('/', '_')
                if keyname:
                    keyname = '%s_' % keyname
                apkname = '%s%s.pyc' % (keyname, basename)
                py_compile.compile(
                        fname,
                        '%s/%s' % (asset_dir, apkname),
                        fname,
                        True)
