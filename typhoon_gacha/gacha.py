import random
import sqlite3
import time
import uuid
import datetime
import collections
from io import BytesIO

import pandas as pd
from PIL import Image, ImageFont, ImageDraw

UR_PROB = 0.001
SSR_PROB = 0.02
SR_PROB = 0.20

SCORE_PER_PULL = 2.909
VALUE_MAP = {1:1, 2:6, 3:36, 4:210}

def log_gacha(result):
    rarity = result['Rarity'].values[0]
    code = result['ATCFCode'].values[0]
    name = result['Name'].values[0]
    desc = {1:'R', 2:'SR', 3:'SSR', 4:'UR'}
    return f'[{desc[rarity]}] {code} {name}'

def log_gacha2(result):
    rarity = result['Rarity']
    code = result['ATCFCode']
    name = result['Name']
    desc = {1:'R', 2:'SR', 3:'SSR', 4:'UR'}
    ret = f'[{desc[rarity]}] {code} {name}'
    if 'Count' in result and result['Count'] > 1:
        ret += f' ({result["Count"]})'
    return ret

def render_box(userid, result, refer_pool=False):
    _collection_flag = not isinstance(refer_pool, bool)
    rarity_color_lut = {4: (245, 66, 102), 3: (255, 162, 41), 2: (169, 41, 255), 1:(0, 0, 0)}
    result_len = len(result) if not _collection_flag else len(refer_pool)
    pix_per_line = 27
    column_width = 300
    item_per_column = 30
    col_num = result_len // item_per_column
    if result_len % item_per_column != 0:
        col_num += 1
    width = column_width * col_num
    if col_num == 1:
        length = pix_per_line * (result_len + 2)
        switch_column_points = []
    else:
        switch_column_points = [i * 30 for i in range(1, col_num)]
        length = pix_per_line * (item_per_column + 2)
    font = ImageFont.truetype(r'C:\Users\27455\AppData\Local\Microsoft\Windows\Fonts\Lato-Regular.ttf', 20)
    font2 = ImageFont.truetype(r'C:\Users\27455\AppData\Local\Microsoft\Windows\Fonts\STXIHEI.TTF', 22)
    img = Image.new('RGB', (width, length), (255, 255, 255))
    x = 20
    y = int(0.5 * pix_per_line)
    image_draw = ImageDraw.Draw(img)
    user_name = pool.get_nick(userid)
    if user_name:
        user_string = f'{user_name} [{userid}]'
    else:
        user_string = str(userid)
    title = f'{user_string}的收藏:' if _collection_flag else f'{user_string}的仓库:'
    image_draw.text((x, y), title, font=font2, fill=(0, 0, 0))
    y += pix_per_line
    count = 0
    data_iter = refer_pool if _collection_flag else result
    for _, line in data_iter.iterrows():
        if count in switch_column_points:
            x += column_width
            y = int(0.5 * pix_per_line) + pix_per_line
        if _collection_flag:
            atcf_code = line['ATCFCode']
            if atcf_code in result['ATCFCode'].values:
                line_rarity = line['Rarity']
                tmp = result[result['ATCFCode'] == atcf_code]
                tmp = tmp[tmp['Rarity'] == line_rarity]
                if len(tmp) > 0:
                    color = rarity_color_lut[line['Rarity']]
                else:
                    color = (207, 207, 207)
            else:
                color = (207, 207, 207)
        else:
            color = rarity_color_lut[line['Rarity']]
        image_draw.text((x, y), log_gacha2(line), font=font, fill=color)
        y += pix_per_line
        count += 1
    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf

def render_rank(rank_data, highlight, title):
    picture_time = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    pix_per_line = 30
    column_width = 350
    width = column_width
    length = pix_per_line * 22
    font = ImageFont.truetype(r'C:\Users\27455\AppData\Local\Microsoft\Windows\Fonts\Lato-Regular.ttf', 20)
    font2 = ImageFont.truetype(r'C:\Users\27455\AppData\Local\Microsoft\Windows\Fonts\STXIHEI.TTF', 20)
    font3 = ImageFont.truetype(r'C:\Users\27455\AppData\Local\Microsoft\Windows\Fonts\Lato-Regular.ttf', 12)
    img = Image.new('RGB', (width, length), (255, 255, 255))
    y = pix_per_line * 0.8
    x = column_width * 0.05
    image_draw = ImageDraw.Draw(img)
    image_draw.text((x, y * 0.5), title, font=font2, fill=(0, 0, 0))
    image_draw.text((220, y), picture_time.strftime('%Y-%m-%d %H:%M:%S'), font=font3, fill=(0, 0, 0))
    extra_plot = True
    y += pix_per_line
    for i in range(20):
        x = column_width * 0.05
        uid = int(rank_data.index[i])
        if uid == highlight:
            color = (245, 66, 102)
            extra_plot = False
        else:
            color = (0, 0, 0)
        image_draw.text((x, y), str(i + 1), font=font, fill=color)
        x = column_width * 0.25
        uname = pool.get_nick(uid)
        if not uname:
            image_draw.text((x, y), str(uid), font=font, fill=color)
        else:
            image_draw.text((x, y - 3), uname, font=font2, fill=color)
        x = column_width * 0.75
        image_draw.text((x, y), str(rank_data.iloc[i]), font=font, fill=color)
        y += pix_per_line
        if i == 18:
            if extra_plot:
                rank = rank_data.index.to_list().index(highlight)
                image_draw.text((column_width * 0.05, y), str(rank + 1), font=font, fill=(245, 66, 102))
                uname = pool.get_nick(highlight)
                if not uname:
                    image_draw.text((column_width * 0.25, y), str(highlight), font=font, fill=(245, 66, 102))
                else:
                    image_draw.text((column_width * 0.25, y - 3), uname, font=font2, fill=(245, 66, 102))
                image_draw.text((column_width * 0.75, y), str(rank_data.iloc[rank]), font=font, fill=(245, 66, 102))
                break
    buf = BytesIO()
    img.save(buf, 'PNG')
    buf.seek(0)
    return buf

class GachaPool(object):
    def __init__(self, pool_path='libs/typhoon_gacha/pool.csv', debug=False):
        pool = pd.read_csv(pool_path)
        self._pool = pool
        self.ur_pool = pool[pool['Rarity'] == 4]
        self.ssr_pool = pool[pool['Rarity'] == 3]
        self.sr_pool = pool[pool['Rarity'] == 2]
        self.r_pool = pool[pool['Rarity'] == 1]
        self.db = sqlite3.connect('libs/typhoon_gacha/gacha_data.db')
        self.debug = debug
        self.pool_mapping = {1:self.r_pool, 2:self.sr_pool, 3:self.ssr_pool, 4:self.ur_pool}

    def _generate_rarity(self):
        rand = random.random()
        if rand < UR_PROB:
            return 4
        elif rand < SSR_PROB:
            return 3
        elif rand < SR_PROB:
            return 2
        else:
            return 1

    def pull_one(self, userid=None, pullid=None, rarity=None):
        if not rarity:
            rarity = self._generate_rarity()
        pool = self.pool_mapping[rarity]
        result = pool.sample()
        self.save_record(result, userid, pullid)
        return result

    def __str__(self):
        return f'<GachaPool SSR: {len(self.ssr_pool)} SR: {len(self.sr_pool)} R: {len(self.r_pool)}>'

    def _update_box_from_record(self, userid):
        command = 'INSERT INTO UserBox(UserID,ATCFCode,Name,Rarity,Count) VALUES(?,?,?,?,?)'
        val = self._calculate_box_from_record(userid)
        cursor = self.db.cursor()
        for _, i in val.iterrows():
            vl = i.tolist()
            ins = [userid] + vl
            cursor.execute(command, ins)
        cursor.close()
        self.db.commit()

    def _get_user_list(self, table_name='UserBox'):
        command = f'SELECT DISTINCT UserID FROM {table_name}'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        return [i[0] for i in ret]

    def _get_all_storms(self, userid):
        command = f'SELECT DISTINCT ATCFCode FROM UserBox WHERE UserID={userid}'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        return [i[0] for i in ret]

    def _get_all_storms_with_rarity(self, userid, rarity):
        command = f'SELECT DISTINCT ATCFCode FROM UserBox WHERE UserID={userid} AND Rarity={rarity}'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        return [i[0] for i in ret]     

    def save_record(self, result, userid, pollid):
        if self.debug:
            return
        command = 'INSERT INTO UserGachaRecord(UserID,Time,ATCFCode,Name,Rarity,PullID) VALUES(?,?,?,?,?,?)'
        command_add = 'INSERT INTO UserBox(UserID,ATCFCode,Name,Rarity,Count) VALUES(?,?,?,?,?)'
        #storm_list = self._get_all_storms(userid)
        atcf_code = result['ATCFCode'].values[0]
        rarity = result['Rarity'].values[0]
        # Update box
        status = self.update_box(userid, atcf_code, rarity, 1)
        cursor = self.db.cursor()
        if status == 1:
            cursor.execute(command_add, [userid] + result.values[0].tolist() + [1,])
        # Save record
        res = result.values[0].tolist()
        data = [userid, time.time()] + res + [pollid.bytes]
        cursor.execute(command, data)
        cursor.close()
        self.db.commit()

    def pull(self, userid, count=None):
        results = list()
        token = self.get_token(userid)
        if not count:
            if token == 0:
                return -1
            if token < 10:
                max_count = token
            else:
                max_count = 10
            pull_time = random.randint(1, max_count)
        else:
            if token < count:
                return -1
            pull_time = count
        pullid = uuid.uuid1()
        for i in range(pull_time):
            results.append(self.pull_one(userid, pullid))
        self.set_token_or_signin_time(userid, token=token - pull_time)
        return results

    def _calculate_box_from_record(self, userid):
        #command = f'SELECT ATCFCode, Name, Rarity, COUNT(ATCFCode) FROM UserGachaRecord WHERE UserID={userid} GROUP BY ATCFCode, Rarity ORDER BY Rarity DESC'
        command = f'SELECT ATCFCode, Name, Rarity, Count FROM UserBox WHERE UserID={userid} ORDER BY Rarity DESC'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        df = pd.DataFrame(ret, columns=['ATCFCode', 'Name', 'Rarity', 'Count'])
        return df

    def get_box(self, userid):
        command = f'SELECT ATCFCode, Name, Rarity, Count FROM UserBox WHERE UserID={userid} AND Count > 0 ORDER BY Rarity DESC'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        df = pd.DataFrame(ret, columns=['ATCFCode', 'Name', 'Rarity', 'Count'])
        return df

    def update_box(self, userid, atcf_code, rarity, increment):
        if self.debug:
            return
        storm_list = self._get_all_storms_with_rarity(userid, rarity)
        if atcf_code in storm_list:
            command_select = f'SELECT Count FROM UserBox WHERE UserID={userid} AND ATCFCode="{atcf_code}" AND Rarity={rarity}'
            cursor = self.db.cursor()
            prev_count = list(cursor.execute(command_select))[0][0]
            command_update = f'UPDATE UserBox SET Count={prev_count + increment} WHERE UserID={userid} AND ATCFCode="{atcf_code}" AND Rarity={rarity}'
            cursor.execute(command_update)
            self.db.commit()
            cursor.close()
            return 0
        return 1

    def view_box(self, userid):
        return render_box(userid, self.get_box(userid))

    def get_token(self, userid):
        command = f'SELECT Token FROM UserToken WHERE UserID={userid}'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        r = list(ret)
        if len(r) == 0:
            self.set_token_or_signin_time(userid)
            return 0
        return r[0][0]

    def get_last_signin_time(self, userid):
        command = f'SELECT LastSignInTime FROM UserToken WHERE UserID={userid}'
        cursor = self.db.cursor()
        ret = cursor.execute(command)
        r = list(ret)
        if len(r) == 0:
            self.set_token_or_signin_time(userid)
            return 0
        return r[0][0]

    def set_token_or_signin_time(self, userid, token=None, signintime=None):
        ulist = self._get_user_list('UserToken')
        cursor = self.db.cursor()
        if userid not in ulist:
            command_add = f'INSERT INTO UserToken(UserID,Token,LastSignInTime) VALUES({userid},0,0)'
            cursor.execute(command_add)
        if token != None:
            command = f'UPDATE UserToken SET Token={token} WHERE UserID={userid}'
            cursor.execute(command)
        if signintime != None:
            command = f'UPDATE UserToken SET LastSignInTime={signintime} WHERE UserID={userid}'
            cursor.execute(command)
        cursor.close()
        self.db.commit()

    def signin(self, userid):
        today = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        today = today.replace(hour=0, minute=0, second=0)
        today_timestamp = int(today.timestamp())
        last_timestamp = self.get_last_signin_time(userid)
        if last_timestamp == today_timestamp:
            return -1
        new_token = int(random.gammavariate(5, 3))
        all_token = self.get_token(userid) + new_token
        self.set_token_or_signin_time(userid, token=all_token, signintime=today_timestamp)
        return new_token, all_token

    def synthesize_card(self, userid, rarity=None, cards=None):
        UPGRADE_PROB = 0.4
        EXTRA_PROB = 0.05
        # if rarity is specified, randomly choose cards from box
        df = self.get_box(userid)
        if rarity != None:
            df_dup = df[df['Count'] > 1]
            df_select = df_dup[df_dup['Rarity'] == rarity]
            all_candidates = list()
            for _, i in df_select.iterrows():
                all_candidates.extend([i['ATCFCode']] * (i['Count'] - 1))
            if len(all_candidates) < 3:
                # Not enough cards to synthesize
                return -1
            cards = random.sample(all_candidates, 3)
            for c in cards:
                self.update_box(userid, c, rarity, -1)
        else:
            # Check if there're enough cards in the box
            base_rarity = list()
            c = collections.Counter(cards)
            cards_count = c.most_common()
            cards_to_be_removed = list()
            for cname, ccount in cards_count:
                target = df[df['ATCFCode'] == cname]
                # Exclude all UR cards
                target = target[target['Rarity'] < 4]
                if len(target) == 0:
                    return -2
                target = target.iloc[0]
                if target['Count'] < ccount:
                    return -2
                base_rarity.append(target['Rarity'])
                cards_to_be_removed.append((cname, target['Rarity'], ccount))
            for cname, crarity, ccount in cards_to_be_removed:
                # Decrese the count of original storms
                self.update_box(userid, cname, crarity, -1 * ccount)
            rarity = min(base_rarity)
        results = list()
        pullid = uuid.uuid1()
        if rarity == 3:
            # If use 3 identical SSR cards, directly return corresponding
            # UR card if applicable
            card_set = set(cards)
            if len(card_set) == 1:
                unique_card = cards[0]
                if unique_card in self.ur_pool['ATCFCode'].values:
                    results.append(self.ur_pool[self.ur_pool['ATCFCode'] == unique_card])
                    self.save_record(results[0], userid, pullid)
                    # Terminate here
                    return cards, results
        # Determine if there's an upgrade of rarity
        if random.random() < UPGRADE_PROB:
            rarity += 1
        results.append(self.pull_one(userid, pullid, rarity))
        if random.random() < EXTRA_PROB:
            results.append(self.pull_one(userid, pullid, rarity))
        return cards, results

    def synthesize_all_dup(self, userid, rarity):
        df = self.get_box(userid)
        df_dup = df[df['Count'] > 1]
        df_select = df_dup[df_dup['Rarity'] == rarity]
        all_candidates = list()
        for _, i in df_select.iterrows():
            all_candidates.extend([i['ATCFCode']] * (i['Count'] - 1))
        syn_count = len(all_candidates) // 3
        if syn_count == 0:
            # Not enough cards to synthesize
            return -1
        new_cards = list()
        for i in range(syn_count):
            cards = all_candidates[i * 3:(i + 1) * 3]
            used_cards, results = self.synthesize_card(userid, cards=cards)
            new_cards.extend(results)
        return new_cards

    def view_collection(self, userid):
        return render_box(userid, self._calculate_box_from_record(userid), refer_pool=self._pool)

    def get_nick(self, userid):
        cmd = f'SELECT Nick FROM UserNick WHERE UserID={userid}'
        cursor = self.db.cursor()
        ret = cursor.execute(cmd)
        r = list(ret)
        if len(r) == 0:
            return None
        else:
            return r[0][0]

    def set_nick(self, userid, nick):
        current_nick = self.get_nick(userid)
        cursor = self.db.cursor()
        if current_nick:
            if current_nick != nick:
                cmd = f'UPDATE UserNick SET Nick="{nick}" WHERE UserID={userid}'
                try:
                    cursor.execute(cmd)
                except sqlite3.IntegrityError:
                    return -1
        else:
            cmd = 'INSERT INTO UserNick(UserID,Nick) VALUES(?,?)'
            try:
                cursor.execute(cmd, (userid, nick))
            except sqlite3.IntegrityError:
                return -1
        self.db.commit()
        return 0

    def get_box_score(self, token_adjust=False):
        cursor = self.db.cursor()
        cmd = 'SELECT UserID, SUM(Count) FROM UserBox WHERE Rarity={} GROUP BY UserID'
        ser = None
        for rarity in range(1, 5):
            df = pd.DataFrame(cursor.execute(cmd.format(rarity)), columns=['UserID', 'Count'])
            _ser = pd.Series(data=df['Count'].values * VALUE_MAP[rarity], index=df['UserID'])
            if isinstance(ser, pd.Series):
                ser = ser.add(_ser, fill_value=0)
            else:
                ser = _ser
        if token_adjust:
            for idx, _id in enumerate(ser.index):
                ser[_id] += SCORE_PER_PULL * self.get_token(_id)
        return ser.sort_values(ascending=False).astype(int)

    def get_collection_score(self):
        cursor = self.db.cursor()
        cmd = 'SELECT UserID, COUNT(ATCFCode) FROM UserBox WHERE Count > 0 GROUP BY UserID'
        ret = cursor.execute(cmd)
        df = pd.DataFrame(ret, columns=['UserID', 'Count'])
        ser = pd.Series(data=df['Count'].values, index=df['UserID'])
        return ser.sort_values(ascending=False)

    def view_box_rank(self, userid, token_adjust=False):
        if token_adjust:
            return render_rank(self.get_box_score(token_adjust=True), userid, '仓库价值排行[估算总价值]')
        else:
            return render_rank(self.get_box_score(), userid, '仓库价值排行')

    def view_collection_rank(self, userid):
        return render_rank(self.get_collection_score(), userid, '当前收藏数量排行')

    def decompose_card(self, userid, card):
        df = self.get_box(userid)
        # Only UR can be broken down
        ur_list = df[df['Rarity'] == 4]
        if len(ur_list) < 1:
            return -1
        target = ur_list[ur_list['ATCFCode'] == card]
        if len(target) == 0:
            return -2
        target = target.iloc[0]
        if target['Count'] == 0:
            return -3
        val = 210 * random.randint(50, 120) / 100
        return_token = 0
        return_cards = list()
        while True:
            # Loop until all values are used
            pullid = uuid.uuid1()
            if random.randint(0, 3) != 0:
                # Return cards
                while True:
                    rarity = self._generate_rarity()
                    if VALUE_MAP[rarity] < val:
                        break
                result = self.pull_one(userid, pullid, rarity)
                return_cards.append(result)
                card_val = VALUE_MAP[result['Rarity'].values[0]]
                if val < card_val:
                    break
                val -= card_val
            else:
                max_pull = int(val / SCORE_PER_PULL)
                if max_pull == 1:
                    ret_token = 1
                else:
                    ret_token = random.randint(1, max_pull)
                val -= return_token * SCORE_PER_PULL
                return_token += ret_token
                if val < SCORE_PER_PULL:
                    break
        all_token = self.get_token(userid) + return_token
        self.update_box(userid, card, 4, -1)
        self.set_token_or_signin_time(userid, token=all_token)
        return return_token, return_cards

pool = GachaPool()

if __name__ == '__main__':
    pool = GachaPool()
    print(pool.decompose_card(274555447, 'WP162016'))