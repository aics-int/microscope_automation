'''
Created on Jun 8, 2017

@author: https://stackoverflow.com/questions/3214245/lines-of-code-in-eclipse-pydev-projects
'''
# prints recursive count of lines of python source code from current directory
# includes an ignore_list. also prints total sloc

import os
cur_path = os.getcwd()
ignore_set = set(["__init__.py", "count_sourcelines.py"])

loclist = []

for pydir, _, pyfiles in os.walk(cur_path):
    for pyfile in pyfiles:
        if pyfile.endswith(".py") or pyfile.endswith(".yml") and pyfile not in ignore_set:
            totalpath = os.path.join(pydir, pyfile)
            loclist.append( ( len(open(totalpath, "r").read().splitlines()),
                               totalpath.split(cur_path)[1]) )

for linenumbercount, filename in loclist: 
    print("%05d lines in %s" % (linenumbercount, filename))

print("\nTotal: %s lines (%s)" %(sum([x[0] for x in loclist]), cur_path))