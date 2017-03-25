#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Created on 2017-01-02 19:43:56
# Project: news



from pyspider.libs.base_handler import *
from datetime import datetime
from datetime import timedelta
import sqlite3 as sqlite
import socket

reload(sys)
sys.setdefaultencoding('utf-8')


DELTA = 2
DBADDR = '/home/sixoloy/data/my_result.db'
SADDR = '/home/sixoloy/data/news.d'

class Handler(BaseHandler):
    crawl_config = {
        'itag': 'v4'
    }

    def create_urls(self):
        days = MyDate.get_days()
        return ['http://www.chinanews.com/scroll-news/gj/%04d/%02d%02d/news.shtml' %(int(day[0]), int(day[1]), int(day[2])) for day in days]
    
    @every(minutes = 60)
    def on_start(self):

        urls = self.create_urls()
        for url in urls[:-1]:
            self.crawl(url, auto_recrawl=False, callback=self.index_page)
        self.crawl(urls[-1], age=5 * 60, auto_recrawl=True, callback=self.index_page)
        
    def index_page(self, response):
        for each in response.doc('.dd_bt > a').items():
            self.crawl(each.attr.href, callback=self.detail_page)

    @config(age=-1)
    def detail_page(self, response):
        
        url = response.url
        
        t_type = 'video' if 'shipin' in url else 'text'
        
        keywords = response.doc('meta[name="keywords"]').attr.content
        
        description = response.doc('meta[name="description"]').attr.content
        
        text = [each.text() for each in response.doc('.left_zw > p').items()]
        text = '\n'.join(text)
        
        
        return {
            "url": url,
            "title": response.doc('title').text()[:-4],
            "date_time": "%s %s" %(response.doc('#newsdate').attr.value, response.doc('#newstime').attr.value),
            "type": t_type,
            "keywords": keywords,
            "description": description,
            "content": text
        }
    
    def on_result(self, result):
        try:
            # store to sqlite
            con = sqlite.connect(DBADDR)
            con.isolation_level = None
            c = con.cursor()

            if not result:
                return

            t = (result['date_time'], result['url'], \
                result['title'], result['content'], \
                result['type'], None, \
                None)

            c.execute('INSERT INTO news_table VALUES (?, ?, ?, ?, ?, ?, ?)', t)
            con.commit()
            con.close()
            
            # call background process
            s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            s.sendto(result['date_time'], SADDR)
            s.close()
            
        except Exception,e:
            print Exception, ":", e
            

    
class MyDate(object):
    daysPerYear_normal = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    daysPerYear_leap = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    @staticmethod
    def get_today():
        return datetime.today()
        
    @staticmethod
    def get_lastday():
        return MyDate.get_today() - timedelta(days = DELTA)
    
    @classmethod
    def get_days(cls):
        today = cls.get_today()
        lastday = cls.get_lastday()
        daysPerYear = cls.daysPerYear_normal
        
        #judge leap_year or not
        year = int(cls.get_today().year)

        if (year % 4 == 0 and year % 100 != 0) or year % 400  == 0:
            daysPerYear = daysPerYear_leap
        
        result = []
        
        
        if lastday.month == today.month:
            for day in xrange(lastday.day, today.day + 1):
                result.append((lastday.year, lastday.month, day))
        else:

            #last month
            for day in xrange(lastday.day, daysPerYear[lastday.month - 1] + 1):
                result.append((lastday.year, lastday.month, day))

            #current year 
            for day in xrange(1, today.day + 1):
                result.append((today.year, today.month, day))
      
        return result