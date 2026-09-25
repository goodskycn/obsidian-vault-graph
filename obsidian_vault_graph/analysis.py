# -*- coding: utf-8 -*-
"""内容分析：关键词标签 + TF-IDF 相关性"""
import collections
import math

import jieba
import jieba.analyse

from . import util


def compute_keywords(notes, bodies, vocab_size=90, min_doc_freq=8):
    """返回 (keywords: {rel: [kw]}, vocab: 全局共享标签词表)"""
    keywords = {}
    df = collections.Counter()
    for rel, p, top, subdir, name in notes:
        text = util.clean_for_nlp(pretty3(name) + " " + bodies[rel])[:20000]
        kws = [k for k in jieba.analyse.extract_tags(text, topK=12) if util.ok_token(k)]
        keywords[rel] = kws
        for w in set(kws):
            df[w] += 1

    folder_words = set()
    for rel, p, top, subdir, name in notes:
        if top != "未分类":
            folder_words.add(top)
        for part in subdir.split("/"):
            if part:
                folder_words.add(part)
    vocab = [w for w, c in df.most_common() if c >= min_doc_freq and w not in folder_words][:vocab_size]
    return keywords, vocab


def pretty3(name):
    return util.pretty(name)


def compute_related(notes, bodies, keywords, min_sim=0.28, max_related=3):
    """TF-IDF 余弦相似度；排除同主题/同目录与同名副本。
    返回 {rel: [(other_rel, sim)]}"""
    N = len(notes)
    df = collections.Counter()
    for rel, p, top, subdir, name in notes:
        for w in set(keywords[rel]):
            df[w] += 1
    info = {n[0]: n for n in notes}

    tokens = {}
    for rel, p, top, subdir, name in notes:
        text = util.clean_for_nlp(info[rel][4] + " " + bodies[rel])[:20000]
        tokens[rel] = collections.Counter(w for w in jieba.cut(text) if util.ok_token(w))

    vectors = {}
    for rel, tf in tokens.items():
        vec = {w: (1 + math.log(c)) * math.log(1 + N / df[w]) for w, c in tf.items() if w in df}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors[rel] = {w: v / norm for w, v in vec.items()}

    inv = collections.defaultdict(list)
    for rel, vec in vectors.items():
        for w in vec:
            inv[w].append(rel)

    related = {}
    for rel, vec in vectors.items():
        top = info[rel][2]
        sub = info[rel][3]
        own = util.norm_title(info[rel][4])
        sims = collections.Counter()
        for w, v in vec.items():
            for other in inv[w]:
                if other != rel:
                    sims[other] += v * vectors[other][w]
        picked, titles = [], set()
        for other, s in sims.most_common(60):
            if s < min_sim:
                break
            if info[other][2] == top or info[other][3] == sub:
                continue
            t = util.norm_title(info[other][4])
            if t == own or t in titles:
                continue
            picked.append((other, s))
            titles.add(t)
            if len(picked) >= max_related:
                break
        related[rel] = picked
    return related
