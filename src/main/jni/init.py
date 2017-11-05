
if __name__ == '__main__':
    with open('monkeypatches.py', 'r') as inf:
        patches = inf.read()
    string_literal = patches.replace('\n', '\\n')
    with open('python_monkeypatches.h', 'w') as outf:
        outf.write('const char *python_monkeypatches = "%s";' % string_literal)
