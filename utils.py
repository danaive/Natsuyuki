#!/usr/bin/env python

import os
from urlparse import urljoin

from requests import session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
domain = "http://seat.lib.whu.edu.cn/"


def read_account():
    with open(os.path.join(BASE_DIR, 'secret'), 'r') as f:
        user0, pass0 = f.readline().strip().split(':')
        user1, pass1 = f.readline().strip().split(':')
    return (user0, pass0), (user1, pass1)


def write_cookie(ck):
    with open(os.path.join(BASE_DIR, 'cookie'), 'w') as f:
        f.write(ck[0])
        f.write(ck[1])


def read_cookie():
    try:
        with open(os.path.join(BASE_DIR, 'cookie'), 'r') as f:
            ck0 = f.read(32)
            ck1 = f.read(32)
        return ck0, ck1
    except:
        return 'no file', 'or empty file'


def check_login(today):
    cookies = read_cookie()
    for ck in cookies:
        s = session()
        x = s.post(urljoin(domain, 'freeBook/ajaxGetTime'),
                   data = {'id': '3010', 'date': today},
                   cookies = {'JSESSIONID': ck})
        if 'login' in x.url:
            return False
    return True


def do_book(usr, idx, span, date):
    cookies = read_cookie()
    s = session()
    usr = int(usr)
    if usr == 2:
        for i, ck in enumerate(cookies):
            x = s.post(urljoin(domain, 'selfRes'),
                       cookies = {'JSESSIONID': ck},
                       data = {
                           'date': date,
                           'start': span[0],
                           'end': span[1],
                           'seat': idx[i]
                       })
            if '<span style="color:red">' not in x.content:
                return False
        return True
    else:
        for i in range(2):
            x = s.post(urljoin(domain, 'selfRes'),
                       cookies = {'JSESSIONID': cookies[usr]},
                       data = {
                           'date': date,
                           'start': span[0],
                           'end': span[1],
                           'seat': idx[i]
                       })
            if '<span style="color:red">' in x.content:
                return True
        return False
