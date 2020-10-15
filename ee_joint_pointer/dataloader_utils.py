#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dataloader.py utils"""
import re
import json
import random

from utils import ENTI_DICT


def split_text(text, max_len, split_pat=r'([，。]”?)', greedy=False):
    """文本分片
    将超过长度的文本分片成多段满足最大长度要求的最长连续子文本
    约束条件：1）每个子文本最大长度不超过max_len；
             2）所有的子文本的合集要能覆盖原始文本。
    Arguments:
        text {str} -- 原始文本
        max_len {int} -- 最大长度

    Keyword Arguments:
        split_pat {str or re pattern} -- 分割符模式 (default: {SPLIT_PAT})
        greedy {bool} -- 是否选择贪婪模式 (default: {False})
                         贪婪模式：在满足约束条件下，选择子文本最多的分割方式
                         非贪婪模式：在满足约束条件下，选择冗余度最小且交叉最为均匀的分割方式

    Returns:
        tuple -- 返回子文本列表以及每个子文本在原始文本中对应的起始位置列表

    Examples:
        text = '今夕何夕兮，搴舟中流。今日何日兮，得与王子同舟。蒙羞被好兮，不訾诟耻。心几烦而不绝兮，得知王子。山有木兮木有枝，心悦君兮君不知。'
        sub_texts, starts = split_text(text, maxlen=30, greedy=False)
        for sub_text in sub_texts:
            print(sub_text)
        print(starts)
        for start, sub_text in zip(starts, sub_texts):
            if text[start: start + len(sub_text)] != sub_text:
            print('Start indice is wrong!')
            break
    """
    # 文本小于max_len则不分割
    if len(text) <= max_len:
        return [text], [0]
    # 分割字符串
    segs = re.split(split_pat, text)
    # init
    sentences = []
    # 将分割后的段落和分隔符组合
    for i in range(0, len(segs) - 1, 2):
        sentences.append(segs[i] + segs[i + 1])
    if segs[-1]:
        sentences.append(segs[-1])
    n_sentences = len(sentences)
    sent_lens = [len(s) for s in sentences]

    # 所有满足约束条件的最长子片段
    alls = []
    for i in range(n_sentences):
        length = 0
        sub = []
        for j in range(i, n_sentences):
            if length + sent_lens[j] <= max_len or not sub:
                sub.append(j)
                length += sent_lens[j]
            else:
                break
        alls.append(sub)
        # 将最后一个段落加入
        if j == n_sentences - 1:
            if sub[-1] != j:
                alls.append(sub[1:] + [j])
            break

    if len(alls) == 1:
        return [text], [0]

    if greedy:
        # 贪婪模式返回所有子文本
        sub_texts = [''.join([sentences[i] for i in sub]) for sub in alls]
        starts = [0] + [sum(sent_lens[:i]) for i in range(1, len(alls))]
        return sub_texts, starts
    else:
        # 用动态规划求解满足要求的最优子片段集
        DG = {}  # 有向图
        N = len(alls)
        for k in range(N):
            tmplist = list(range(k + 1, min(alls[k][-1] + 1, N)))
            if not tmplist:
                tmplist.append(k + 1)
            DG[k] = tmplist

        routes = {}
        routes[N] = (0, -1)
        for i in range(N - 1, -1, -1):
            templist = []
            for j in DG[i]:
                cross = set(alls[i]) & (set(alls[j]) if j < len(alls) else set())
                w_ij = sum([sent_lens[k] for k in cross]) ** 2  # 第i个节点与第j个节点交叉度
                w_j = routes[j][0]  # 第j个子问题的值
                w_i_ = w_ij + w_j
                templist.append((w_i_, j))
            routes[i] = min(templist)

        sub_texts, starts = [''.join([sentences[i] for i in alls[0]])], [0]
        k = 0
        while True:
            k = routes[k][1]
            sub_texts.append(''.join([sentences[i] for i in alls[k]]))
            starts.append(sum(sent_lens[: alls[k][0]]))
            if k == N - 1:
                break

    return sub_texts, starts


def whitespace_tokenize(text):
    """
    Desc:
        runs basic whitespace cleaning and splitting on a piece of text.
    """
    text = text.strip()
    # 内容为空则返回空列表
    if not text:
        return []
    tokens = list(text)
    return tokens


class InputExample(object):
    """a single set of samples of data_src
    """

    def __init__(self,
                 idx,
                 text,
                 enti_type=None,
                 start_position=None,
                 end_position=None,
                 tag=None
                 ):
        self.idx = idx
        self.text = text
        self.enti_type = enti_type
        self.start_position = start_position
        self.end_position = end_position
        self.tag = tag


class InputFeatures(object):
    """
    Desc:
        a single set of features of data_src
    """

    def __init__(self,
                 input_ids,
                 input_mask,
                 split_to_original_id,
                 example_id,
                 cls_label=None,
                 tag=None,
                 random_cls_id=None,
                 random_start_posi=None,
                 random_end_posi=None,
                 ):
        self.input_mask = input_mask
        self.input_ids = input_ids

        # cascade
        self.cls_label = cls_label
        self.tag = tag
        self.random_cls_id = random_cls_id
        self.random_start_posi = random_start_posi
        self.random_end_posi = random_end_posi

        # use to split
        self.split_to_original_id = split_to_original_id
        self.example_id = example_id


def read_examples(input_file):
    """read data_src to InputExamples
    :return examples (List[InputExample])
    """
    # read json file
    with open(input_file, "r", encoding='utf-8') as f:
        input_data = json.load(f)
    # get InputExample class
    examples = []
    for entry in input_data:
        idx = entry["id"]
        text = entry["context"]
        enti_type = entry["type"]
        start_position = [[pos[0] for pos in type_pos] for type_pos in entry["entity"]]
        end_position = [[pos[1] for pos in type_pos] for type_pos in entry["entity"]]

        # init
        tag = list(text)
        # 替换多个实体
        for idx, s_tp in enumerate(enti_type):
            # 获取B-tag
            en_tag = ENTI_DICT[s_tp]
            # 取主体
            for entity in entry['entity'][idx]:
                # 替换实体
                tag[entity[0]] = en_tag[0]
                tag[entity[0] + 1:entity[1] + 1] = [en_tag[1] for _ in range(entity[1] - entity[0])]
            # 打O标
            for idx, item in enumerate(tag):
                if len(item) == 1:
                    tag[idx] = ENTI_DICT['Others']
        # sanity check
        assert len(text) == len(tag), '标签与原文本长度不一致！'

        example = InputExample(idx=idx,
                               text=text,
                               enti_type=enti_type,
                               start_position=start_position,
                               end_position=end_position,
                               tag=tag)
        examples.append(example)

    print("InputExamples:", len(examples))
    return examples


def convert_examples_to_features(params, examples, tokenizer, pad_sign=True, greed_split=True):
    """convert InputExamples to features.
    :param examples (List[InputExamples])
    :param pad_sign: 是否补零
    :return: features (List[InputFeatures])
    """
    # tag to id
    tag2idx = {tag: idx for idx, tag in enumerate(params.label_list)}
    features = []

    max_len = params.max_seq_length
    # 分割符
    split_pad = r'([,.!?，。！？、：]”?)'
    for (example_idx, example) in enumerate(examples):
        # 原始文本index
        original_id = list(range(len(example.text)))
        # split long text
        sub_contexts, starts = split_text(text=example.text, max_len=max_len,
                                          greedy=greed_split, split_pat=split_pad)

        for context, start in zip(sub_contexts, starts):
            # 保存子文本对应原文本的位置
            split_to_original_id = original_id[start:start + len(context)]
            tag = example.tag[start:start + len(context)]
            # List[str]
            context_doc = whitespace_tokenize(context)
            # sanity check
            assert len(context_doc) == len(context) == len(split_to_original_id), 'check the whitespace tokenize!'

            # init
            start_label = [0] * max_len
            end_label = [0] * max_len
            cls_label = [0] * len(tag2idx)

            random_start_posi = [0] * max_len
            random_end_posi = [0] * max_len
            cls_id = -10000
            pairs_dict = {}

            # 获取文本tokens
            # 标签不为空的样本
            if len(example.start_position) != 0 and len(example.end_position) != 0:
                has_label = False
                # get gold label
                for enti_type, start_item, end_item in zip(example.enti_type, example.start_position,
                                                           example.end_position):
                    type_pairs = []
                    for s, e in zip(start_item, end_item):
                        # 属于该子文本的标签
                        if 0 <= (s - start) < max_len and 0 <= (e - start) < max_len:
                            # 实体标签
                            start_label[s - start] = 1
                            end_label[e - start] = 1
                            # 类别标签
                            cls_label[tag2idx[enti_type]] = 1
                            type_pairs.append((s - start, e - start))
                            has_label = True
                    # 将该类别的标签加入字典
                    if has_label:
                        pairs_dict[enti_type] = type_pairs
                # 如果分割后的文本没有标签，则舍弃
                if not has_label:
                    continue

            # get context_tokens
            context_doc_tokens = []
            for token in context_doc:
                # tokenize
                tmp_subword_lst = tokenizer.tokenize(token)
                if len(tmp_subword_lst) == 1:
                    context_doc_tokens.extend(tmp_subword_lst)  # context len
                else:
                    raise ValueError("Please check the result of tokenizer!!!")

            # cut off
            if len(context_doc_tokens) > max_len:
                context_doc_tokens = context_doc_tokens[:max_len]
                split_to_original_id = split_to_original_id[: max_len]
                tag = tag[: max_len]

            # input_mask:
            #   the mask has 1 for real tokens and 0 for padding tokens.
            #   only real tokens are attended to.
            # context
            input_mask = [1] * len(context_doc_tokens)
            # token to id
            input_ids = tokenizer.convert_tokens_to_ids(context_doc_tokens)

            # zero-padding up to the sequence length
            if len(input_ids) < max_len and pad_sign:
                # 补零
                padding = [0] * (max_len - len(input_ids))
                padding_s2o = [-1] * (max_len - len(input_ids))
                padding_tag = ['O'] * (max_len - len(input_ids))
                input_ids += padding
                input_mask += padding
                split_to_original_id += padding_s2o
                tag += padding_tag

            # TODO: random choose(for train stage)
            if len(pairs_dict.keys()) != 0:
                # 选一个类别的实体
                select_pairs_key = random.sample(pairs_dict.keys(), 1)[0]
                select_pairs = pairs_dict.get(select_pairs_key)
                # 获得实体index
                cls_id = tag2idx.get(select_pairs_key)
                # 打标
                for pair in select_pairs:
                    random_start_posi[pair[0]] = 1
                    random_end_posi[pair[1]] = 1

            features.append(
                InputFeatures(
                    input_ids=input_ids,
                    input_mask=input_mask,
                    cls_label=cls_label,
                    tag=tag,
                    random_cls_id=cls_id,
                    random_start_posi=random_start_posi,
                    random_end_posi=random_end_posi,
                    split_to_original_id=split_to_original_id,
                    example_id=example_idx
                ))
    return features
