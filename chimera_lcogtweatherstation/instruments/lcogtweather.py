import logging
import time

from astropy import units
from chimera.core.exceptions import OptionConversionException
from chimera.core.lock import lock
from chimera.instruments.weatherstation import WeatherBase
from chimera.interfaces.weatherstation import WSValue
# this imports are for lcgot scraper and filter
import json
import re
import requests
from bs4 import BeautifulSoup


class LCOGTWeather(WeatherBase):
    __config__ = {"model": "LCOGT telescope weather station",
                  "check_interval": 3 * 60,  # in seconds
                  "uri": 'http://telops.lcogt.net/#',
                  }

    def __init__(self):
        WeatherBase.__init__(self)
        self._last_check = 0
        self._time_ws = None

        # logging.
        # put every logger on behalf of chimera's logger so
        # we can easily setup levels on all our parts

        logName = self.__module__
        if not logName.startswith("chimera."):
            logName = "chimera." + logName + " (%s)" % logName

        self.log = logging.getLogger(logName)

    def clear_data(self, name, data):

        # removes html tags from data

        # print"in clear_data"

        a = re.sub('<td><b>', '', str(data))

        b = re.sub('</b></td>', '', a)

        if name == 'insolation':
            c = re.sub('<span style="color:red;', '', b)
            f = re.sub('</span>', '', c)
            f = re.sub('">', '', f)
            b = f



        elif name == 'moon':
            d = re.sub('<span>', '', b)
            e = re.sub('</span></td>', '', d)
            g = re.sub('class=', '', e)
            h = re.sub('<td "moon', '', g)
            i = re.sub('">', '', h)
            b = i

        elif name == 'time':
            c = re.sub('As of <b>', '', b)
            d = re.sub('</b>', '', c)
            b = d

        # print "*****************************************************"
        # print"value of b:",b
        return b

    def card_to_degree(self, card):
        card.strip('')
        # print "card:", card,card.__len__(), type(card)


        deg_out = 1000.0

        translate = {'N': 0.0, 'NNE': 22.5, 'NE': 45.0, 'ENE': 67.5, 'E': 90.0, 'ESE': 112.5, 'SE': 135.0, 'SSE': 157.5,
                     'S': 180.0, 'SSW': 202.5, 'SW': 225.0, 'WSW': 247.5, 'W': 270.0, 'WNW': 292.5, 'NW': 315.0,
                     'NNW': 337.5}
        for key in translate:

            # print "key:",key ,type(key),len(key), translate[key], type(translate[key])

            if key == card:
                deg_out = translate[key]
                # print "deg_out:", deg_out
                return deg_out

        # print "wind direction not found"
        return False

    def scrape(self):
        self.client = requests.session()

        self.a = self.client.get('http://telops.lcogt.net/#')

        latest_comet_queue_id = int(re.findall('Telops.latest_comet_queue_id = (.+);', self.a.text)[0])

        self.r = self.client.post(
            url='http://telops.lcogt.net/dajaxice/netnode.refresh/',
            data={'argv': json.dumps({"latest": latest_comet_queue_id})},
            headers={
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate',
                "Content-Type": "application/x-www-form-urlencoded",
                'Host': 'telops.lcogt.net',
                "Origin": "http://telops.lcogt.net",
                "Referer": "http://telops.lcogt.net/",
                'X-CSRFToken': None,
                'X-Requested-With': 'XMLHttpRequest',

            },
            cookies={'pushstate': 'pushed'}

        )

        return json.loads(self.r.text)

    @lock
    def _check(self):

        if time.time() >= self._last_check + self["check_interval"]:
            try:

                data = self.scrape()

                # print 'data is:',data, type(data)

                temperature = []
                dew_point = []
                pressure = []
                humidity = []
                wind = []
                insolation = []
                brightness = []
                transparency = []
                ok_to_open = []
                interlock_reason = []
                moon = []
                last_time = ''

                for val in data:
                    if 'id' in val.keys():
                        # print 'id', val['id']



                        if val['id'] == '#site-lsc-ssb-system-Weather-tip':
                            line = val['val']
                            # print "line is",line
                            html = BeautifulSoup(line, 'lxml')
                            temperature.append(html.find_all('td')[1])
                            dew_point.append(html.find_all('td')[3])
                            pressure.append(html.find_all('td')[5])
                            humidity.append(html.find_all('td')[7])
                            wind.append(html.find_all('td')[9])
                            insolation.append(html.find_all('td')[11])
                            brightness.append(html.find_all('td')[13])
                            transparency.append(html.find_all('td')[15])
                            ok_to_open.append(html.find_all('td')[17])

                            try:
                                moon.append(html.find_all('td')[21])
                                interlock_reason.append(html.find_all('td')[19])


                            except IndexError:
                                moon.append(html.find_all('td')[19])
                                interlock_reason.append("none")

                        if val['id'] == '#site-tfn-time':
                            last_time = val['val']
                            # print "time is:", last_time

                temp_out = float(self.clear_data('temperature', temperature[temperature.__len__() - 1])[:-3])
                # print "Temperature:" + str(temp_out)

                hum_out = float(self.clear_data('humidity', humidity[humidity.__len__() - 1])[:-1])
                # print "Humidity:" + str(hum_out)

                win = self.clear_data('wind', wind[wind.__len__() - 1])
                wind_speed_out = float(win.split('m/s')[0])
                wind_dir_out = win.split('m/s')[1]
                # print "Wind speed:" +str(wind_speed_out)
                # print "Wind direction:" + wind_dir_out

                press_out = float(self.clear_data('pressure', pressure[pressure.__len__() - 1])[:-4])
                # print "Pressure:" + str(press_out)

                time_out = self.clear_data('time', last_time)
                # print "Time:"+ str(time_out)



            except TypeError:
                return False

            self._time_ws = time_out
            self._temperature = temp_out
            self._humidity = hum_out
            self._wind_speed = wind_speed_out
            self._wind_dir = self.card_to_degree(wind_dir_out.lstrip())
            self._pressure = press_out
            self._last_check = time.time()
            return True
        else:
            return True

    def obs_time(self):
        ''' Returns a string with UT date/time of the meteorological observation
        '''
        return self._time_ws

    def humidity(self, unit_out=units.pct):

        if unit_out not in self.__accepted_humidity_units__:
            raise OptionConversionException("Invalid humidity unit %s." % unit_out)

        if self._check():
            return WSValue(self.obs_time(), self._convert_units(self._humidity, units.pct, unit_out), unit_out)
        else:
            return False

    def temperature(self, unit_out=units.Celsius):

        if unit_out not in self.__accepted_temperature_units__:
            raise OptionConversionException("Invalid temperature unit %s." % unit_out)

        if self._check():
            return WSValue(self.obs_time(), self._convert_units(self._temperature, units.Celsius, unit_out), unit_out)
        else:
            return False

    def wind_speed(self, unit_out=units.meter / units.second):

        if self._check():
            return WSValue(self.obs_time(), self._convert_units(self._wind_speed, (units.m / units.s), unit_out),
                           unit_out)
        else:
            return False

    def wind_direction(self, unit_out=units.degree):

        if self._check():
            return WSValue(self.obs_time(), self._convert_units(self._wind_dir, units.deg, unit_out), unit_out)
        else:
            return False

    def dew_point(self, unit_out=units.Celsius):
        return NotImplementedError()

    def pressure(self, unit_out=units.Pa):
        if self._check():
            return WSValue(self.obs_time(), self._convert_units(self._pressure, units.cds.mmHg, unit_out), unit_out)
        else:
            return False

    def rain(self, unit_out=units.imperial.inch / units.hour):
        return NotImplementedError()

    def getMetadata(self, request):

        return [('ENVMOD', str(self['model']), 'Weather station Model'),
                ('ENVTEM', self.temperature(), '[degC] Weather station temperature'),
                ('ENVHUM', self.humidity(), '[%] Weather station relative humidity'),
                ('ENVWIN', self.wind_speed(), '[m/s] Weather station wind speed'),
                ('ENVDIR', self.wind_direction(), '[deg] Weather station wind direction'),
                ('ENVPRE', self.pressure(), '[mmHg] Weather station air pressure'),
                ('ENVDAT', self.obs_time(), 'UT time of the meteo observation')
                ]


if __name__ == '__main__':
    test = LCOGTWeather()
    test.__start__()
    test._check()
    print test.getMetadata(None)
