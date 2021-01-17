#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `zeyrek` package."""

import pytest

from zeyrek.attributes import SecondaryPos, PrimaryPos, calculate_phonetic_attributes, RootAttribute, PhoneticAttribute
from zeyrek.lexicon import DictionaryItem, RootLexicon
from zeyrek.morphology import MorphAnalyzer
from zeyrek.morphotactics import StemTransition, SearchPath, root_S, noun_S, MorphemeState, p2sg_S, loc_ST, a3pl_S, \
    SuffixTransition, morphemes, equ_ST, TurkishMorphotactics, adjectiveRoot_ST


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


def test_stem_transition():
    from zeyrek.attributes import calculate_phonetic_attributes
    word_line = 'beyaz [P:Adj]'
    lexicon = RootLexicon.from_lines([word_line])
    morphotactics = TurkishMorphotactics(lexicon=lexicon)
    dict_item = lexicon.get_matching_items('beyaz')[0]
    transition = morphotactics.stem_transitions.prefix_matches('beyaz')[0]
    assert transition.to_ == adjectiveRoot_ST
    assert str(transition) == "<(Dict: beyaz [P:Adj]):beyaz → [adjectiveRoot_ST:Adj]>"
    assert transition.condition is None
    assert transition.condition_count == 0
    assert transition.dict_item.lemma == 'beyaz'
    assert transition.from_ is root_S

    calculated_attrs = calculate_phonetic_attributes('beyaz')
    assert transition.attrs == calculated_attrs
    assert type(transition.to_) == MorphemeState


@pytest.fixture
def lex_from_lines():
    return RootLexicon.from_lines(["adak", "elma", "beyaz [P:Adj]", "meyve"])


def test_analysis(lex_from_lines):
    lemmer = MorphAnalyzer(lexicon=lex_from_lines)
    analysis = lemmer.analyze('elma')
    assert analysis is not None
    analysis = lemmer.analyze('beyazlaştırıcı')
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
