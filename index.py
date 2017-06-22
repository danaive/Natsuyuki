#!/usr/bin/env python2

from flask import Flask, render_template, redirect, url_for, request, jsonify
from datetime import datetime, timedelta
from pytz import timezone
from requests import session
from urlparse import urljoin
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image
from seats import seats
import os


app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
domain = "http://seat.lib.whu.edu.cn/"
# seats = (((3091, 3092), (99, 100)),
#          ((3093, 3094), (101, 102)),
#          ((3096, 3097), (103, 104)),
#          ((3098, 3099), (105, 106)),
#          ((3100, 3101), (107, 108)),
#          ((3105, 3106), (109, 110)),
#          ((2575, 2574), (13, 14)),
#          ((2572, 2571), (15, 16)),
#          ((2569, 3089), (17, 18)))


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
    res = []
    for ck in cookies:
        s = session()
        x = s.post(urljoin(domain, 'freeBook/ajaxGetTime'),
                   data = {'id': '3010', 'date': today},
                   cookies = {'JSESSIONID': ck})
        if 'login' in x.url:
            res.append(False)
        else:
            res.append(True)
    return res


@app.route('/')
def index():
    tz = timezone('Asia/Shanghai')
    dt = datetime.now(tz)
    if not any(check_login(dt.strftime('%Y-%m-%d'))):
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
        html = s.post(urljoin(domain, 'freeBook/ajaxGetTime'),
                      data = {'id': str(st[0]), 'date': date},
                      cookies = cookies).content
        starts = BeautifulSoup(html, 'html.parser')
        spans[st[0]] = []
        for link in starts.find_all('a'):
            code = link.get('time')
            html = s.post(urljoin(domain, 'freeBook/ajaxGetEndTime'),
                          data = {'seat': str(st[0]), 'date': date, 'start': code},
                          cookies = cookies).content
            ends = BeautifulSoup(html, 'html.parser')
            for link2 in ends.find_all('a'):
                spans[st[0]].append((code, link2.get('time')))
    res = []
    if request.form['usr'] == '2':
        for i in range(0, len(seats), 2):
            id0 = seats[i][0]
            id1 = seats[i+1][0]
            for span in spans[id0]:
                if span in spans[id1] and span[0] != 'now':
                    if start <= int(span[0]) and int(span[1]) <= end:
                        res.append({
                            'id': (id0, id1),
                            'seat': (seats[i][1], seats[i+1][1]),
                            'span': span,
                            'pos': seats[i][2]
                        })
    else:
        for st in seats:
            for span in spans[st[0]]:
                if span[0] != 'now' and start <= int(span[0]) and int(span[1]) <= end:
                    res.append({
                        'id': (st[0], st[0]),
                        'seat': (st[1], st[1]),
                        'span': span,
                        'pos': st[2]
                    })
    res.sort(key=lambda x: int(x['span'][1]) - int(x['span'][0]), reverse=True)
    return jsonify(res)


@app.route('/book', methods=['POST'])
def book():
    idx = request.form['id0'], request.form['id1']
    cookies = read_cookie()
    s = session()
    usr = int(request.form['usr'])
    if usr == 2:
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
    else:
        x = s.post(urljoin(domain, 'selfRes'),
                   cookies = {'JSESSIONID': cookies[usr]},
                   data = {
                       'date': request.form['date'],
                       'start': request.form['start'],
                       'end': request.form['end'],
                       'seat': request.form['id0']
                   })
        if '<span style="color:red">' not in x.content:
            return jsonify({'msg': 'fail'})
    return jsonify({'msg': 'ok'})


@app.route('/check_booked', methods=['POST'])
def check_booked():
    cookies = read_cookie()
    name = ('Dan', 'Iris')
    res = []
    for ck, usr in zip(cookies, name):
        s = session()
        html = s.get(urljoin(domain, 'history?type=SEAT'),
                     cookies = {'JSESSIONID': ck}).content
        soup = BeautifulSoup(html, 'html.parser').find('a', attrs={'class': 'showLoading'})
        if soup:
            link = soup.get('href')
            time = soup.parent.find('dt').string
            pos = soup.parent.find('a').string.strip()
            res.append({'name': usr, 'link': link, 'time': time, 'pos': pos})
    return jsonify(res)


@app.route('/cancel_booked', methods=['POST'])
def cancel_booked():
    link = request.form['link']
    ck, _ = read_cookie()
    s = session()
    x = s.post(urljoin(domain, link), cookies={'JSESSIONID': ck})
    if 'login' in x.url:
        return jsonify({'msg': 'fail'})
    return jsonify({'msg': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0')
