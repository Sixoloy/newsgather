# -*- encoding:utf-8 -*-

import sqlite3 as sqlite
import os
import sys
import signal
import socket
import jieba
from newsgather import TextRank4Sentence
from sklearn.feature_extraction.text import TfidfTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

text = ["中国", "日本"]

jieba.add_word('军演', 10)
jieba.add_word('中俄')
jieba.load_userdict('./dict_military.dict')

textrank = TextRank4Sentence()
textrank.analyze(text=text[0], lower=True, window=2, source='all_filters')

words = []
words.append(' '.join(textrank.get_words()))

textrank.analyze(text=text[1], lower=True, window=2, source='all_filters')
words.append(' '.join(textrank.get_words()))

vectorizer = CountVectorizer()  # 该类会将文本中的词语转换为词频矩阵，矩阵元素a[i][j] 表示j词在i类文本下的词频
transformer = TfidfTransformer()  # 该类会统计每个词语的tf-idf权值
x = vectorizer.fit_transform(words)
l = vectorizer.get_feature_names()



print str(l).decode('unicode escape')
print x.toarray()

x = transformer.fit_transform(x.toarray())


print x.toarray()