#!/usr/bin/env python

from requests import session
from datetime import datetime, timedelta
from pytz import timezone
from requests import session
from seats import *
from utils import *
import os, json, time


if __name__ == '__main__':
    try:
        task = json.load(open('task'))
    except:
        exit(0)
    tz = timezone('Asia/Shanghai')
    dt = datetime.now(tz)
    date = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    usr = '2' if task['2'] else '0' if task['0'] else '1'
    span = task[usr]['start'], task[usr]['end']
    tag = time.time()
    while True:
        for idx in favor:
            if do_book(usr, idx, span, date):
                tag = None
                break
        if not tag or time.time() - tag >= 360.0:
            break
