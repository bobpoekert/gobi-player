#!/usr/bin/env python2.7
import os
from os.path import join
import py_compile
import struct
import imp
import subprocess

def is_unchanged(source_path, bytecode_path):
    if not os.path.exists(bytecode_path):
        return False
    mtime = int(os.stat(source_path).st_mtime)
    expect = struct.pack('<4sl', imp.get_magic(), mtime)
    cfile = bytecode_path
    with open(cfile, 'rb') as chandle:
        actual = chandle.read(8)
    return expect == actual

if __name__ == '__main__':

    dirname = "cheap_hella_gobi_PyBridge"

    here = '/'.join(__file__.split('/')[:-1])

    asset_dir = '%s/../src/main/assets/%s' % (here, dirname)


    if not os.path.exists(asset_dir):
        subprocess.call(['mkdir', '-p', asset_dir])

    src_dirnames = ['%s/src' % here, '%s/stdlib' % here]
    for src_dirname in src_dirnames:
        for root, dirs, files in os.walk(src_dirname, followlinks=True):
            if 'site-packages' in root or 'tests' in root:
                continue
            for f in files:
                if not f.endswith('.py'):
                    continue
                fname = join(root, f)
                basename = f.split('.')[0]
                keyname = root[len(src_dirname):]
                if keyname:
                    if keyname[0] == '/':
                        keyname = keyname[1:]
                    keyname = keyname.replace('/', '_')
                    keyname = '%s_' % keyname
                apkname = '%s%s.pyc' % (keyname, basename)
                apk_full = '%s/%s' % (asset_dir, apkname)
                if not is_unchanged(fname, apk_full):
                    py_compile.compile(
                            fname,
                            apk_full,
                            fname,
                            True)
