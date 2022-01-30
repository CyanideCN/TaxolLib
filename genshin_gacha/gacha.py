import random
import json
import math
import sqlite3
from io import BytesIO

from PIL import Image

with open('libs/genshin_gacha/pool.json', 'r', encoding='utf-8') as buf:
    pool = json.load(buf)

class Gacha(object):
    def __init__(self, **stats):
        #self.db = database
        self._4_star_counter = stats['_4_star_counter']
        self._5_star_counter = stats['_5_star_counter']
        self._4_star_char_counter = stats['_4_star_char_counter']
        self._4_star_weapon_counter = stats['_4_star_weapon_counter']
        self._5_star_char_counter = stats['_5_star_char_counter']
        self._5_star_weapon_counter = stats['_5_star_weapon_counter']
        self._is_last_4_star_up = bool(stats['_4_star_up'])
        self._is_last_5_star_up = bool(stats['_5_star_up'])
        self._last_5_star_counter = 1

    @classmethod
    def from_database(cls, db, uid):
        default_vals = {'_4_star_counter':1, '_5_star_counter':1, '_4_star_weapon_counter':1,
            '_4_star_char_counter':1, '_5_star_weapon_counter':1, '_5_star_char_counter':1,
            '_4_star_up':0, '_5_star_up':0}
        command = f'SELECT DISTINCT UserID FROM UserData'
        cursor = db.cursor()
        ret = cursor.execute(command)
        user_list = [i[0] for i in ret]
        if uid not in user_list:
            INSERT_CMD = f'''INSERT INTO UserData(UserID,_4StarCounter,_5StarCounter,_4StarWeaponCounter,_4StarCharCounter,\
            _5StarWeaponCounter,_5StarCharCounter,_4StarUp,_5StarUp) VALUES({uid},1,1,1,1,1,1,0,0)'''
            cursor.execute(INSERT_CMD)
            db.commit()
            return cls(**default_vals)
        QUERY_CMD = f'SELECT * FROM UserData WHERE UserID={uid}'
        ret = cursor.execute(QUERY_CMD)
        res = [i for i in ret][0][1:]
        print(res)
        for i, k in enumerate(default_vals):
            default_vals[k] = res[i]
        print(default_vals)
        return cls(**default_vals)

    def _determine_rarity(self):
        # _3_star_weight = 9430
        rand_num = random.randint(1, 10000)
        if self._5_star_counter <= 73:
            _5_star_weight = 60
        else:
            _5_star_weight = 60 + 600 * (self._5_star_counter - 73)
        if rand_num <= _5_star_weight:
            self._4_star_counter += 1
            self._last_5_star_counter = self._5_star_counter
            self._5_star_counter = 1
            return 5
        rand_num -= _5_star_weight
        if self._4_star_counter <= 8:
            _4_star_weight = 510
        else:
            _4_star_weight = 510 + 5100 * (self._4_star_counter - 8)
        if rand_num <= _4_star_weight:
            self._4_star_counter = 1
            self._5_star_counter += 1
            return 4
        else:
            self._4_star_counter += 1
            self._5_star_counter += 1
            return 3

    def reset_counter(self):
        self._4_star_counter = 1
        self._5_star_counter = 1
        self._4_star_char_counter = 1
        self._4_star_weapon_counter = 1
        self._5_star_char_counter = 1
        self._5_star_weapon_counter = 1

    def _determine_if_up(self, rarity):
        if rarity == 4:
            if not self._is_last_4_star_up:
                self._is_last_4_star_up = True
                return True
            else:
                if random.randint(0, 1) == 1:
                    self._is_last_4_star_up = True
                    return True
                else:
                    self._is_last_4_star_up = False
                    return False
        if rarity == 5:
            if not self._is_last_5_star_up:
                self._is_last_5_star_up = True
                return True
            else:
                if random.randint(0, 1) == 1:
                    self._is_last_5_star_up = True
                    return True
                else:
                    self._is_last_5_star_up = False
                    return False

    def _determine_if_char(self, rarity):
        if rarity == 5:
            return True
        if self._4_star_weapon_counter <= 17:
            weapon_weight = 255
        else:
            weapon_weight = 255 + 2550 * (self._4_star_weapon_counter - 17)
        if self._4_star_char_counter <= 17:
            char_weight = 255
        else:
            char_weight = 255 + 2550 * (self._4_star_char_counter - 17)
        is_char_prior = char_weight > weapon_weight
        total_weight = weapon_weight + char_weight
        rand_num = random.randint(1, total_weight)
        if is_char_prior:
            if rand_num < char_weight:
                self._4_star_char_counter = 1
                self._4_star_weapon_counter += 1
                return True
            else:
                self._4_star_char_counter += 1
                self._4_star_weapon_counter = 1
                return False
        else:
            if rand_num < weapon_weight:
                self._4_star_weapon_counter = 1
                self._4_star_char_counter += 1
                return False
            else:
                self._4_star_char_counter = 1
                self._4_star_weapon_counter += 1
                return True

    def pull_one(self):
        self._rarity = rarity = self._determine_rarity()
        if rarity > 3:
            up_flag = self._determine_if_up(rarity)
            char_flag = self._determine_if_char(rarity)
            if up_flag and char_flag:
                k = f'{rarity}_star_char_up'
            elif up_flag and not char_flag:
                k = f'{rarity}_star_weapon_up'
            elif char_flag and not up_flag:
                k = f'{rarity}_star_char_const'
            elif not char_flag and not up_flag:
                k = f'{rarity}_star_weapon_const'
        else:
            k = '3_star_weapon_const'
        candidates = pool[k]
        return random.choice(candidates)

    @staticmethod
    def get_png_path(name):
        return f'libs/genshin_gacha/icon/{name}.png'

    def concat_pic(self, item_list, border=5):
        num = len(item_list)
        w, h = [130, 160]
        des = Image.new('RGBA', (w * min(num, border), h * math.ceil(num / border)), (255, 255, 255, 0))
        for i in range(num):
            im = Image.open(self.get_png_path(item_list[i]))
            im = im.resize((130, 160))
            w_row = (i % border) + 1
            h_row = math.ceil((i + 1) / border)
            pixel_w = (w_row - 1) * w #+ pixel_w_offset
            pixel_h = (h_row - 1) * h #+ pixel_h_offset
            des.paste(im, (int(pixel_w), int(pixel_h)))
        return des

    def flush_database(self, db, uid):
        UPDATE_CMD = '''UPDATE UserData SET _4StarCounter={}, _5StarCounter={}, _4StarWeaponCounter={}\
            , _4StarCharCounter={}, _5StarWeaponCounter={}, _5StarCharCounter={}, _4StarUp={}, _5StarUp={}'''
        UPDATE_CMD += f' WHERE UserID={uid}'
        write_attrs = ['_4_star_counter', '_5_star_counter', '_4_star_weapon_counter', '_4_star_char_counter',
            '_5_star_weapon_counter', '_5_star_char_counter', '_4_star_up', '_5_star_up']
        data = list()
        for k in write_attrs:
            if k not in ['_4_star_up', '_5_star_up']:
                data.append(getattr(self, k))
            else:
                data.append(int(getattr(self, '_is_last' + k)))
        cursor = db.cursor()
        #print(UPDATE_CMD.format(*data))
        cursor.execute(UPDATE_CMD.format(*data))
        db.commit()

def pull_ten(uid):
    db = sqlite3.connect('libs/genshin_gacha/data.db')
    gacha = Gacha.from_database(db, uid)
    msg = ''
    item_list = list()
    for _ in range(10):
        result = gacha.pull_one()
        if gacha._rarity == 5:
            counter = gacha._last_5_star_counter
            msg += f'{counter}发 '
        item_list.append(result)
    img = gacha.concat_pic(item_list)
    gacha.flush_database(db, uid)
    buf = BytesIO()
    img.save(buf, 'png')
    buf.seek(0)
    return buf, msg.strip()