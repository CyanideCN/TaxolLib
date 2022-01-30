import os

from pybufrkit.dataquery import NodePathParser, DataQuerent
from pybufrkit.decoder import Decoder
import numpy as np
from pandas import DataFrame

def dump_msg(msg):
    return np.array(list(msg.values())[0][0], float).ravel()

def safe_number(arr):
    nanpos = np.isnan(arr)
    arr_new = arr.copy()
    if nanpos.any():
        arr_new[nanpos] = -9999
    return arr_new

def decimal_fmt(num):
    return '{:.2f}'.format(num)

def format_str(tup):
    tup = map(decimal_fmt, tup)
    fmt = '{:>7},{:>10},{:>10},{:>10},{:>10},{:>10}\n'.format(*tup)
    return fmt

class SoundingDecoder(object):

    CODE_PRES = '007004'
    CODE_TMP = '012101'
    CODE_TD = '012103'
    CODE_HGT = '010009'
    CODE_WDIR = '011001'
    CODE_WSPD = '011002'
    CODE_BLOCK = '001001'
    CODE_ID = '001002'

    def __init__(self, file):
        decoder = Decoder()
        f = open(file, 'rb')
        self.msg = decoder.process(f.read())
        f.close()
        self.id_list = self._station_list()

    def _station_list(self):
        q = DataQuerent(NodePathParser())
        wmo_block = q.query(self.msg, self.CODE_BLOCK).results
        wmo_id = q.query(self.msg, self.CODE_ID).results
        def ravel(l):
            return [i for j in l for i in j]
        id_list = [str(i) + str(j).zfill(3) for i, j in zip(ravel(wmo_block.values()), ravel(wmo_id.values()))]
        return np.array(id_list)

    def _query(self, subset_num):
        TEMPLATE = '@[{}] > {}'
        q = DataQuerent(NodePathParser())
        df = DataFrame()
        pres_msg = q.query(self.msg, TEMPLATE.format(subset_num, self.CODE_PRES)).results
        df['pressure'] = dump_msg(pres_msg) / 100
        tmp_msg = q.query(self.msg, TEMPLATE.format(subset_num, self.CODE_TMP)).results
        df['temperature'] = dump_msg(tmp_msg) - 273.15
        td_msg = q.query(self.msg, TEMPLATE.format(subset_num, self.CODE_TD)).results
        df['dewpoint'] = dump_msg(td_msg) - 273.15
        hgt_msg = q.query(self.msg, TEMPLATE.format(subset_num, self.CODE_HGT)).results
        df['geopotential'] = dump_msg(hgt_msg)
        wdir_msg = q.query(self.msg, TEMPLATE.format(subset_num, self.CODE_WDIR)).results
        df['wind_direction'] = dump_msg(wdir_msg)
        wspd_msg = q.query(self.msg, TEMPLATE.format(subset_num, self.CODE_WSPD)).results
        df['wind_speed'] = dump_msg(wspd_msg)
        # Basic QC
        df = df.fillna(value={'dewpoint':-9999}) # Fill missing dewpoint at high levels
        df = df.interpolate(method='linear', limit_direction='forward', axis=0).drop_duplicates('geopotential').sort_values(by='geopotential')
        return df.fillna(-9999) # Fill Nans in starting level

    def query(self, station_id):
        if station_id not in self.id_list:
            raise ValueError('Station not found')
        id_idx = (station_id == self.id_list).nonzero()
        subset_num = id_idx[0][0]
        return self._query(subset_num)

    def to_sharppy(self, station_id, dtime, outdir):
        df = self.query(station_id)
        fname = 'SKEWT_' + dtime.strftime('%Y%m%d%H0000') + '_' + station_id +'.txt'
        outpath = os.path.join(outdir, fname)
        f = open(outpath, 'w')
        f.write('%TITLE%\n')
        f.write(' {}   {}\n\n'.format(station_id, dtime.strftime('%y%m%d/%H%M')))
        f.write('   LEVEL       HGHT       TEMP       DWPT       WDIR       WSPD\n')
        f.write('-------------------------------------------------------------------\n')
        f.write('%RAW%\n')
        for data in zip(safe_number(df['pressure']), safe_number(df['geopotential']),
                        safe_number(df['temperature']), safe_number(df['dewpoint']),
                        safe_number(df['wind_direction']), safe_number(df['wind_speed'] * 1.9438)):
            formatted = format_str(data)
            f.write(formatted)
        f.write('%END%')
        f.close()
        return outpath