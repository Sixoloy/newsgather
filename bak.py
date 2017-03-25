# -*-encoding:utf8 -*-
import jieba
import SocketServer
from newsgather import TextRank4Sentence, util
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from newsgather.util import *

SADDR = '/home/sixoloy/data/news.d'
DBADDR = '/home/sixoloy/data/my_result.db'
title_weight = 3
theta = 0.5


def enhance(news, allwords, model):
    pass

def modelize(row_news):
    # preprocess each news
    for new in news:
        words_db = process_each_row(new)

        corpus.append(words_db)

        # calculate word frequency in titles
        textrank.analyze(text=new['title'], lower=True, window=2, source='all_filters')
        title_words = [' '.join(textrank.get_words())]

        vectorizer = CountVectorizer()
        frequency = vectorizer.fit_transform(title_words).toarray()[0]
        word_name = vectorizer.get_feature_names()

        title_frequency.append(dict(zip(word_name, frequency)))

    vectorizer = CountVectorizer()
    frequency = vectorizer.fit_transform(corpus).toarray()
    allWords = vectorizer.get_feature_names()

    print("开始聚类数据库中的新闻...")

    # enhence title frequency for each news
    for index in xrange(len(news)):
        for item in title_frequency[index]:
            item_index = vectorizer.vocabulary_.get(item)
            if not item_index:
                break
            item_frequency = title_frequency[index][item]
            frequency[index][item_index] = frequency[index][item_index] + item_frequency * (title_weight - 1)

    transformer = TfidfTransformer()
    trainedTfidf = transformer.fit_transform(frequency).toarray()


def process_each_row(cur_news):
    """对每条新闻进行分词并进行文本摘要和文本聚类"""
    textrank.analyze(cur_news['content'], lower=False, window=2, source='all_filters')
    words = textrank.get_words()
    keyphrases = textrank.get_keyphrases(keywords_num=3, min_occur_num=1)
    keywords = textrank.get_keywords(6, 2)
    description = textrank.get_key_sentences(3, 0, 'index')

    words_db = ' '.join(words)
    keywords_db = ' '.join([item.word for item in keywords])
    keyphrases_db = ' '.join(keyphrases)
    description_db = ' '.join([item.sentence for item in description])

    con,c = connect_db(DBADDR)
    t = (words_db, keywords_db, keyphrases_db, description_db, new['date_time'])
    c.execute('UPDATE news_table SET words = ?, keywords = ?, keyphrases = ?, description = ? WHERE date_time = ?', t)
    con.close()

    return words_db

class MyUDPHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        data = self.request[0].strip()
        print data

        con, c = connect_db(DBADDR)
        c.execute('SELECT * FROM news_table WHERE date_time = ?', (data,))
        cur_news = c.fetchone()[0]
        con.close()
        process_each_row(cur_news)


        con, c = connect_db(DBADDR)
        c.execute('SELECT * FROM news_table WHERE type = "text"')
        news = list(c.fetchall())
        con.close()

        corpus = []
        indice = -1
        for i, new in enumerate(news):
            corpus.append(new['words'])
            if new['date_time'] == data:
                indice = i

        vectorizer = CountVectorizer()
        frequency = vectorizer.fit_transform(corpus).toarray()
        allWords = vectorizer.get_feature_names()

        # enhence title frequency for each news
        for index in xrange(len(news)):
            for item in title_frequency[index]:
                item_index = vectorizer.vocabulary_.get(item)
                if not item_index:
                    break
                item_frequency = title_frequency[index][item]
                frequency[index][item_index] = frequency[index][item_index] + item_frequency * (title_weight - 1)

        transformer = TfidfTransformer()
        trainedTfidf = transformer.fit_transform(frequency).toarray()

        cos_sim = np.array(cosine_similarity(trainedTfidf[indice].reshape(1, -1), trainedTfidf))[0]
        max_index = np.argmax(cos_sim)

        print cos_sim

        con, c = connect_db()
        # 加入簇
        if cos_sim[max_index] >= theta:
            t = (news[max_index]['date_time'],)
            c.execute('SELECT clusterID FROM news_table WHERE date_time = ?', t)
            clusterID = c.fetchone()[0]

            t = (clusterID,)
            c.execute('SELECT title FROM news_table WHERE clusterID = ?', t)
            titles = ' '.join(list(c.fetchall()))

            textrank.analyze(text=titles, lower=True, window=2, source='all_filters')
            title_words = [' '.join(textrank.get_words('all_filters'))]
            weight = transformer.transform(vectorizer.transform(title_words)).toarray()[0]
            description_indice = np.argmax(weight)
            description = allWords[description_indice]

            t = (description, clusterID)
            c.execute('UPDATE cluster_table SET keywords = ? WHERE clusterID = ?', t)

            t = (clusterID, news[index]['date_time'])
            c.execute('UPDATE news_table SET isprocessed = 0, clusterID = ? WHERE date_time = ?', t)

        # 新建一个簇
        else:
            textrank.analyze(text=news[index]['title'], lower=True, window=2, source='all_filters')
            title_words = [' '.join(textrank.get_words('all_filters'))]
            weight = transformer.transform(vectorizer.transform(title_words)).toarray()[0]
            description_indice = np.argmax(weight)
            description = allWords[description_indice]

            t = (None, description)
            c.execute('INSERT INTO cluster_table VALUES(?, ?)', t)
            c.execute('SELECT last_insert_rowid()')
            clusterID = c.fetchone()[0]
            t = (clusterID, news[index]['date_time'])
            c.execute('UPDATE news_table SET isprocessed = 0, clusterID = ? WHERE date_time = ?', t)
        con.close()



class ForkedUnixUDPServer(SocketServer.ForkingMixIn, SocketServer.UnixDatagramServer):
    pass

if __name__ == '__main__':

    jieba.load_userdict('./dict_military.dict')
    textrank = TextRank4Sentence()

    # process storage
    con, c = connect_db(DBADDR)

    # cluster initial
    corpus = []
    title_frequency = []

    news = list(c.execute('SELECT * FROM news_table WHERE isprocessed = 0 and type = "text" '))
    con.close()

    print("开始预处理数据库中的新闻...")

    # preprocess each news
    for new in news:

        words_db = process_each_row(new)

        corpus.append(words_db)

        # calculate word frequency in titles
        textrank.analyze(text = new['title'], lower = True, window = 2, source ='all_filters')
        title_words = [' '.join(textrank.get_words())]

        vectorizer = CountVectorizer()
        frequency = vectorizer.fit_transform(title_words).toarray()[0]
        word_name = vectorizer.get_feature_names()

        title_frequency.append(dict(zip(word_name, frequency)))

    vectorizer = CountVectorizer()
    frequency = vectorizer.fit_transform(corpus).toarray()
    allWords = vectorizer.get_feature_names()

    print("开始聚类数据库中的新闻...")

    # enhence title frequency for each news
    for index in xrange(len(news)):
        for item in title_frequency[index]:
            item_index = vectorizer.vocabulary_.get(item)
            if not item_index:
                break
            item_frequency = title_frequency[index][item]
            frequency[index][item_index] = frequency[index][item_index] + item_frequency * (title_weight - 1)

    transformer = TfidfTransformer()
    trainedTfidf = transformer.fit_transform(frequency).toarray()

    print("开始聚类数据库中的新闻...")

    # clustering
    for index in xrange(len(news)):
        # 第一篇文章独立分类
        if index == 0:
            # 找出聚类的描述（找tfidf最高的词）
            textrank.analyze(text=news[index]['title'], lower=True, window=2, source='all_filters')
            title_words = [' '.join(textrank.get_words('all_filters'))]
            weight = transformer.transform(vectorizer.transform(title_words)).toarray()[0]
            description_indice = np.argmax(weight)
            description = allWords[description_indice]
            # description = ' '.join([allWords[indice] for indice in description_indice])

            con, c = connect_db(DBADDR)
            t = (None, description)
            c.execute('DELETE FROM cluster_table')
            c.execute('UPDATE sqlite_sequence SET seq = 0 WHERE name = "cluster1_table"')
            c.execute('INSERT INTO cluster_table VALUES(?, ?)', t)
            t = (news[index]['date_time'],)
            c.execute('UPDATE news_table SET isprocessed = 0, cluster1ID = 1 WHERE date_time = ?', t)
            con.close()

        # 其他的文章和之前已经完成聚类的文章进行相似度检测
        else:
            cos_sim = np.array(cosine_similarity(trainedTfidf[index].reshape(1, -1), trainedTfidf[:index]))[0]
            max_index = np.argmax(cos_sim)

            print cos_sim

            con, c = connect_db()
            # 加入簇
            if cos_sim[max_index] >= theta:
                t = (news[max_index]['date_time'],)
                c.execute('SELECT cluster1ID FROM news_table WHERE date_time = ?', t)
                clusterID = c.fetchone()[0]

                t = (clusterID,)
                c.execute('SELECT title FROM news_table WHERE cluster1ID = ?', t)
                titles = ' '.join(list(c.fetchall()))

                textrank.analyze(text=titles, lower=True, window=2, source='all_filters')
                title_words = [' '.join(textrank.get_words('all_filters'))]
                weight = transformer.transform(vectorizer.transform(title_words)).toarray()[0]
                description_indice = np.argmax(weight)
                description = allWords[description_indice]

                t = (description, clusterID)
                c.execute('UPDATE cluster_table SET keywords = ? WHERE cluster1ID = ?', t)

                t = (clusterID, news[index]['date_time'])
                c.execute('UPDATE news_table SET isprocessed = 0, cluster1ID = ? WHERE date_time = ?', t)

            # 新建一个簇
            else:
                textrank.analyze(text=news[index]['title'], lower=True, window=2, source='all_filters')
                title_words = [' '.join(textrank.get_words('all_filters'))]
                weight = transformer.transform(vectorizer.transform(title_words)).toarray()[0]
                description_indice = np.argmax(weight)
                description = allWords[description_indice]
                # description_indice = np.argsort(-weight)[:5]
                # description = ' '.join([allWords[indice] for indice in description_indice])

                t = (None, description)
                c.execute('INSERT INTO cluster1_table VALUES(?, ?)', t)
                c.execute('SELECT last_insert_rowid()')
                clusterID = c.fetchone()[0]
                t = (clusterID, news[index]['date_time'])
                c.execute('UPDATE news_table SET isprocessed = 0, cluster1ID = ? WHERE date_time = ?', t)
            con.close()

    # call background process
    if os.path.exists(SADDR):
        os.unlink(SADDR)

    server = ForkedUnixUDPServer(SADDR, MyUDPHandler)
    server.serve_forever()

# !/usr/bin/env python
# -*- encoding: utf-8 -*-
# Created on 2017-01-02 19:43:56
# Project: news



from pyspider.libs.base_handler import *
from datetime import datetime
from datetime import timedelta
import mysql.connector
import socket

reload(sys)
sys.setdefaultencoding('utf-8')

DELTA = 30
DBADDR = '/home/sixoloy/data/my_result.db'
SADDR = '/home/sixoloy/data/news.d'
DB_CONFIG = {
    'user': 'root',
    'password': '88955211',
    'host': '127.0.0.1',
    'database': 'news',
    'raise_on_warnings': True
}


class Handler(BaseHandler):
    crawl_config = {
        'itag': 'v8'
    }

    def create_urls(self):
        days = MyDate.get_days()
        return [
            'http://www.chinanews.com/scroll-news/gj/%04d/%02d%02d/news.shtml' % (int(day[0]), int(day[1]), int(day[2]))
            for day in days]

    @every(minutes=60)
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
            "date_time": "%s %s" % (response.doc('#newsdate').attr.value, response.doc('#newstime').attr.value),
            "type": t_type,
            "keywords": keywords,
            "description": description,
            "content": text
        }

    def on_result(self, result):

        if not result:
            return

        # store to sqlite
        cnx = mysql.connector.connect(**DB_CONFIG)
        c = cnx.cursor()

        t = (result['date_time'], result['url'], \
             result['title'], result['content'], \
             result['type'], 0,
             None, None, None, None, None, None)

        c.execute('INSERT INTO news_table VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', t)
        cnx.commit()
        cnx.close()

        # call background process
        if result['type'] == 'text':
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                s.sendto(result['date_time'], SADDR)
                s.close()
            except:
                print "未开启socket接收端..."


class MyDate(object):
    daysPerYear_normal = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    daysPerYear_leap = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    @staticmethod
    def get_today():
        return datetime.today()

    @staticmethod
    def get_lastday():
        return MyDate.get_today() - timedelta(days=DELTA)

    @classmethod
    def get_days(cls):
        today = cls.get_today()
        lastday = cls.get_lastday()
        daysPerYear = cls.daysPerYear_normal

        # judge leap_year or not
        year = int(cls.get_today().year)

        if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0:
            daysPerYear = daysPerYear_leap

        result = []

        if lastday.month == today.month:
            for day in xrange(lastday.day, today.day + 1):
                result.append((lastday.year, lastday.month, day))
        else:

            # last month
            for day in xrange(lastday.day, daysPerYear[lastday.month - 1] + 1):
                result.append((lastday.year, lastday.month, day))

            # current year
            for day in xrange(1, today.day + 1):
                result.append((today.year, today.month, day))

        return result
