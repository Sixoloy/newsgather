# -*-encoding:utf8 -*-

from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from gensim import corpora, models, similarities
from . import TextRankSentence
from .util import *

class Cluster(object):
    def __init__(self, row_news, connection, n_cell_clusters = 4, title_weight = 3, theta = 0.25):
        self.news = row_news
        self.db_connection = connection
        self.db_cursor = connection.cursor()
        self.textrank = TextRankSentence()
        self.title_weight = title_weight
        self.theta = theta
        self.vectorizer = None
        self.frequency = None
        self.allwords = None
        self.trainedTFIDF = None
        self.n_clusters = 0
        self.n_cell_clusters = n_cell_clusters
        self.km = KMeans(n_clusters = n_cell_clusters, n_jobs = -1)

    def __process_each_row(self, cur_news):
        """对每条新闻进行分词并进行文本摘要和文本聚类"""
        self.textrank.analyze(cur_news['content'], lower=False, window=2, source='all_filters')
        words = self.textrank.get_words()
        keyphrases = self.textrank.get_keyphrases(keywords_num=3, min_occur_num=1)
        keywords = self.textrank.get_keywords(6, 2)
        description = self.textrank.get_key_sentences(3, 0, 'index')

        words_db = ' '.join(words)
        keywords_db = ' '.join([item.word for item in keywords])
        keyphrases_db = ' '.join(keyphrases)
        description_db = ' '.join([item.sentence for item in description])

        c = self.db_cursor
        t = (words_db, keywords_db, keyphrases_db, description_db, cur_news['date_time'])
        c.execute('UPDATE news_table SET words = %s, keywords = %s, keyphrases = %s, description = %s WHERE date_time = %s',
                  t)

        return words_db

    def __find_most_similar(self, sample, model):
        cos_sim = np.array(cosine_similarity(sample, model))[0]
        max_index = np.argmax(cos_sim)
        # print cos_sim

        return max_index, cos_sim[max_index]

    def __find_description(self, text):
        self.textrank.analyze(text = text, lower = True, window = 2, source = 'all_filters')
        title_words = [' '.join(self.textrank.get_words('all_filters'))]
        weight = self.transformer.transform(self.vectorizer.transform(title_words)).toarray()[0]
        description_indice = np.argmax(weight)
        description = self.allwords[description_indice]

        return description

    def __create_cluster(self, index):
        self.n_clusters = self.n_clusters + 1
        description = self.__find_description(self.news[index]['title'])

        c = self.db_cursor
        t = (None, description)
        c.execute('INSERT INTO cluster1_table VALUES(%s, %s)', t)
        cluster1ID = c.lastrowid
        t = (cluster1ID, self.news[index]['date_time'])
        c.execute('UPDATE news_table SET cluster1ID = %s WHERE date_time = %s', t)
        self.news[index]['cluster1ID'] = cluster1ID

        return cluster1ID

    def __join_cluster(self, index, max_index):
        cluster1ID = self.news[max_index]['cluster1ID']
        news_filter = filter(lambda new: new['cluster1ID'] == cluster1ID, self.news)
        titles = " ".join([new['title'] for new in news_filter])

        c = self.db_cursor

        description = self.__find_description(titles)
        t = (description, cluster1ID)
        c.execute('UPDATE cluster1_table SET keywords = %s WHERE cluster1ID = %s', t)
        t = (cluster1ID, self.news[index]['date_time'])
        c.execute('UPDATE news_table SET cluster1ID = %s WHERE date_time = %s', t)
        self.news[index]['cluster1ID'] = cluster1ID

        return cluster1ID

    def enhance(self, news, vectorizer, frequency):
        title_frequency = []

        for new in news:
            # calculate word frequency in titles
            self.textrank.analyze(text = new['title'], lower = True, window = 2, source = 'all_filters')
            title_words = [' '.join(self.textrank.get_words())]

            __vectorizer = CountVectorizer()
            __frequency = __vectorizer.fit_transform(title_words).toarray()[0]
            word_name = __vectorizer.get_feature_names()

            title_frequency.append(dict(zip(word_name, __frequency)))

        # enhence title frequency for each news
        for index in xrange(len(news)):
            for item in title_frequency[index]:
                item_index = vectorizer.vocabulary_.get(item)
                if not item_index:
                    break
                item_frequency = title_frequency[index][item]
                frequency[index][item_index] = frequency[index][item_index] + item_frequency * (self.title_weight - 1)

        return frequency

    def modelize(self):
        # cluster initial
        print("开始建模...")
        corpus = []

        for new in self.news:
            words_db = self.__process_each_row(new)
            corpus.append(words_db)

        self.vectorizer = CountVectorizer()
        self.frequency = self.vectorizer.fit_transform(corpus).toarray()
        self.allwords = self.vectorizer.get_feature_names()

        self.frequency = self.enhance(self.news, self.vectorizer, self.frequency)
        self.transformer = TfidfTransformer()
        self.trainedTFIDF = self.transformer.fit_transform(self.frequency).toarray()

        # self.dictionary = corpora.Dictionary(corpus)
        # corpus = [self.dictionary.doc2bow(text) for text in corpus]
        # self.tfidfModel = models.TfidfModel(corpus)
        # self.trainedTFIDF = self.tfidfModel[corpus]
        #
        # self.lsiModel = models.LsiModel(self.trainedTFIDF, id2word=self.dictionary, num_topics=10)
        # self.trainedLSI = self.lsiModel[corpus]

    def clustering(self):
        # clustering
        print("开始聚类...")
        for index in xrange(len(self.news)):
            # 第一篇文章独立分类
            if index == 0:
                c = self.db_cursor
                c.execute('UPDATE news_table SET cluster1ID = null')
                c.execute('UPDATE news_table SET cluster2ID = null')
                c.execute('DELETE FROM cluster2_table')
                c.execute('DELETE FROM cluster1_table')
                c.execute('ALTER TABLE cluster1_table AUTO_INCREMENT=1')

                self.__create_cluster(index)

            # 其他的文章和之前已经完成聚类的文章进行相似度检测
            else:
                max_index, max_value = self.__find_most_similar(self.trainedTFIDF[index].reshape(1, -1),
                                                                self.trainedTFIDF[:index])

                # 加入簇
                if max_value >= self.theta:
                    self.__join_cluster(index, max_index)

                # 新建一个簇
                else:
                    self.__create_cluster(index)

        # cell clustering
        for id1 in xrange(self.n_clusters):
            self.__cell_clustering(id1 + 1)

    def __cell_clustering(self, cluster1ID):
        """需要考虑当新闻数小于4的情况"""
        cell_news_indice = [indice for indice, new in enumerate(self.news) if new['cluster1ID'] == cluster1ID]
        cell_news = [self.trainedTFIDF[indice] for indice in cell_news_indice]

        if (len(cell_news_indice) < self.n_cell_clusters):
            km = KMeans(n_clusters = len(cell_news_indice), n_jobs = -1)
            n_cell_clusters = len(cell_news_indice)
        else:
            km = self.km
            n_cell_clusters = self.n_cell_clusters

        results = km.fit_predict(cell_news)

        for i in xrange(n_cell_clusters):
            each_cell_news= [self.news[cell_news_indice[indice]] for result, indice in enumerate(results) if result == i]
            titles = " ".join([new['title'] for new in each_cell_news])
            description = self.__find_description(titles)
            c = self.db_cursor
            t = (cluster1ID, i, description)
            c.execute('INSERT INTO cluster2_table VALUES(%s, %s, %s)', t)

        for i in xrange(len(cell_news_indice)):
            c = self.db_cursor
            t = (int(results[i]), self.news[cell_news_indice[i]]['date_time'])
            c.execute('UPDATE news_table SET isprocessed = 1, cluster2ID = %s WHERE date_time = %s', t)

    def handle_news(self, cur_news):

        indice = -1
        for i, new in enumerate(self.news):
            if new['date_time'] == cur_news['date_time']:
                indice = i

        # cos_sim = np.array(cosine_similarity(self.trainedTFIDF[indice].reshape(1, -1), self.trainedTFIDF))[0]
        max_index, max_value = self.__find_most_similar(self.trainedTFIDF[indice].reshape(1, -1), self.trainedTFIDF)

        # 加入簇
        if max_value >= self.theta:
            id = self.__join_cluster(indice, max_index)

        # 新建一个簇
        else:
            id = self.__create_cluster(indice)

        self.__cell_clustering(id)