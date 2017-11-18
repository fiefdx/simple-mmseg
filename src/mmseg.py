# -*- coding: utf-8 -*-
'''
Created on 2017-11-18
@summary: mmseg
@author: fiefdx
'''

import os
import string
import math

dict_word = {}
max_word_length = 0
_curpath = os.path.normpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

def load_dict_chars(fpath):
    global max_word_length
    fp = open(fpath, "rb")
    for line in fp.readlines():
        freq, word = line.split(" ")
        word = unicode(word.strip(), "utf-8")
        dict_word[word] = (len(word), int(freq))
        if max_word_length < len(word):
            max_word_length = len(word)
    fp.close()

def load_dict_words(fpath):
    global max_word_length
    fp = open(fpath, "rb")
    for line in fp.readlines():
        _, word = line.split(" ")
        word = unicode(word.strip(), "utf-8")
        dict_word[word] = (len(word), 0)
        if max_word_length < len(word):
            max_word_length = len(word)
    fp.close()

def get_dict_word(word):
    result = dict_word.get(word)
    if result:
        return Word(word, result[1])
    return None

def load_dict():
    load_dict_chars(os.path.join(_curpath, 'chars.dic'))
    load_dict_words(os.path.join(_curpath, 'words.dic'))

class Word(object):
    def __init__(self, text = '', freq = 0):
        self.text = text
        self.freq = freq
        self.length = len(text)

class Chunk(object):
    def __init__(self, w1, w2 = None, w3 = None):
        self.words = []
        self.words.append(w1)
        if w2:
            self.words.append(w2)
        if w3:
            self.words.append(w3)

    def total_word_length(self):
        length = 0
        for word in self.words:
            length += len(word.text)
        return length

    def average_word_length(self):
        return float(self.total_word_length()) / len(self.words)

    def standard_deviation(self):
        average = self.average_word_length()
        sum_tmp = float()
        for word in self.words:
            tmp = float(len(word.text) - average)
            sum_tmp += tmp**2
        return sum_tmp

    def word_frequency(self):
        sum_tmp = float()
        for word in self.words:
            if word.length == 1:
                sum_tmp += math.log(word.freq)
        return sum_tmp

class SimpleCompare(object):
    def take_high_test(self, chunks):
        len_chunk = 0
        result = []
        for chunk in chunks:
            if chunk.total_word_length() > len_chunk:
                len_chunk = chunk.total_word_length()
                result = [chunk]
        return result

class ComplexCompare(object):
    def take_high_test(self, chunks, comparator):
        i = 1
        for j in range(1, len(chunks)):
            rlt = comparator(chunks[j], chunks[0])
            if rlt > 0:
                i = 0
            if rlt >= 0:
                chunks[i], chunks[j] = chunks[j], chunks[i]
                i += 1
        return chunks[0:i]

    # 以下四个函数是mmseg算法的四种过滤原则，核心算法
    def mmFilter(self, chunks):
        def comparator(a, b):
            return a.total_word_length() - b.total_word_length()
        return self.take_high_test(chunks, comparator)

    def lawlFilter(self, chunks):
        def comparator(a, b):
            return a.average_word_length() - b.average_word_length()
        return self.take_high_test(chunks, comparator)

    def svmlFilter(self, chunks):
        def comparator(a, b):
            return b.standard_deviation() - a.standard_deviation()
        return self.take_high_test(chunks, comparator)

    def logFreqFilter(self, chunks):
        def comparator(a, b):
            return a.word_frequency() - b.word_frequency()
        return self.take_high_test(chunks, comparator)


class Analysis(object):
    def __init__(self, text, simple = True):
        if isinstance(text, unicode):
            self.text = text
        else:
            self.text = text.decode("utf-8")
        self.simple = simple
        self.cache_size = 3
        self.pos = 0
        self.text_length = len(self.text)
        self.cache = []
        self.cache_index = 0
        self.simple_compare = SimpleCompare()
        self.complex_compare = ComplexCompare()

        for i in range(self.cache_size):
            self.cache.append([-1, Word()])

        if not dict_word:
            load_dict()

    def __iter__(self):
        while True:
            token = self.get_next_token()
            if token is None:
                raise StopIteration
            yield token

    def get_next_char(self):
        return self.text[self.pos]

    def is_chinese_char(self, character):
        return 0x4e00 <= ord(character) < 0x9fa6

    def is_ascii_char(self, character):
        if character in string.whitespace:
            return False
        elif character in string.punctuation:
            return False
        return character in string.printable

    def get_next_token(self):
        while self.pos < self.text_length:
            if self.is_chinese_char(self.get_next_char()):
                token = self.get_chinese_words()
            else:
                token = self.get_ascii_words()
            if len(token) > 0:
                return token
        return None

    def get_ascii_words(self):
        while self.pos < self.text_length:
            ch = self.get_next_char()
            if self.is_ascii_char(ch) or self.is_chinese_char(ch):
                break
            self.pos += 1
        # english start pos
        start = self.pos
        # find english word end pos
        while self.pos < self.text_length:
            ch = self.get_next_char()
            if not self.is_ascii_char(ch):
                break
            self.pos += 1
        end = self.pos

        # skip chinese word whitespaces and punctuations
        while self.pos < self.text_length:
            ch = self.get_next_char()
            if self.is_ascii_char(ch) or self.is_chinese_char(ch):
                break
            self.pos += 1

        return self.text[start:end]

    def get_chinese_words(self):
        chunks = self.create_simple_chunks() if self.simple else self.create_chunks()
        if self.simple and len(chunks) > 1:
            chunks = self.simple_compare.take_high_test(chunks)
        elif self.simple is False:
            if len(chunks) > 1:
                chunks = self.complex_compare.mmFilter(chunks)
            if len(chunks) > 1:
                chunks = self.complex_compare.lawlFilter(chunks)
            if len(chunks) > 1:
                chunks = self.complex_compare.svmlFilter(chunks)
            if len(chunks) > 1:
                chunks = self.complex_compare.logFreqFilter(chunks)

        if len(chunks) == 0:
            return ""

        word = [chunks[0].words[0]]
        token = ""
        length = 0
        for x in word:
            if x.length != -1:
                token += x.text
                length += len(x.text)
        self.pos += length
        return token

    def create_chunks(self):
        chunks = []
        original_pos = self.pos
        words1 = self.get_match_chinese_words()

        for word1 in words1:
            self.pos += len(word1.text)
            if self.pos < self.text_length:
                words2 = self.get_match_chinese_words()
                for word2 in words2:
                    self.pos += len(word2.text)
                    if self.pos < self.text_length:
                        words3 = self.get_match_chinese_words()
                        for word3 in words3:
                            if word3.length == -1:
                                chunk = Chunk(word1, word2)
                            else:
                                chunk = Chunk(word1, word2, word3)
                            chunks.append(chunk)
                    elif self.pos == self.text_length:
                        chunks.append(Chunk(word1, word2))
                    self.pos -= len(word2.text)
            elif self.pos == self.text_length:
                chunks.append(Chunk(word1))
            self.pos -= len(word1.text)

        self.pos = original_pos
        return chunks

    def create_simple_chunks(self):
        chunks = []
        original_pos = self.pos
        words = self.get_match_chinese_words()

        for word in words:
            self.pos += len(word.text)
            chunks.append(Chunk(word))
            self.pos -= len(word.text)

        self.pos = original_pos
        return chunks

    def get_match_chinese_words(self):
        # use cache, check it
        for i in range(self.cache_size):
            if self.cache[i][0] == self.pos:
                return self.cache[i][1]

        original_pos = self.pos
        words = []
        index = 0
        while self.pos < self.text_length:
            if index >= max_word_length:
                break
            elif not self.is_chinese_char(self.get_next_char()):
                break
            self.pos += 1
            index += 1

            text = self.text[original_pos: self.pos]
            word = get_dict_word(text)
            if word:
                words.append(word)

        self.pos = original_pos
        # if word not exists , place X and length -1
        if not words:
            word = Word()
            word.length = -1
            word.text = "X"
            words.append(word)

        self.cache[self.cache_index] = (self.pos, words)
        self.cache_index += 1
        if self.cache_index >= self.cache_size:
            self.cache_index = 0
        return words
