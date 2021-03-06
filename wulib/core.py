#!/usr/bin/env python
#

from itertools import filterfalse, chain, islice
import sys
import os
import fnmatch
import time
from random import randint
from collections import defaultdict, deque
from functools import reduce

# OS functions
def scriptdir(libdir, filedir=__file__):
    return os.path.join(os.path.dirname(os.path.realpath(filedir)), libdir)

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))

def ichunks(l, n):
    """Same as chunks, but works with itertables (no indexes). Doesn't support
    window keyword argument. You should figure out how so you can just have
    one function."""
    l = iter(l)
    chunk = take(n, l)
    while chunk != []:
        yield chunk
        chunk = take(n, l)

def chunks(l, n, slide=None):
    """Yield successive n-sized chunks from l with a sliding window of slide
    indexes. Default value of slide has non-overlapping chunks."""
    if slide is None: slide = n
    for i in range(0, len(l), slide):
        yield l[i:i+n]

# Helpful "itertools" functions
# see: http://docs.python.org/library/itertools.html
def unique(iterable, key=None):
    """List unique elements, preserving order. Remember all elements ever seen.

    unique_everseen('AAAABBBCCDAABBB') --> A B C D
    unique_everseen('ABBCcAD', str.lower) --> A B C D"""
    seen = set()
    seen_add = seen.add
    if key is None:
        for element in filterfalse(seen.__contains__, iterable):
            seen_add(element)
            yield element
    else:
        for element in iterable:
            k = key(element)
            if k not in seen:
                seen_add(k)
                yield element

def flatten(listoflists):
    return chain.from_iterable(listoflists)

def anyp(pred, iterable):
    """Python's any() is terrible."""
    for it in iterable:
        if pred(it):
            return it
    return False

# Filesystem functions
def rwalk(directory, pattern):
    """Recursively search "directory" for files that match the Unix shell-style
    wildcard given by "pattern" (like '*.mp3'). Returns matches as a generator."""
    for root, dirnames, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)

# Helper functions
def retry(function, args, exceptions, kwargs={}, times=-1, sleep=5, default=None, fixfun=lambda : None, moreinfo=''):
    """Repeatedly call a function until it succeeds.

    Required arguments:
    function -- function to call
    args -- arguments in a list for function
    exceptions -- tuple of exceptions to catch

    Keyword arguments:
    kwargs -- keyword arguments for function
    times -- number of times to repeat call (-1 means repeat indefinitely)
    sleep -- max time to sleep between repeated calls
    default -- value to return if function never succeeds
    fixfun -- function to call between failures (use side-effects to potentially fix the problem)

    Example:
    > def foo(x, y, bar=None):
    ...   if bar is not None: print(bar)
    ...   return x/y
    > baz = wulib.retry(foo, [4, 0], (ZeroDivisionError,), kwargs={'bar': 'calling foo'}, times=2, default='error')
    calling foo
    Calling foo failed, retrying...
    calling foo
    Calling foo failed, retrying...
    > baz
    'error'
    """
    while times != 0:
        try:
            times -= 1
            return function(*args, **kwargs)
        except exceptions:
            sys.stderr.write('Calling %s failed, retrying...\n' % function.__name__)
            if moreinfo != '':
                sys.stderr.write('\t%s\n' % moreinfo)
            time.sleep(randint(0, sleep))
            fixfun()

    return default

def inittorsocket(): import torsocket

def withtor(function, args=[], timer=60, exceptions=None):
    """Call function using args with Tor and renew the connection to Tor
    (change the exit node) every timer seconds. Alternatively, change the exit
    node when exceptions (tuple) is thrown."""
    sys.path.append(scriptdir('pylib'))
    from rtimer import RepeatTimer

    def restarttor():
        os.system('killall -HUP tor')
        time.sleep(10)

    if exceptions is None:
        r = RepeatTimer(timer, restarttor)
        r.start()
        try:
            function(*args)
        except KeyboardInterrupt:
            sys.stderr.write('User termination of %s\n' % function.__name__)
        finally:
            r.cancel()
    else:
        return retry(function, args, exceptions, fixfun=restarttor)

def ipythonshell(global_ns={}, local_ns={}, args=[], banner='Running in iPython subshell', exit_msg='Exiting subshell...'):
    from IPython.Shell import IPShellEmbed
    ipshell = IPShellEmbed(args, banner=banner, exit_msg=exit_msg)
    ipshell('*** C-d to exit interpreter and continue program.\n', global_ns=global_ns, local_ns=local_ns)

# Statistics

def frequency(iterable):
    from operator import itemgetter
    d = defaultdict(int)
    for item in iterable:
        d[item] += 1

    return sorted(iter(d.items()), key=itemgetter(1), reverse=True)

def meanwithconfidence(data, confidence=0.95):
    """Returns the mean of data with the confidence interval."""
    import scipy.stats
    from numpy import mean, array, sqrt
    a = 1.0 * array(data)
    n = len(a)
    m, se = mean(a), scipy.stats.sem(a)
    h = se * scipy.stats.t._ppf((1 + confidence) / 2., n - 1)
    return m, h

# Text munging
def fuckunicode(s):
    def isascii(c): return ord(c) < 128
    return list(filter(isascii, s))

# Configs
class ConfClass(object):
    """Taken from scapy.config. Subclass ConfClass to create the config for your
    project. Example:

    >>> class Test(ConfClass):
        version = "1.2"
        type = 3
        foo = "asdf"
        bar = [1, 2, 3]

    >>> conf = Test()
    >>> conf
    bar        = [1, 2, 3]
    foo        = 'asdf'
    random     = 'cool'
    type       = 3
    version    = '3.4'"""
    def configure(self, cnf):
        self.__dict__ = cnf.__dict__.copy()
    def __repr__(self):
        return str(self)
    def __str__(self):
        s=""
        keys = self.__class__.__dict__.copy()
        keys.update(self.__dict__)
        keys = list(keys.keys())
        keys.sort()
        for i in keys:
            if i[0] != "_":
                r = repr(getattr(self, i))
                r = " ".join(r.split())
                wlen = 76-max(len(i),10)
                if len(r) > wlen:
                    r = r[:wlen-3]+"..."
                s += "%-10s = %s\n" % (i, r)
        return s[:-1]

# Functional tools I miss
def compose(*funcs, **kfuncs):
    """Compose a group of functions (f(g(h(..)))) into (fogoh...)(...)"""
    return reduce(lambda f, g: lambda *args, **kaargs: f(g(*args, **kaargs)), funcs)
