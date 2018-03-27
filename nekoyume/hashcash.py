#!/usr/bin/env python3.6
"""Implement Hashcash version 1 protocol in Python 3.6
+---------------------------------------------------------------------------+
| Written by David Mertz; Modified by Jc Kim; released to the Public Domain |
+---------------------------------------------------------------------------+

Double spend database not implemented in this module, but stub
for callbacks is provided in the 'check()' function

The function 'check()' will validate 'generalized hashcash' tokens
generically.  Future protocol version are treated as generalized tokens
(should a future version be published w/o this module being correspondingly
updated).

A 'generalized hashcash' is implemented in the '_mint()' function, with the
public function 'mint()' providing a wrapper for actual hashcash protocol.
The generalized form simply finds a suffix that creates zero bits in the
hash of the string concatenating 'challenge' and 'suffix' without specifying
any particular fields or delimiters in 'challenge'.  E.g., you might get:

    >>> from hashcash import _mint
    >>> _mint('foo', bits=16)
    '1369a'
    >>> from hashlib import sha256
    >>> sha256(b'foo1369a').hexdigest()
    '0000ac007db1be2dcb5e1fb94685c64976c8485931a44b8546d3034ad853555f'
    >>> sha256(b'1:16:180130:foo::QiTuo+Vq:19556').hexdigest()
    '00002d016664c69bda0fe9730f058fa8b5ef508fc8078253e07948c769d4642a'

Notice that '_mint()' behaves deterministically, finding the same suffix
every time it is passed the same arguments.  'mint()' incorporates a random
salt in stamps (as per the hashcash v.1 protocol).
"""
from math import ceil, floor
from hashlib import sha256


tries = [0]                 # Count hashes performed for benchmark


def _mint(challenge, bits):
    """Answer a 'generalized hashcash' challenge'

    Hashcash requires stamps of form 'ver:bits:date:res:ext:rand:counter'
    This internal function accepts a generalized prefix 'challenge',
    and returns only a suffix that produces the requested SHA leading zeros.

    NOTE: Number of requested bits is rounded up to the nearest multiple of 4
    """
    counter = 0
    hex_digits = int(ceil(bits/4.))
    zeros = '0'*hex_digits
    while 1:
        digest = sha256(str.encode(challenge+hex(counter)[2:])).hexdigest()
        if digest[:hex_digits] == zeros:
            tries[0] = counter
            return hex(counter)[2:]
        counter += 1


def check(stamp, resource=None, bits=None,
          check_expiration=None, ds_callback=None):
    if type(bits) is not int:
        return True
    elif resource is not None and stamp.find(resource) < 0:
        return False
    else:
        hex_digits = int(floor(bits/4))
        return sha256(str.encode(stamp)).hexdigest().startswith(
            '0'*hex_digits)
