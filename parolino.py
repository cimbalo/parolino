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

def check_dictionary(word):
    if dictionary.check(word) or dictionary.check(word + u'\u0300') or dictionary.check(word + u'\u0301'):
        return 1
    else:
        return 0

class Game():

    def __init__(self, room):
        self.room = room
        self.round = -1
        self.words = {}
        self.letters = []
        self.running = False
        self.results = {}
        self.validity = {}
        self.scores = {}
        self.votes = {}

    def new_round(self):
        self.round += 1
        self.words = {}
        self.letters = roll_dice()
        self.running = time.time() + DURATION
        self.results = {}
        self.validity = {}
        self.scores = {}
        self.votes = {}

    def background_thread(self):
        socketio.sleep(DURATION)
        self.running = None
        socketio.emit('board', (self.letters, self.running), to=self.room)
        print("stopping")

    def calculate_votes(self, word):
        vote = 0
        for key in self.votes.keys():
            if word in self.votes[key]:
                vote += 1 if self.votes[key][word] else -1
        if vote < 0:
            self.validity[word] = vote
        else:
            self.validity[word] = check_dictionary(word)

    def calculate_results(self):
        # print(app.words)
        all_words = [word for v in self.words.values() for word in v ]
        # for word in set(all_words):
        #     if word not in self.validity:
                
        unique = []
        for word in set(all_words):
            if all_words.count(word) == 1:
                unique.append(word)
        for k, v in self.words.items():
            if k not in self.results:
                self.results[k] = {}
            partial = 0
            for word in v:
                self.calculate_votes(word)
                if word in unique and self.validity[word] >= 0:
                    self.results[k][word] = points(word)
                    partial += self.results[k][word]
                elif self.validity[word] < 0:
                    self.results[k][word] = self.validity[word]
                else:
                    self.results[k][word] = 0
            if k not in self.scores:
                self.scores[k] = []
            for i in range(len(self.scores[k]), self.round + 1):
                self.scores[k].append(None)
            self.scores[k][self.round] = partial
            print(self.round, self.scores)
        # print(app.results)

@app.route('/')
def home():
    return app.send_static_file('index.html')

@socketio.on('connect')
def connect():
    print("connected")

@socketio.on('disconnect')
def disconnect():
    print("disconnect")
    if request.sid in app.clients_room:
        del app.clients_room[request.sid]

@socketio.on('join')
def join(username, room):
    print(f'user "{username}" joined room "{room}"')
    if request.sid in app.clients_room:
        leave_room(room)
    join_room(room)
    app.clients_room[request.sid] = room
    app.clients[request.sid] = username
    if room not in app.games:
        app.games[room] = Game(room)
    emit('board', (app.games[app.clients_room[request.sid]].letters, app.games[app.clients_room[request.sid]].running), to=app.clients_room[request.sid])
    send_result()

@socketio.on('start')
def start():
    app.games[app.clients_room[request.sid]].new_round()
    socketio.start_background_task(app.games[app.clients_room[request.sid]].background_thread)
    socketio.emit('board', (app.games[app.clients_room[request.sid]].letters, app.games[app.clients_room[request.sid]].running), to=app.clients_room[request.sid])

@socketio.on('reset')
def reset():
    app.games[app.clients_room[request.sid]] = Game(app.clients_room[request.sid])
    socketio.emit('board', (app.games[app.clients_room[request.sid]].letters, app.games[app.clients_room[request.sid]].running), to=app.clients_room[request.sid])
    send_result()
    print(f"reset {app.clients_room[request.sid]}")

@socketio.on('send')
def send(words):
    app.games[app.clients_room[request.sid]].words[app.clients[request.sid]] = words
    # print(words)
    app.games[app.clients_room[request.sid]].calculate_results()
    send_result()

@socketio.on('votes')
def send(votes):
    app.games[app.clients_room[request.sid]].votes[app.clients[request.sid]] = votes
    # print(words)
    app.games[app.clients_room[request.sid]].calculate_results()
    send_result()

def send_result():
    socketio.emit('results',
                  (json.dumps(app.games[app.clients_room[request.sid]].results),
                  json.dumps(app.games[app.clients_room[request.sid]].validity),
                  json.dumps({k: (v[-1], sum(filter(None, v))) for k, v in app.games[app.clients_room[request.sid]].scores.items()})),
                  to=app.clients_room[request.sid])
   
if __name__ == "__main__":
    # import logging
    # logging.basicConfig()
    # logging.getLogger().setLevel(logging.DEBUG)
    app.clients_room = {}
    app.clients = {}
    app.games = {}
    socketio.run(app, host="0.0.0.0", port=5001, debug=True)
