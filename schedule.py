#!/usr/bin/env python

import json
import os
import time
from datetime import datetime, timedelta

from pytz import timezone
from requests import session

from seats import *
from utils import *

if __name__ == '__main__':
    try:
        task = json.load(open('task'))
        assert task['0'] or task['1'] or task['2']
    except:
        print 'Load json failed.'
        exit(0)
    tz = timezone('Asia/Shanghai')
    dt = datetime.now(tz)
    date = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    for key in ('0', '1', '2'):
        if task[key]:
            usr = key
    span = task[usr]['start'], task[usr]['end']
    tag = time.time()
    print 'Start booking...'
    while True:
        for idx in favor:
            print 'booking seat %s at %s' % (idx, datetime.now(tz).strftime('%H:%M:%S'))
            if do_book(usr, idx, span, date):
                tag = None
                print 'success'
                break
        if not tag or time.time() - tag >= 360.0:
            break

    task[usr] = None for usr in ('0', '1', '2')
    json.dump(task, open('task'))
