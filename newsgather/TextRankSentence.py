#-*- encoding:utf-8 -*-
"""
@author:   letian
@homepage: http://www.letiantian.me
@github:   https://github.com/someus/
"""
from __future__ import (absolute_import, division,
                        unicode_literals)

import networkx as nx
import numpy as np

from . import util
from .Segmentation import Segmentation

class TextRankSentence(object):
    
    def __init__(self, stop_words_file = None, 
                 allow_speech_tags = util.allow_speech_tags,
                 delimiters = util.sentence_delimiters):
        """
        Keyword arguments:
        allow_speech_tags   --  list 保留词的词性列表，筛选掉无效的词
        stop_words_file     --  str，停止词文件路径，若不是str则是使用默认停止词文件
        delimiters          --  默认值是`?!;？！。；…\n`，用来将文本拆分为句子。
        
        Object Var:
        self.sentences               --  由句子组成的列表。
        self.words_no_filter         --  对sentences中每个句子分词而得到的两级列表。
        self.words_no_stop_words     --  去掉words_no_filter中的停止词而得到的两级列表。
        self.words_all_filters       --  保留words_no_stop_words中指定词性的单词而得到的两级列表。
        """
        self.text = ''
        self.kewwords = None

        self.seg = Segmentation(stop_words_file=stop_words_file,
                                allow_speech_tags=allow_speech_tags,
                                delimiters=delimiters)
        
        self.sentences = None
        self.words_no_filter = None     # 2维列表
        self.words_no_stop_words = None
        self.words_all_filters = None
        
        self.key_sentences = None
        
    def analyze(self, text,
                window = 2,
                lower = False, 
                vertex_source = 'all_filters',
                edge_source = 'no_stop_words',
                source = 'no_stop_words', 
                sim_func = util.get_similarity,
                pagerank_config = {'alpha': 0.85,}):
        """
        Keyword arguments:
        text                 --  文本内容，字符串。
        window               --  窗口大小，int，用来构造单词之间的边。默认值为2。
        vertex_source        --  选择使用words_no_filter, words_no_stop_words, words_all_filters中的哪一个来构造pagerank对应的图中的节点。
                                 默认值为`'all_filters'`，可选值为`'no_filter', 'no_stop_words', 'all_filters'`。关键词也来自`vertex_source`。
        edge_source          --  选择使用words_no_filter, words_no_stop_words, words_all_filters中的哪一个来构造pagerank对应的图中的节点之间的边。
                                 默认值为`'no_stop_words'`，可选值为`'no_filter', 'no_stop_words', 'all_filters'`。边的构造要结合`window`参数。
        lower                --  是否将文本转换为小写。默认为False。
        source               --  选择使用words_no_filter, words_no_stop_words, words_all_filters中的哪一个来生成句子之间的相似度。
                                 默认值为`'all_filters'`，可选值为`'no_filter', 'no_stop_words', 'all_filters'`。
        sim_func             --  指定计算句子相似度的函数。
        """
        
        self.text = text
        self.keywords = []
        self.key_sentences = []
        self.graph = None

        result = self.seg.segment(text=text, lower=lower)
        self.sentences = result.sentences
        self.words_no_filter = result.words_no_filter
        self.words_no_stop_words = result.words_no_stop_words
        self.words_all_filters   = result.words_all_filters

        options = ['no_filter', 'no_stop_words', 'all_filters']
        if source in options:
            _source = result['words_'+source]
        else:
            _source = result['words_no_stop_words']


        if vertex_source in options:
            _vertex_source = result['words_'+vertex_source]
        else:
            _vertex_source = result['words_all_filters']

        if edge_source in options:
            _edge_source   = result['words_'+edge_source]
        else:
            _edge_source   = result['words_no_stop_words']

        self.keywords = util.sort_words(_vertex_source, _edge_source, window = window, pagerank_config = pagerank_config)
        self.key_sentences = util.sort_sentences(sentences = self.sentences,
                                                 words     = _source,
                                                 sim_func  = sim_func,
                                                 pagerank_config = pagerank_config)

    def get_keywords(self, num = 6, word_min_len = 1):
        """获取最重要的num个长度大于等于word_min_len的关键词。

        Return:
        关键词列表。
        """
        result = []
        count = 0
        for item in self.keywords:
            if count >= num:
                break
            if len(item.word) >= word_min_len:
                result.append(item)
                count += 1
        return result
    
    def get_keyphrases(self, keywords_num = 12, min_occur_num = 2): 
        """获取关键短语。
        获取 keywords_num 个关键词构造的可能出现的短语，要求这个短语在原文本中至少出现的次数为min_occur_num。

        Return:
        关键短语的列表。
        """
        keywords_set = set([ item.word for item in self.get_keywords(num = keywords_num, word_min_len = 1)])
        keyphrases = set()
        for sentence in self.words_no_filter:
            one = []
            for word in sentence:
                if word in keywords_set:
                    one.append(word)
                else:
                    if len(one) >  1:
                        keyphrases.add(''.join(one))
                    if len(one) == 0:
                        continue
                    else:
                        one = []
            # 兜底
            if len(one) >  1:
                keyphrases.add(''.join(one))

        return [phrase for phrase in keyphrases 
                if self.text.count(phrase) >= min_occur_num]

    def get_key_sentences(self, num = 6, sentence_min_len = 6, key = 'weight'):
        """获取最重要的num个长度大于等于sentence_min_len的句子用来生成摘要。

        Return:
        多个句子组成的列表。
        """
        result = []
        count = 0
        for item in self.key_sentences:
            if count >= num:
                break
            if len(item['sentence']) >= sentence_min_len:
                result.append(item)
                count += 1
        result = sorted(result, key = lambda item: item[key])

        return result
    
    def get_words(self, type = 'no_stop_words'):
        """返回字符串形式的分词结果
            
        """
        result_words = []
        words_lists = getattr(self, 'words_' + type)
        return sum(words_lists, [])

if __name__ == '__main__':
    pass