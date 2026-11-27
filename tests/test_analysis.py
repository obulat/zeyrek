"""Tests for `zeyrek` package."""

import os
import subprocess
import sys

import nltk
import pytest

from zeyrek.attributes import (
    PrimaryPos,
    SecondaryPos,
    calculate_phonetic_attributes,
)
from zeyrek.lexicon import DictionaryItem, RootLexicon
from zeyrek.morphology import MorphAnalyzer
from zeyrek.morphotactics import (
    MorphemeState,
    SearchPath,
    StemTransition,
    TurkishMorphotactics,
    adjectiveRoot_ST,
    root_S,
)

nltk.download("punkt_tab")


@pytest.fixture
def dict_item():
    word = "ev"
    lemma = word
    root = word
    primary_pos = PrimaryPos.Noun
    secondary_pos = SecondaryPos.NONE
    attrs = calculate_phonetic_attributes(word)
    pronunciation = word
    index = 0
    return DictionaryItem(
        lemma, root, primary_pos, secondary_pos, attrs, pronunciation, index
    )


def test_DictionaryItem_creation(dict_item):
    assert dict_item.lemma == "ev"


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
    dict_item = DictionaryItem(
        "beyaz", "beyaz", PrimaryPos.Adjective, SecondaryPos.NONE, [], "beyaz", 0
    )
    transition = StemTransition(dict_item, root_S, attrs, word)
    assert transition.dict_item.lemma == "beyaz"
    p = SearchPath.initial(transition, "laşacak")
    assert p.stem_transition == transition


def test_stem_transition():
    from zeyrek.attributes import calculate_phonetic_attributes

    word_line = "beyaz [P:Adj]"
    lexicon = RootLexicon.from_lines([word_line])
    morphotactics = TurkishMorphotactics(lexicon=lexicon)
    lexicon.get_matching_items("beyaz")[0]
    transition = morphotactics.stem_transitions.prefix_matches("beyaz")[0]
    assert transition.to_ == adjectiveRoot_ST
    assert str(transition) == "<(Dict: beyaz [P:Adj]):beyaz → [adjectiveRoot_ST:Adj]>"
    assert transition.condition is None
    assert transition.condition_count == 0
    assert transition.dict_item.lemma == "beyaz"
    assert transition.from_ is root_S

    calculated_attrs = calculate_phonetic_attributes("beyaz")
    assert transition.attrs == calculated_attrs
    assert type(transition.to_) == MorphemeState


@pytest.fixture
def lex_from_lines():
    return RootLexicon.from_lines(["adak", "elma", "beyaz [P:Adj]", "meyve"])


def test_analysis(lex_from_lines):
    lemmer = MorphAnalyzer(lexicon=lex_from_lines, return_all_lemmas=True)
    analysis = lemmer.analyze("elma")
    assert analysis is not None
    analysis = lemmer.analyze("beyazlaştırıcı")
    assert analysis is not None
    assert "beyaz" in lemmer.lemmatize("beyazlaştı")[0][1]
    assert "elma" in lemmer.lemmatize("elmalı")[0][1]
    assert "meyve" in lemmer.lemmatize("meyvesiz")[0][1]


def test_default_lexicon():
    lex = RootLexicon.default_text_dictionaries()
    assert lex.get_item_by_id("elma_Noun") is not None
    assert len(lex) > 0


def test_sentence():
    lemmer = MorphAnalyzer(return_all_lemmas=True)
    sentence = "Bunu okuyabiliyorum"
    result = lemmer.lemmatize(sentence)
    assert "Bunu" in result[0][0]
    assert "bu" in result[0][1]


def test_compound_words():
    lemmer = MorphAnalyzer()
    compound_word = "Zeytinyağlı"
    result = lemmer.lemmatize(compound_word)
    assert "zeytinyağı" in result


def test_single_lemma():
    analyzer = MorphAnalyzer()
    res = analyzer.lemmatize("Şu dünyadaki sevilen kişi sevmeyi bilendir.")
    assert res == ["şu", "dünya", "sevmek", "kişi", "sevmek", "bilmek", "."]


def test_phonetic_attributes_cache_cannot_be_changed():
    attrs = calculate_phonetic_attributes("en")
    assert isinstance(attrs, frozenset)
    calculate_phonetic_attributes.cache_clear()
    assert calculate_phonetic_attributes("en") == attrs


def test_repeated_analysis_gives_the_same_lemmas():
    # Analyzing a word used to change the cached phonetic attributes, so the
    # second call for "olacak" found no analysis and returned the word itself.
    analyzer = MorphAnalyzer()
    text = "olacak oluyor gelecek yapılacak"
    expected = ["olmak", "olmak", "gelecek", "yapmak"]
    assert analyzer.lemmatize(text) == expected
    assert analyzer.lemmatize(text) == expected


def test_analysis_does_not_depend_on_hash_seed():
    code = (
        "from zeyrek.morphology import MorphAnalyzer;"
        "a = MorphAnalyzer();"
        "print(sorted(str(x) for w in ('reddi', 'reddine', 'bilendir') for x in a._parse(w)))"
    )
    outputs = {
        subprocess.run(
            [sys.executable, "-c", code],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for seed in ("1", "2")
    }
    assert len(outputs) == 1


@pytest.mark.parametrize(
    ("base", "word", "lemma"),
    [
        ("okumak", "okunmak", "okumak"),
        ("yazmak", "yazılmak", "yazmak"),
        ("okumak", "okuyabilmek", "okumak"),
        ("gelmek", "gelememek", "gelmek"),
    ],
)
def test_analysing_a_verb_does_not_break_its_derived_forms(base, word, lemma):
    # https://github.com/obulat/zeyrek/issues/42
    analyzer = MorphAnalyzer()
    analyzer.analyze(base)
    assert analyzer.lemmatize(word) == [lemma]
