#!/usr/bin/env python2

from flask import Flask, render_template, redirect, url_for, request, jsonify
from datetime import datetime, timedelta
from pytz import timezone
from requests import session
from urlparse import urljoin
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
import os


app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
domain = "http://seat.lib.whu.edu.cn/"
seats = (((3091, 3092), (99, 100)),
         ((3093, 3094), (101, 102)),
         ((3096, 3097), (103, 104)),
         ((3098, 3099), (105, 106)),
         ((3100, 3101), (107, 108)),
         ((3105, 3106), (109, 110)),
         ((2575, 2574), (13, 14)),
         ((2572, 2571), (15, 16)),
         ((2569, 3089), (17, 18)))


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
    print 'done'
    return True


@app.route('/')
def index():
    tz = timezone('Asia/Shanghai')
    dt = datetime.now(tz)
    if not check_login(dt.strftime('%Y-%m-%d')):
        return redirect(url_for('login'))
    opts = range(8 * 60 + 30, 22 * 60, 30)
    if dt.hour * 60 + dt.minute >= 22 * 60 + 30:
        date = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        now = dt.hour * 60 + dt.minute
        opts = filter(lambda x: x >= now, opts)
        date = dt.strftime('%Y-%m-%d')
    return render_template('index.html', date=date, opts=opts)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        cookies = []
        imgs = []
        for i in range(2):
            c = session().get(urljoin(domain, 'simpleCaptcha/captcha'))
            cookies.append(c.cookies['JSESSIONID'])
            captcha = Image.open(BytesIO(c.content)).resize((120, 50))
            imgs.append(os.urandom(6).encode('hex'))
            captcha.save(os.path.join(BASE_DIR, 'static/img/%s.jpg' % imgs[-1]))
        write_cookie(cookies)
        return render_template('login.html', imgs=imgs)
    else:
        # map(os.remove, os.listdir(os.path.join(BASE_DIR, 'static/img/')))
        account = read_account()
        cookies = read_cookie()
        captcha = request.form['captcha0'], request.form['captcha1']
        for ac, ck, cp in zip(account, cookies, captcha):
            s = session()
            x = s.post(urljoin(domain, 'auth/signIn'),
                   data = {'username': ac[0], 'password': ac[1], 'captcha': cp},
                   cookies = {'JSESSIONID': ck})
        return jsonify({'msg': 'done'})


@app.route('/query', methods=['POST'])
def query():
    date = request.form['date']
    start = int(request.form['start'])
    end = int(request.form['end'])
    ck, _ = read_cookie()
    cookies = {'JSESSIONID': ck}
    spans = {}
    s = session()
    for st in seats:
        for idx, seat in zip(st[0], st[1]):
            html = s.post(urljoin(domain, 'freeBook/ajaxGetTime'),
                          data = {'id': str(idx), 'date': date},
                          cookies = cookies).content
            starts = BeautifulSoup(html, 'html.parser')
            spans[idx] = []
            for link in starts.find_all('a'):
                code = link.get('time')
                html = s.post(urljoin(domain, 'freeBook/ajaxGetEndTime'),
                              data = {'seat': str(idx), 'date': date, 'start': code},
                              cookies = cookies).content
                ends = BeautifulSoup(html, 'html.parser')
                for link2 in ends.find_all('a'):
                    spans[idx].append((code, link2.get('time')))
    res = []
    for idx, st in seats:
        for span in spans[idx[0]]:
            if span in spans[idx[1]] and span[0] != 'now':
                if start <= int(span[0]) and int(span[1]) <= end:
                    res.append({'id': idx, 'seat': st, 'span': span})
    res.sort(key=lambda x: int(x['span'][1]) - int(x['span'][0]), reverse=True)
    return jsonify(res)


@app.route('/book', methods=['POST'])
def book():
    idx = request.form['id0'], request.form['id1']
    cookies = read_cookie()
    s = session()
    for i, ck in enumerate(cookies):
        x = s.post(urljoin(domain, 'selfRes'),
                   cookies = {'JSESSIONID': ck},
                   data = {
                       'date': request.form['date'],
                       'start': request.form['start'],
                       'end': request.form['end'],
                       'seat': request.form['id%d' % i]
                   })
        if '<span style="color:red">' not in x.content:
            return jsonify({'msg': 'fail'})
    return jsonify({'msg': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0')
