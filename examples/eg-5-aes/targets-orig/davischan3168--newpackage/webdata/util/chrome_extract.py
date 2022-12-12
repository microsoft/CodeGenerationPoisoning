#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2012 Jordan Wright <jordan-wright.github.io>
# Copyright (c) 2014-2015 Rasmus Sorensen <scholer.github.io> rasmusscholer@gmail.com

##    This program is free software: you can redistribute it and/or modify
##    it under the terms of the GNU General Public License as published by
##    the Free Software Foundation, either version 3 of the License, or
##    (at your option) any later version.
##
##    This program is distributed in the hope that it will be useful,
##    but WITHOUT ANY WARRANTY; without even the implied warranty of
##    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##    GNU General Public License for more details.
##
##    You should have received a copy of the GNU General Public License

"""
Get chrome cookies from chrome's database on Windows.

This library is based on code from https://github.com/scholer/Mediawiker.

References and other projects:
* https://gist.github.com/jordan-wright/5770442
* https://github.com/jdallien/cookie_extractor
* Search github for "cookie" and "fetch" or "extract" or "hijack" or ...

Platform-specific implementations:
* Windows:      Uses win32crypt module.
* OSX/Linux:    Uses AES decryption. OS X additionally uses keyring module.

OS X and Linux implementations are based on code from pyCookieCheat.py.


"""

from __future__ import print_function
import os
import sys
import warnings
import tempfile
import sqlite3

#cookieshopdir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
#libdir = os.path.dirname(cookieshopdir)

try:
    from urllib.parse import urlparse
except ImportError:
    # python 2:
    from urlparse import urlparse

# Windows decryption.
if sys.platform == 'win32':
    import win32crypt
elif sys.platform in ('linux', 'darwin'):
    from Crypto.Cipher import AES
    from Crypto.Protocol.KDF import PBKDF2



## ENCRYPTION CONSTANTS ##
crypt_iv = b' ' * 16
# Queries:
logins_query = 'SELECT action_url, username_value, password_value FROM logins'


## SQLITE DATABASE FILE PATHS: ##

# If running Chrome on OSX
if sys.platform == 'darwin':
    cookies_dbpath = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Cookies')
    logins_dbpath = os.path.expanduser('~/Library/Application Support/Google/Chrome/Default/Login Data')
# If running Chromium on Linux
elif sys.platform == 'linux':
    cookies_dbpath = os.path.expanduser('~/.config/chromium/Default/Cookies')
    logins_dbpath = os.path.expanduser('~/.config/chromium/Default/Login Data')
elif sys.platform == 'win32':
    chrome_appdata = os.path.abspath(os.path.join(os.getenv("APPDATA"), r"..\Local\Google\Chrome\User Data\Default"))
    cookies_dbpath = os.path.join(chrome_appdata, "Cookies")
    logins_dbpath = os.path.join(chrome_appdata, "Login Data")
else:
    raise RuntimeError("This module only supports Windows, OS X and Linux.")



def cookie_query_for_domain(url):
    """
    Create sql query to find cookies for a particular domain given a url of the format
        https://lab.wyss.harvard.edu/shih/RasmusProjects
    """
    # Part of the domain name that will help the sqlite3 query pick it from the Chrome cookies
    domain = urlparse(url).netloc
    # If url is just a domain, e.g. lab.wyss.harvard.edu, then urlparse doesn't work:
    if not domain:
        #print("Given URL doesn't seem to have a schema. Parsing domain as '%s' instead." % domain)
        domain = url.split('/')[0]
    sql = 'select name, value, encrypted_value from cookies where host_key like "%{}%"'.format(domain)
    return sql


##  DECRYPTION ##
def make_chrome_cryptkey():
    """ Make a platform-dependent encryption (decryption) key for Chrome. """
    salt = b'saltysalt'
    length = 16

    if sys.platform == 'win32':
        # Windows doesn't really use an encryption key...
        return None

    # If running Chrome on OSX
    if sys.platform == 'darwin':
        my_pass = keyring.get_password('Chrome Safe Storage', 'Chrome')
        my_pass = my_pass.encode('utf8') # Ensure bytearray
        iterations = 1003
    # If running Chromium on Linux
    elif sys.platform == 'linux':
        my_pass = 'peanuts'.encode('utf8')
        iterations = 1
    else:
        raise RuntimeError("This script only works on OSX or Linux.")

    # Generate key from values above
    # All inputs should be bytearrays or integers.
    key = PBKDF2(my_pass, salt, length, iterations)
    return key


def chrome_decrypt(encrypted_value, key=None):
    """
    Decrypt value using Chrome's platform-dependent symmetric encryption scheme using key.
    encrypted_value should be a byte string, otherwise you'll probably get a
    TypeError: expected an object with a buffer interface
    """
    # For windows, chrome just uses
    if sys.platform == 'win32':
        # CryptUnprotectData returns a two-string tuple. Not sure what the first value is...
        # This is more obfucation, so might change at some point...
        _, decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)
        return decrypted.decode('utf-8')

    # Encrypted cookies should be prefixed with 'v10' according to the Chromium code. Strip it off.
    # (Only for OSX/Linux, c.f. <chromium code base>//src/components/os_crypt/os_crypt_mac.mm)
    encryption_scheme_version, encrypted_value = encrypted_value[:3], encrypted_value[3:]

    # Strip padding by taking off number indicated by padding
    # eg if last is '\x0e' then ord('\x0e') == 14, so take off 14.
    # You'll need to change this function to use ord() for python2.
    def clean(x):
        """ Remove padding and decode to utf8 """
        return x[:-x[-1]].decode('utf8')

    cipher = AES.new(key, AES.MODE_CBC, IV=crypt_iv)
    decrypted = cipher.decrypt(encrypted_value)
    return clean(decrypted)



def query_db(dbpath, query):
    """
    Connects to database in dbpath, queries with query
    and returns all matching rows as a list by calling fetchall()
    (I believe the returned values are byte strings, at least in some cases...)
    """
    # Connect to the Database
    try:
        with sqlite3.connect(dbpath) as conn:
            # Get the results
            cursor = conn.execute(query)
            res = cursor.fetchall()
            del cursor
    except sqlite3.OperationalError:
        # This can happen if the sqlite database file is locked.
        # Try to make a temporary copy and use that.
        try:
            tempdir = tempfile.TemporaryDirectory()
        except AttributeError:
            tempdir = tempfile.mkdtemp()
        tempdbpath = os.path.join(tempdir, os.path.basename(dbpath))
        import shutil
        # Copy db to temp file:
        shutil.copy(dbpath, tempdbpath)
        # Try once again to connect to chrome database:
        with sqlite3.connect(tempdbpath) as conn:
            cursor = conn.execute(query)
            res = cursor.fetchall()
            del cursor
        try:
            os.remove(tempdbpath)
            try:
                tempdir.cleanup()
            except AttributeError:
                shutil.rmtree(tempdir)
        except WindowsError as e:
            print(e)
    return res


def query_cookies_db(query):
    """ Convenience function... """
    return query_db(cookies_dbpath, query)


def get_chrome_logins():
    """
    Returns list of dict with site, username, password.
    """
    rows = query_db(logins_dbpath, logins_query)
    rowdicts = [{'site': result[0], 'username': result[1], 'password': win32crypt.CryptUnprotectData(result[2], None, None, None, 0)[1]}]
    return rowdicts


def print_logins():
    rows = query_db(logins_dbpath, logins_query)
    for result in rows:
        # Decrypt the Password
        # CryptUnprotectData(optionalEntropy, reserved , promptStruct , flags )
        password = win32crypt.CryptUnprotectData(result[2], None, None, None, 0)[1]
        if password:
            print("---")
            print("Site: %s\nUsername: %s\nPass: %s" % (result[0], result[1], len(password)))



def get_chrome_cookies(url, filter=None):
    """
    Returns all chrome's cookies for url (or domain) <url>,
    as a dict {cookie_name : value},
    making sure that value is decrypted (if stored as encrypted).
    Optional arg <filter>, if given, is a function that filters the result,
    including only cookies where filter(cookie_name) is True.
    Usage:
        >>> get_chrome_cookies('lab.wyss.harvard.edu', filter=lambda k: 'session_id' in k)
    """
    key = make_chrome_cryptkey() # Encryption key (is None for Windows)
    query = cookie_query_for_domain(url)
    # SQL query returns rows with: name, value, encrypted_value
    # Gets the full results list and closes db connection
    # Returns a list of key, value, encrypted_value, where key is cookie name.
    cookie_entries = query_db(cookies_dbpath, query)
    if filter:
        cookie_entries = [(k, v, ev) for k, v, ev in cookie_entries if filter(k)]
    # Decrypting cookies: Make sure *all* inputs are bytearrays, including key:
    cookies_dict = {k: chrome_decrypt(ev, key=key) if ev else v for k, v, ev in cookie_entries}
    return cookies_dict



def main():
    if sys.argv:
        print(get_chrome_cookies(sys.argv[1]))
    else:
        print_logins()


if __name__ == '__main__':
    main()
