#!/usr/bin/env python3
import time
import random
import json
from flask import Flask, url_for, redirect
from flask_socketio import SocketIO, emit
import enchant
# random.seed(42)

DURATION = 180

dices = """oombaq
nezdva
uliore
tlspeu
ueonct
capedm
ofirac
ramosi
otaeai
gtnvei
sntdoe
esihrn
larecs
ilabrt
shefie
ulenog"""

app = Flask(__name__)
socketio = SocketIO(app,cors_allowed_origins='*')

dictionary = enchant.Dict("it_IT")

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/reset')
def reset():
    app.letters = []
    app.running = False
    app.words = {}
    app.results = {}
    app.validity = {}
    app.scores = {}
    app.round = -1
    return "ok"

@socketio.on('connect')
def connect():
    print("connected")
    emit('board', (app.letters, app.running))
    send_result()


@socketio.on('start')
def start():
    app.round += 1
    app.letters = roll_dice()
    socketio.start_background_task(background_thread)
    app.running = time.time() + DURATION
    app.results = {}
    app.validity = {}
    socketio.emit('board', (app.letters, app.running))

@socketio.on('send')
def send(sid, words):
    app.words[sid] = words
    # print(words)
    calculate_results()
    send_result()

def send_result():
    if app.round >= 0:
        for k, v in app.results.items():
            if k not in app.scores:
                app.scores[k] = []
            partial = 0
            for i in range(len(app.scores[k]), app.round + 1):
                app.scores[k].append(None)
            for word, score in v.items():
                partial += score
            app.scores[k][app.round] = partial
        print(app.round, app.scores)
    socketio.emit('results', (json.dumps(app.results), json.dumps(app.validity), json.dumps(app.scores)))

def score(word):
    if len(word) <= 4:
        return 1
    if len(word) == 5:
        return 2
    if len(word) == 6:
        return 3
    if len(word) == 7:
        return 5
    if len(word) >= 8:
        return 11

def calculate_results():
    # print(app.words)
    all_words = [word for v in app.words.values() for word in v ]
    for word in set(all_words):
        if dictionary.check(word) or dictionary.check(word + u'\u0300') or dictionary.check(word + u'\u0301'):
            app.validity[word] = 1
        else:
            app.validity[word] = 0
    unique = []
    for word in set(all_words):
        if all_words.count(word) == 1:
            unique.append(word)
    for k, v in app.words.items():
        app.results[k] = {}
        for word in v:
            if word in unique:
                app.results[k][word] = score(word)
            else:
                app.results[k][word] = 0
    # print(app.results)


def background_thread():
    socketio.sleep(DURATION)
    app.running = None
    socketio.emit('board', (app.letters, app.running))
    print("stopping")


def roll_dice():
    results = []
    for line in dices.split("\n"):
        results.append(random.choice(line).upper().replace("Q", "Qu"))
    random.shuffle(results)
    results = [results[i:i + 4] for i in range(0, len(results), 4)]
    return results
    
if __name__ == "__main__":
    # import logging
    # logging.basicConfig()
    # logging.getLogger().setLevel(logging.DEBUG)
    app.letters = []
    app.running = False
    app.words = {}
    app.results = {}
    app.validity = {}
    app.scores = {}
    app.round = -1
    socketio.run(app, port=5001)#, debug=True)
