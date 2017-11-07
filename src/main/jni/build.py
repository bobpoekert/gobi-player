#!/usr/bin/env python2.7


if __name__ == '__main__':
    import os
    from os.path import join
    import py_compile

    dirname = "org_schabi_newpipe_extractor_PyBridge"

    with open('monkeypatches.py', 'r') as inf:
        patches = inf.read()
    string_literal = patches.replace('\n', '\\n')
    with open('python_monkeypatches.h', 'w') as outf:
        outf.write('const char *python_monkeypatches = "%s";' % string_literal)

    for f in os.listdir('../assets/%s' % dirname):
        os.unlink('../assets/%s/%s' % (dirname, f))
    src_dirnames = ['../../../python/', '../../../python_stdlib/']
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
                        '../assets/%s/%s' % (dirname, apkname),
                        fname,
                        True)
