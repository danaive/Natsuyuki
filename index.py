#!/usr/bin/env python

import json
import os
from datetime import datetime, timedelta
from io import BytesIO
from urlparse import urljoin

from bs4 import BeautifulSoup
from PIL import Image
from pytz import timezone
from requests import session

from flask import Flask, jsonify, redirect, render_template, request, url_for
from seats import *
from utils import *

app = Flask(__name__)


@app.route('/')
def index():
    tz = timezone('Asia/Shanghai')
    dt = datetime.now(tz)
    if not check_login(dt.strftime('%Y-%m-%d')):
        return redirect(url_for('login'))
    opts = range(8 * 60 + 30, 22 * 60, 30)
    if dt.hour * 60 + dt.minute >= 22 * 60:
        date = (dt + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
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
            if code != 'now' and int(code) >= start:
                html = s.post(urljoin(domain, 'freeBook/ajaxGetEndTime'),
                              data = {'seat': str(st[0]), 'date': date, 'start': code},
                              cookies = cookies).content
                ends = BeautifulSoup(html, 'html.parser')
                for link2 in ends.find_all('a'):
                    code2 = link2.get('time')
                    if int(code2) <= end and int(code2) - int(code) >= 120:
                        spans[st[0]].append((code, code2))
    res = []
    if request.form['usr'] == '2':
        for i in range(0, len(seats), 2):
            id0 = seats[i][0]
            id1 = seats[i+1][0]
            for span in spans[id0]:
                if span in spans[id1]:
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
                if start <= int(span[0]) and int(span[1]) <= end:
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
    span = request.form['start'], request.form['end']
    if do_book(request.form['usr'], idx, span, request.form['date']):
        return jsonify({'msg': 'ok'})
    return jsonify({'msg': 'fail'})


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


@app.route('/biu', methods=['POST'])
def delegate():
    try:
        task = json.load(open('task'))
    except:
        task = {'0': None, '1': None, '2': None}
    start = request.form['start']
    end = request.form['end']
    usr = request.form['usr']
    task[usr] = {'start': start, 'end': end}
    try:
        json.dump(task, open('task', 'w'))
        return jsonify({'msg': 'ok'})
    except:
        return jsonify({'msg': 'fail'})


if __name__ == '__main__':
    app.run(host='0.0.0.0')
