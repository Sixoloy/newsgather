#-*- encoding:utf-8 -*-
from __future__ import print_function

import sys
import jieba
try:
    reload(sys)
    sys.setdefaultencoding('utf-8')
except:
    pass

import codecs
from newsgather import TextRankSentence

text = "我吃苹果。我吃苹果。"
textrank = TextRankSentence()

textrank.analyze(text=text, lower=True, window=2, source = 'all_filters')   # py2中text必须是utf8编码的str或者unicode对象，py3中必须是utf8编码的bytes或者str对象

print( '关键词：' )
for item in textrank.get_keywords(20, word_min_len=2):
    print(item.word, item.weight)

print()
print( '关键短语：' )
for phrase in textrank.get_keyphrases(keywords_num=20, min_occur_num= 1):
    print(phrase)


print()
print( '摘要：' )
for item in textrank.get_key_sentences(num=3):
    print(item.index, item.weight, item.sentence)

print( '分词' )
print (textrank.get_words())

a = [1, 3, 45]
b = [2]

for i in xrange(1, 2):
    print (i)