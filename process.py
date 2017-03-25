# -*-encoding:utf8 -*-

import os
import jieba
import SocketServer
from newsgather import Cluster
from newsgather.util import *

SADDR = '/home/sixoloy/data/news.d'
TITLE_WEIGHT = 3
THETA = 0.3
DB_CONFIG = {
  'user': 'root',
  'password': '88955211',
  'host': '127.0.0.1',
  'database': 'news',
  'raise_on_warnings': True,
  'autocommit': True
}

class MyUDPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        print data

        cnx, c = connect_db(DB_CONFIG)
        c.execute('SELECT * FROM news_table WHERE date_time = ?', (data,))
        cur_news = c.fetchone()
        c.execute('SELECT * FROM news_table WHERE type = "text"')
        news = list(c.fetchall())
        news = [dict(zip(c.column_names, new)) for new in news]

        cluster = Cluster(news, cnx, TITLE_WEIGHT, THETA)
        cluster.modelize()
        cluster.handle_news(cur_news)
        cnx.close()

class ForkedUnixUDPServer(SocketServer.ForkingMixIn, SocketServer.UnixDatagramServer):
    pass

if __name__ == '__main__':

    jieba.load_userdict('./dict_military.dict')

    # process storage
    cnx, c = connect_db(DB_CONFIG)
    c.execute('SELECT * FROM news_table WHERE '
              'isprocessed = 0 '
              'AND type = "text"'
              'AND title <> ""'
              'AND content <> ""')
    news = list(c.fetchall())
    news = [dict(zip(c.column_names, new)) for new in news]

    print("开始预处理数据库中的新闻...")
    cluster = Cluster(news, cnx, TITLE_WEIGHT, THETA)
    cluster.modelize()
    cluster.clustering()

    cnx.close()
    print("预聚类处理完成...")

    # call background process
    if os.path.exists(SADDR):
        os.unlink(SADDR)

    print("开始接收新闻...")
    server = ForkedUnixUDPServer(SADDR, MyUDPHandler)
    server.serve_forever()

