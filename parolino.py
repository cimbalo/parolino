#!/usr/bin/env python3
import time
import random
import json
from flask import Flask, url_for, redirect, request
from flask_socketio import SocketIO, emit, join_room, leave_room
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

def points(word):
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

def roll_dice():
    results = []
    for line in dices.split("\n"):
        results.append(random.choice(line).upper().replace("Q", "Qu"))
    random.shuffle(results)
    results = [results[i:i + 4] for i in range(0, len(results), 4)]
    return results

class Game():
    room = "public"
    letters = []
    running = False
    words = {}
    results = {}
    validity = {}
    scores = {}
    round = -1

    def new_round(self):
        self.round += 1
        self.letters = roll_dice()
        self.running = time.time() + DURATION
        self.results = {}
        self.validity = {}

    def background_thread(self):
        socketio.sleep(DURATION)
        self.running = None
        socketio.emit('board', (self.letters, self.running), to=self.room)
        print("stopping")

    def calculate_results(self):
        # print(app.words)
        all_words = [word for v in self.words.values() for word in v ]
        for word in set(all_words):
            if word not in self.validity:
                if dictionary.check(word) or dictionary.check(word + u'\u0300') or dictionary.check(word + u'\u0301'):
                    self.validity[word] = 1
                else:
                    self.validity[word] = 0
        unique = []
        for word in set(all_words):
            if all_words.count(word) == 1:
                unique.append(word)
        for k, v in self.words.items():
            self.results[k] = {}
            for word in v:
                if word in unique:
                    self.results[k][word] = points(word)
                else:
                    self.results[k][word] = 0
        
        if self.round >= 0:
            for k, v in self.results.items():
                if k not in self.scores:
                    self.scores[k] = []
                partial = 0
                for i in range(len(self.scores[k]), self.round + 1):
                    self.scores[k].append(None)
                for word, score in v.items():
                    partial += score
                self.scores[k][self.round] = partial
            print(self.round, self.scores)
        # print(app.results)

@app.route('/')
def home():
    return app.send_static_file('index.html')

@app.route('/reset')
def reset():
    app.games[app.clients[request.sid]]= Game()
    return "ok"

@socketio.on('connect')
def connect():
    print("connected")

@socketio.on('disconnect')
def disconnect():
    print("disconnect")
    send_result()
    if request.sid in app.clients:
        del app.clients[request.sid]

@socketio.on('join')
def join(room):
    join_room(room)
    app.clients[request.sid] = room
    if room not in app.games:
        app.games[room] = Game()
    emit('board', (app.games[app.clients[request.sid]].letters, app.games[app.clients[request.sid]].running), to=app.clients[request.sid])
    send_result()

@socketio.on('start')
def start():
    app.games[app.clients[request.sid]].new_round()
    socketio.start_background_task(app.games[app.clients[request.sid]].background_thread)
    socketio.emit('board', (app.games[app.clients[request.sid]].letters, app.games[app.clients[request.sid]].running), to=app.clients[request.sid])

@socketio.on('send')
def send(sid, words):
    app.games[app.clients[request.sid]].words[sid] = words
    # print(words)
    app.games[app.clients[request.sid]].calculate_results()
    send_result()

def send_result():
    socketio.emit('results', (json.dumps(app.games[app.clients[request.sid]].results), json.dumps(app.games[app.clients[request.sid]].validity), json.dumps(app.games[app.clients[request.sid]].scores)), to=app.clients[request.sid])
   
if __name__ == "__main__":
    # import logging
    # logging.basicConfig()
    # logging.getLogger().setLevel(logging.DEBUG)
    app.clients = {}
    app.games = {}
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)
