import numpy as np

__version__ = '1.0.2'

rng = np.random.default_rng()

NO_INFLUENCE = -1

def random_with_range(a, b):
    return (b - a) * rng.random() + a

def distance(x1, x2, y1, y2):
    return np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def comp2lonlat(dir, spd):
    lat = spd * np.cos(np.deg2rad(dir))
    lon = spd * np.sin(np.deg2rad(dir))
    return lon, lat

def dlondlat2comp(dlon, dlat):
    spd = np.sqrt(dlon ** 2 + dlat ** 2)
    dir = 90. - np.rad2deg(np.arctan2(-dlat, -dlon))
    if dir < 0:
        dir += 360
    return dir, spd

def acute_intersect_angle(a1, a2):
    a = abs(a1 - a2)
    if a > 180:
        a = 360 - a
    return a

def angle_mean(a1, a2):
    if a1 > 180:
        a1 = a1 - 360
    if a2 > 180:
        a2 = a2 - 360
    mean = (a1 + a2) / 2
    return mean if mean > 0 else mean + 360

class SubtropRidge(object):
    def __init__(self):
        self.center_lon = random_with_range(95, 145)
        self.center_lat = rng.poisson(22) + random_with_range(-7, 7)
        self.half_span_lon = random_with_range(15, 22)
        self.half_span_lat = random_with_range(9, 14)

    def get_movement(self, lon, lat):
        return NO_INFLUENCE
        west_bound = self.center_lon - self.half_span_lon - 3
        east_bound = self.center_lon + self.half_span_lon + 3
        bottom = self.center_lat - self.half_span_lat
        top = self.center_lat + self.half_span_lat
        if (lon < west_bound) or (lon > east_bound) or (lat > top):
            return NO_INFLUENCE
        if (lat < bottom):
            # Westward
            direction = random_with_range(275, 305)
            movement = random_with_range(0.5, 2)
        else:
            angle = NO_INFLUENCE
            dist_from_center = distance(self.center_lon, lon, self.center_lat, lat)
            #diagonal_length = np.sqrt(self.half_span_lat ** 2 + self.half_span_lon ** 2)
            abs_angle = np.rad2deg(np.tan(abs(lat - self.center_lat) / abs(lon - self.center_lon)))
            dist_from_west = distance(west_bound, lon, self.center_lat, lat)
            dist_from_south = distance(self.center_lon, lon, bottom, lat)
            dist_from_east = distance(east_bound, lon, self.center_lat, lat)
            dist_from_north = distance(self.center_lon, lon, top, lat)
            if dist_from_center < self.half_span_lon:
                if (lon <= self.center_lon) and (lat <= self.center_lat):
                    print('3 quad')
                    # Third quadrant
                    weighted_distance = np.average([self.half_span_lon, self.half_span_lat],
                        weights=[dist_from_south, dist_from_west])
                    if dist_from_center < weighted_distance:
                        angle = 360 - abs_angle
                elif (lon < self.center_lon) and (lat > self.center_lat):
                    print('4 quad')
                    # Forth quadrant
                    weighted_distance = np.average([self.half_span_lon, self.half_span_lat],
                        weights=[dist_from_north, dist_from_west])   
                    if dist_from_center < weighted_distance:
                        angle = abs_angle
                elif (lon > self.center_lon) and (lat < self.center_lat):
                    print('2 quad')
                    # Second quadrant
                    weighted_distance = np.average([self.half_span_lon, self.half_span_lat],
                        weights=[dist_from_south, dist_from_east])
                    if dist_from_center < weighted_distance:
                        angle = abs_angle
                elif (lon > self.center_lon) and (lat > self.center_lat):
                    print('1 quad')
                    # First quadrant
                    weighted_distance = np.average([self.half_span_lon, self.half_span_lat],
                        weights=[dist_from_north, dist_from_east])
                    if dist_from_center < weighted_distance:
                        angle = 360 - abs_angle
                if angle == NO_INFLUENCE:
                    return NO_INFLUENCE
                angle = angle % 360
                direction = 360 - angle + random_with_range(-5, 5)
                movement = random_with_range(0.5, 3)
            else:
                return NO_INFLUENCE
        return direction, movement

    def update(self):
        self.center_lon += random_with_range(-0.5, 0.5)
        self.center_lat += random_with_range(-0.3, 0.3)
        self.half_span_lon += random_with_range(-0.5, 0.5)
        self.half_span_lat += random_with_range(-0.3, 0.3)

class Westerlies(object):
    def __init__(self):
        self.center_lat = random_with_range(35, 45)

    def get_movement(self, lon, lat):
        if lat < self.center_lat - 13:
            return NO_INFLUENCE
        else:
            # print('East')
            east_adjust = random_with_range(1, 4)
            if lat < self.center_lat:
                east_adjust *= 1 - (self.center_lat - lat) / 7
                if east_adjust < 0:
                    east_adjust = 0
            direction = random_with_range(45, 115)
            return direction, east_adjust

    def update(self):
        self.center_lat += random_with_range(-0.2, 0.2)

class Storm(object):
    def __init__(self):
        self.longitude = []
        self.latitude = []
        self.intens = []
        #self.pres = []
        self.STR = SubtropRidge()
        self.WST = Westerlies()
        self.last_dir = random_with_range(270, 310)
        self.last_spd = 0.5
        self._near_eq_flag = False
        self._weaken_flag = False
        self.init_storm()
        self._south_time = 0

    @property
    def last_lon(self):
        return self.longitude[-1]

    @property
    def last_lat(self):
        return self.latitude[-1]

    @property
    def last_intens(self):
        return self.intens[-1]

    def init_storm(self):
        lat = rng.poisson(12) + random_with_range(-7, 7)
        #lat = 10
        lon = random_with_range(120, 170)  + rng.random() * 10 - 5
        #lon = 179
        intens = random_with_range(20, 30)
        #intens = 137
        self.latitude.append(lat)
        self.longitude.append(lon)
        self.intens.append(intens)

    def get_intens_change(self):
        # Restrictions
        if self.last_lat < 2:
            return self.last_intens * -1 * random_with_range(0.5, 0.9)
        # Westerly
        if (self.last_intens > 50) and (self.last_lat > self.WST.center_lat):
            # print(f'Westerly')
            return self.last_intens ** 0.5 - self.last_intens
        if 95 < self.last_lon <= 110:
            return self.last_intens * -1 * random_with_range(0.2, 0.5)
        # Mainland
        elif 110 < self.last_lon < 120:
            if self.last_lon < 117:
                if self.last_lat > 23:
                    return self.last_intens * -1 * random_with_range(0.3, 0.5)
            if 117 < self.last_lat < 120:
                if self.last_lat > 27:
                    return self.last_intens * -1 * random_with_range(0.3, 0.5)
        elif 120 < self.last_lon < 123:
            # Philippines
            if 14 < self.last_lat < 18:
                return self.last_intens * -1 * random_with_range(0.2, 0.5)
            elif 5 < self.last_lat <= 14:
                return self.last_intens * -1 * random_with_range(0.1, 0.4)
        else:
            if (self.last_lat > 35) and (self.last_lon < 120):
                return self.last_intens * -1 * random_with_range(0.4, 0.6)
        # From stats
        if self.last_lon >= 125:
            if self.last_lat < 25:
                weaken_prob = 0.1
            else:
                weaken_prob = 0.8
        elif 110 < self.last_lon < 125:
            if self.last_lat < 20:
                weaken_prob = 0.1
            else:
                weaken_prob = 0.9
        else:
            weaken_prob = 0.9
        # inhibit intensification above 35N
        if self.last_lat > 35:
            weaken_prob = 1
        # universal flags
        if self._weaken_flag:
            weaken_prob += 0.1
        if self.last_intens > 180:
            weaken_prob = 0.99
        elif self.last_intens > 110:
            weaken_prob += 0.1
        change = rng.gamma(3.5, 2)
        if rng.random() < weaken_prob:
            change *= -1
        if (25 < self.last_lat < 35) and (self.last_lon > 125):
            if rng.random() > 0.6:
                change += random_with_range(0, 5)
        if (self.last_intens > 137) and (self.last_lat > 27):
            d = self.last_intens - 137
            change = random_with_range(d * 1.5, d * 2) * -1
        return change

    def extra_mov_factor(self):
        dlon, dlat = 0, 0
        if (self.last_lon < 125) and (self.last_lat < 20):
            dlat += random_with_range(0.2, 0.5)
        return dlon, dlat

    def move(self):
        ret = self.STR.get_movement(self.last_lon, self.last_lat)
        self.STR.update()
        if ret == NO_INFLUENCE:
            if self._near_eq_flag or (self.last_lat < self.latitude[0] - 1):
                # print('North')
                deg_from_0 = 270 - self.last_dir
                direction = self.last_dir + random_with_range(deg_from_0 + 5, deg_from_0 + 20)
            if self.last_intens > 100:
                dir_adj_range = 5 + (100 / self.last_intens) * 5
            else:
                dir_adj_range = 20
            direction = self.last_dir + random_with_range(-1 * dir_adj_range, dir_adj_range)
            movement = self.last_spd + random_with_range(-0.5 * self.last_spd, 1)
        else:
            direction, movement = ret
            if self.last_intens > 1000:
                # Stronger TCs are reluctant to steering
                direction_diff_factor = abs(direction - self.last_dir)
                direction = self.last_dir + random_with_range(-direction_diff_factor, direction_diff_factor)
                movement *= (20 / (self.last_intens - 80))
                dx, dy = comp2lonlat(direction, movement)
                dx1, dy1 = comp2lonlat(self.last_dir, movement)
                dx_weighted = np.average([dx, dx1], weights=[70, self.last_intens])
                dy_weighted = np.average([dy, dy1], weights=[70, self.last_intens])
                direction, movement = dlondlat2comp(dx_weighted, dy_weighted)
        direction = direction % 360
        if self._south_time >= random_with_range(1, 3):
            # Reduce south component
            if 90 < direction < 180:
                # Round to less than 90 degs
                direction = random_with_range(60, 90)
            elif 180 < direction < 270:
                direction = random_with_range(270, 310)
        if acute_intersect_angle(direction, self.last_dir) > 60:
            # Reduce sudden turn
            # print('Reduce turn')
            direction = angle_mean(direction, self.last_dir)
            if acute_intersect_angle(direction, self.last_dir) > 60:
                direction = angle_mean(direction, self.last_dir)
        dlon, dlat = comp2lonlat(direction, movement)
        elon, elat = self.extra_mov_factor()
        self.WST.update()
        ret = self.WST.get_movement(self.last_lon, self.last_lat)
        if ret != NO_INFLUENCE:
            # Interaction with westerly
            dlon1, dlat1 = comp2lonlat(*ret)
            dlon += dlon1
            dlat += dlat1
        dlon += elon
        dlat += elat
        if dlat < 0:
            self._south_time += 1
        else:
            self._south_time = 0
        self.longitude.append(self.last_lon + dlon)
        self.latitude.append(self.last_lat + dlat)
        self.last_dir = direction
        self.last_spd = movement
        if (self.last_lat < 5) and (90 < self.last_dir < 270):
            self._near_eq_flag = True
        else:
            self._near_eq_flag = False
        dintens = self.get_intens_change()
        if dintens < 0:
            self._weaken_flag = True
        else:
            self._weaken_flag = False
        if dintens < -50:
            dintens = -50
        self.intens.append(self.last_intens + dintens)

    def is_dissipated(self):
        if self.last_intens < 20:
            stop_prob = (20 - self.last_intens) / 15
            if rng.random() < stop_prob:
                return True
        if self.last_lat < 0.5:
            return True
        elif (self.last_lat > self.WST.center_lat + 3):
            if self.last_intens < 40:
                if rng.random() < 0.9:
                    return True
        return False

    def run(self):
        while not self.is_dissipated():
            self.move()
        self.postprocess()

    def postprocess(self):
        SOUTH_TURN_THRES = -0.3
        dy = np.diff(self.latitude)
        bad_pts = (dy < SOUTH_TURN_THRES).nonzero()[0]
        if bad_pts.size > 0:
            # Remove 2 end points
            bad_pts = bad_pts[bad_pts < len(self.latitude) - 2]
            for bp in bad_pts:
                new_lat = (self.latitude[bp] + self.latitude[bp + 2]) / 2
                self.latitude[bp + 1] = new_lat

    def __repr__(self):
        return f'<Storm {self.last_lat} N {self.last_lon} E {self.intens[-1]} kt>'

    def to_database(self, conn, sim_id, user_id):
        sql_tpl = '''INSERT INTO TRACK(SimID, UserID, Lon, Lat, Wind) VALUES(?,?,?,?,?)'''
        cursor = conn.cursor()
        lon = np.round_(self.longitude, 1)
        lat = np.round_(self.latitude, 1)
        wind = np.array(self.intens).astype(int).tolist()
        result = zip(lon, lat, wind)
        for r in result:
            cursor.execute(sql_tpl, (sim_id, user_id) + r)
        conn.commit()
        cursor.close()

if __name__ == '__main__':
    import time
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs

    total_time = 0

    def get_colors_sshws(wind_speed):
        #Return default SSHWS category color scale
        if wind_speed < 5:
            return '#CCCCCC'
        elif 5 <= wind_speed < 34:
            return '#8FC2F2' #'#7DB7ED'
        elif 34 <= wind_speed < 64:
            return '#3185D3'
        elif 64 <= wind_speed < 83:
            return '#FFFF00'
        elif 83 <= wind_speed < 96:
            return '#FF9E00'
        elif 96 <= wind_speed < 113:
            return '#DD0000'
        elif 113 <= wind_speed < 137:
            return '#FF00FC'
        else:
            return '#8B0088'

    #plt.plot(s.intens)
    proj = ccrs.PlateCarree()
    ax = plt.axes(projection=ccrs.PlateCarree(central_longitude=180))
    for i in range(50):
        start = time.time()
        s = Storm()
        s.run()
        end = time.time()
        total_time += end - start
        lon = np.array(s.longitude)
        lat = np.array(s.latitude)
        intens = np.array(s.intens)
        data = np.array(s.intens)
        for idx in range(len(data) - 1):
            lat0 = s.latitude[idx]
            lon0 = s.longitude[idx]
            lat1 = s.latitude[idx + 1]
            lon1 = s.longitude[idx + 1]
            its = s.intens[idx]
            c = get_colors_sshws(its)
            ax.plot([lon0, lon1], [lat0, lat1], color=c, transform=proj)
    ax.coastlines('50m')
    print(f'Total time {total_time}s Average time {total_time / 50}s')
    #ax.set_global()
    plt.show()
    #db = sqlite3.connect(r'D:\酷Q Pro\data\image\tcsim\Track.db')
    #s.to_database(db, 1, 2)