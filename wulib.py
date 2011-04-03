#!/usr/bin/env python
#

from itertools import ifilterfalse, chain
import sys
import os
import fnmatch
import time
from random import randint

sys.path.append('pylib')
from rtimer import RepeatTimer

def chunks(l, n):
    """ Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
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
        for element in ifilterfalse(seen.__contains__, iterable):
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

# Filesystem functions
def rwalk(directory, pattern):
    """Recursively search "directory" for files that match the Unix shell-style
    wildcard given by "pattern" (like '*.mp3'). Returns matches as a generator."""
    for root, dirnames, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            yield os.path.join(root, filename)

# Helper functions
def retry(function, args, exceptions, kwargs={}, times=-1, sleep=5, default=None, fixfun=lambda : None):
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
            time.sleep(randint(0, sleep))
            fixfun()

    return default

def inittorsocket(): import torsocket

def withtor(function, args=[], timer=60, exceptions=None):
    """Call function using args with Tor and renew the connection to Tor
    (change the exit node) every timer seconds. Alternatively, change the exit
    node when exceptions (tuple) is thrown."""
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
