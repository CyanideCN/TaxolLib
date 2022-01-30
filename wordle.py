import random
import asyncio
import sqlite3
import datetime
import time
import uuid
from collections import defaultdict

from nonebot.typing import T_State
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp.message import MessageSegment, Message
import pandas as pd

with open('data/wordle_cet4.txt', 'r') as f:
    wordle_cet4 = f.readlines()

with open('data/wordle_gre.txt', 'r') as f:
    wordle_gre = f.readlines()

wordle_session = dict()

class WordleDB(object):
    def __init__(self):
        self.db = sqlite3.connect('Wordle.db')

    def _get_user_list(self):
        command = f'SELECT DISTINCT UserID FROM UserRecord'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        return [i[0] for i in ret]

    def update_score(self, userid, score):
        cursor = self.db.cursor()
        if userid not in self._get_user_list():
            command_create = 'INSERT INTO UserRecord(UserID,TotalScore) VALUES(?,?)'
            cursor.execute(command_create, (userid, score))
        else:
            command_select = f'SELECT TotalScore FROM UserRecord WHERE UserID={userid}'
            prev_score = list(cursor.execute(command_select))[0][0]
            command_update = f'UPDATE UserRecord SET TotalScore={prev_score + score} WHERE UserID={userid}'
            cursor.execute(command_update)
        self.db.commit()
        cursor.close()

    def save_session(self, id, groupid, stime, word, etime, acount, winner, score):
        stime = stime + datetime.timedelta(hours=8)
        self._check_session_valid(id)
        cmd = '''INSERT INTO WordleRecord(ID,Year,Month,Day,Hour,Minute,Second,GroupID,Word,ElapsedTime,AttemptCount,WinnerID,Score)
         VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)'''
        cursor = self.db.cursor()
        cursor.execute(cmd, (id, stime.year, stime.month, stime.day, stime.hour, stime.minute, stime.second,
        groupid, word, etime, acount, winner, score))
        self.db.commit()
        cursor.close()

    def _check_session_valid(self, id):
        command = f'SELECT ID FROM WordleRecord WHERE ID="{id}"'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        ret = [i[0] for i in ret]
        if len(ret) == 0:
            return True
        else:
            return False

    def get_score(self):
        command = f'SELECT UserID, TotalScore FROM UserRecord ORDER BY TotalScore DESC'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        df = pd.DataFrame(ret, columns=['ID', 'Score'])
        ser = pd.Series(data=df['Score'].values, index=df['ID'])
        return ser.astype(int)

    def get_time_rank(self):
        command = f'SELECT WinnerID, ElapsedTime FROM WordleRecord ORDER BY ElapsedTime ASC LIMIT 20'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        df = pd.DataFrame(ret, columns=['ID', 'Score'])
        ser = pd.Series(data=df['Score'].values, index=df['ID'])
        return ser.round(1)

    def get_wordle_stats(self, uid):
        command = f'SELECT ElapsedTime, AttemptCount, Word FROM WordleRecord WHERE WinnerID={uid}'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        df = pd.DataFrame(ret, columns=['Time', 'Count', 'Word'])
        return df

db = WordleDB()

class WordleSession(object):

    CORRECT = '✔'
    MISSING = '❌'
    WRONG = '⭕'

    def __init__(self, group_id, difficulty):
        self.session_id = str(uuid.uuid1())
        self.group_id = group_id
        self.difficulty = 0 if difficulty != 1 else difficulty
        self.status = 0
        self.attempt_count = 0
        self.answer = self.choose_word()
        self.player_resp_time = defaultdict(int)
        self.disclosed_position = list()

    def choose_word(self):
        word_list = wordle_gre if self.difficulty == 1 else wordle_cet4
        return random.choice(word_list).strip()

    def process_input(self, uid, word):
        if len(word) != len(self.answer):
            return 1
        message = ''
        if len(set(word)) == 1:
            return 2
        ctime = time.time()
        self.attempt_count += 1
        for i in range(len(word)):
            if word[i] not in self.answer:
                message += self.MISSING
            elif word[i] == self.answer[i]:
                message += self.CORRECT
            else:
                message += self.WRONG
        msg_set = set(message)
        if len(msg_set) == 1 and msg_set.pop() == self.CORRECT:
            self.status = 1
            return 0
        if ctime < self.player_resp_time[uid] + 6:
            return 3
        self.player_resp_time[uid] = ctime
        return f'不对哦~\n' + message

    def init_prompt(self):
        self.start_time = datetime.datetime.utcnow()
        return f'游戏难度:{self.difficulty}\n本轮要猜的单词长度为{len(self.answer)}\n输入#加上单词即可参与游戏'

    def disclose_one(self):
        ret = ''
        if len(self.disclosed_position) < len(self.answer) - 3:
            while True:
                position = random.randint(0, len(self.answer) - 1)
                if position not in self.disclosed_position:
                    self.disclosed_position.append(position)
                    break
            for i in range(len(self.answer)):
                if i in self.disclosed_position:
                    ret += self.answer[i]
                else:
                    ret += '?'
        return ret

    def save_record(self, winner_id):
        msg = ''
        total_time = (datetime.datetime.utcnow() - self.start_time).total_seconds()
        if self.status == 0:
            score = 0
        else:
            base_score = (self.difficulty + 2) * 5
            length_bonus = len(self.answer) - 10
            if length_bonus < 0:
                length_bonus = 0
            raw_score = base_score + length_bonus
            time_scale = 120 / total_time
            if time_scale < 1:
                time_scale = 1
            elif time_scale > 5:
                time_scale = 5
            score = int(raw_score * time_scale)
            db.update_score(winner_id, score)
            msg += f'总尝试时间: {int(total_time)}s 获得分数: {score}分'
        db.save_session(self.session_id, self.group_id, self.start_time, self.answer, total_time, self.attempt_count,
        winner_id, score)
        return msg

async def start_wordle(bot: Bot, event: Event, state: T_State):
    mode = event.get_plaintext().strip()
    group_id = event.group_id
    if group_id in wordle_session:
        return await bot.send(event, '上一局游戏尚未结束!')
    try:
        mode = int(mode)
        ws = WordleSession(group_id, mode)
    except ValueError:
        if mode.isascii():
            ws = WordleSession(group_id, 0)
        else:
            raise
    wordle_session[group_id] = ws
    await bot.send(event, ws.init_prompt())
    await asyncio.sleep(60)
    for _ in range(len(ws.answer) - 2):
        await asyncio.sleep(60)
        if ws.status == 1:
            break
        dis = ws.disclose_one()
        if dis:
            await bot.send(event, f'提示:{dis}')
    if ws.status == 0:
        await bot.send(event, f'答案是{ws.answer}')
        if group_id in wordle_session:
            ws.save_record(None)
            del wordle_session[group_id]


code_mapping = {0:'恭喜你，猜对了!', 1:'单词长度不匹配', 2:'禁止穷举', 3:'你刷得太快啦'}

async def play_wordle(bot: Bot, event: Event, state: T_State):
    group_id = event.group_id
    uid = event.user_id
    ws = wordle_session.get(group_id, None)
    word = event.get_plaintext().strip()[1:].strip().lower()
    if ws and word.isalpha() and word.isascii():
        msg = ws.process_input(uid, word)
        if isinstance(msg, int):
            send_msg = code_mapping[msg]
            if msg == 0:
                ret = ws.save_record(uid)
                send_msg += f' 答案是{ws.answer}' + '\n' + ret
                send_msg = Message(Message(MessageSegment.at(uid)).extend([send_msg]))
                del wordle_session[group_id]
            await bot.send(event, send_msg)
        else:
            await bot.send(event, msg)