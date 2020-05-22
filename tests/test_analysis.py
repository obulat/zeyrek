#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `zeyrek` package."""

import pytest

from zeyrek.attributes import SecondaryPos, PrimaryPos, calculate_phonetic_attributes
from zeyrek.lexicon import DictionaryItem, RootLexicon
from zeyrek.morphology import MorphAnalyzer
from zeyrek.morphotactics import StemTransition, SearchPath, root_S


@pytest.fixture
def response():
    """Sample pytest fixture.

    See more at: http://doc.pytest.org/en/latest/fixture.html
    """
    # import requests
    # return requests.get('https://github.com/audreyr/cookiecutter-pypackage')


@pytest.fixture
def dict_item():
    word = 'ev'
    lemma = word
    root = word
    primary_pos = PrimaryPos.Noun
    secondary_pos = SecondaryPos.NONE
    attrs = calculate_phonetic_attributes(word)
    pronunciation = word
    index = 0
    return DictionaryItem(lemma, root, primary_pos, secondary_pos, attrs, pronunciation, index)


def test_DictionaryItem_creation(dict_item):
    assert dict_item.lemma == 'ev'


def test_rootlexicon(dict_item):
    lex = RootLexicon()
    lex.add(dict_item)
    assert dict_item in lex.item_set
    assert dict_item.id_ in lex.id_dict
    print(dict_item.id_)
    item = lex.get_item_by_id(dict_item.id_)
    assert item == dict_item
    assert len(lex) == 1


def test_initial_search_path():
    from zeyrek.attributes import calculate_phonetic_attributes
    word = "beyazlaşacak"
    attrs = calculate_phonetic_attributes(word)
    dict_item = DictionaryItem("beyaz", "beyaz", PrimaryPos.Adjective, SecondaryPos.NONE, [], "beyaz", 0)
    transition = StemTransition(dict_item, root_S, attrs, word)
    assert transition.dict_item.lemma == "beyaz"
    p = SearchPath.initial(transition, "laşacak")
    assert p.stem_transition == transition


"""
def test_stem_transition():
    from zeyrek.attributes import calculate_phonetic_attributes
    word = 'beyaz'
    attr = DictItemAttrs(RootAttribute(0), calculate_phonetic_attributes(word))
    dict_item = DictionaryItem(word, word, PrimaryPos.Adjective,
                               SecondaryPos.NONE, attr, word, 0)
    transition = StemTransition(word, dict_item,
                                attr, noun_S)
    assert transition.to_ == noun_S
    # assert str(transition) == "<(Dict: beyaz [P:Adj]):beyaz → [noun_S:Noun]>"
    print(transition, dir(transition))
    assert transition.condition is None
    assert transition.condition_count == 0
    assert transition.dict_item.lemma == 'beyaz'
    assert transition.from_ is None
    print(transition.phonetic_attrs)

    assert transition.phonetic_attrs & (PhoneticAttribute.FirstLetterConsonant | PhoneticAttribute.LastLetterConsonant)
    assert transition.surface == dict_item.lemma
    assert type(transition.to_) == MorphemeState
    assert transition.to_ == noun_S



def test_morphotactics():
    item = DictionaryItem("guzel", "guzel", PrimaryPos.Adjective, SecondaryPos.NONE, [], "guzel", 0)
    lex = RootLexicon()
    lex.add(item)
    m = TurkishMorphotactics(lex)
    print(m)
    assert m is not None

    from zeyrek.conditions import PreviousMorphemeIs
    trans = SuffixTransition(p2sg_S, equ_ST, 'cA', PreviousMorphemeIs(morphemes['A3pl']))
    print(trans, trans.condition, trans.condition_count)
    pre_trans = SuffixTransition(a3pl_S, p2sg_S)

    assert trans is not None
    path = SearchPath('ca', MorphemeState(loc_ST, loc_ST, True), [a3pl_S, p2sg_S], PhoneticAttribute.LastLetterVowel, True)
    assert trans.condition.accept(path)
"""


@pytest.fixture
def lex_from_lines():
    return RootLexicon.from_lines(["adak", "elma", "beyaz [P:Adj]", "meyve"])


def test_analysis(lex_from_lines):
    lemmer = MorphAnalyzer(lexicon=lex_from_lines)
    analysis = lemmer.analyze('elma')
    print(analysis)
    assert analysis is not None
    analysis = lemmer.analyze('beyazlaştırıcı')
    print(analysis)
    assert analysis is not None
    assert 'beyaz' in lemmer.lemmatize('beyazlaştı')[0][1]
    assert 'elma' in lemmer.lemmatize('elmalı')[0][1]
    assert 'meyve' in lemmer.lemmatize('meyvesiz')[0][1]


def test_default_lexicon():
    lex = RootLexicon.default_text_dictionaries()
    assert lex.get_item_by_id('elma_Noun') is not None
    assert len(lex) > 0


def test_sentence():
    lemmer = MorphAnalyzer()
    sentence = "Bunu okuyabiliyorum"
    result = lemmer.lemmatize(sentence)
    assert 'Bunu' in result[0][0]
    assert 'bu' in result[0][1]
