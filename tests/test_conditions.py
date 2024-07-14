#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `zeyrek.conditions` module."""
import pytest
from zeyrek.attributes import RootAttribute, PhoneticAttribute, \
    calculate_phonetic_attributes
from zeyrek.conditions import CombinedCondition, has, HasRootAttribute, DictionaryItemIs, not_have, \
    HasPhoneticAttribute, DictionaryItemIsAny, NoSurfaceAfterDerivation, HasAnySuffixSurface, HasTail, \
    PreviousMorphemeIs, PreviousStateIs, LastDerivationIs, HasDerivation, PreviousStateIsNot, HasTailSequence, \
    ContainsMorphemeSequence, LastDerivationIsAny, PreviousGroupContains, CurrentGroupContainsAny, \
    PreviousGroupContainsMorpheme, ContainsMorpheme, PreviousMorphemeIsAny, PreviousStateIsAny
from zeyrek.lexicon import RootLexicon
from zeyrek.morphology import MorphAnalyzer
from zeyrek.morphotactics import SearchPath, StemTransition, noun_S, SurfaceTransition, SuffixTransition, \
    adjectiveRoot_ST, verbRoot_S, become_S, vPast_S, past, verb, vCausTir_S, \
    nom_ST, vAgt_S, a3sg_S, pnon_S, morphemes, agt, a3sg, noun, pnon, nom, vPass_S, vAble_S

import nltk
nltk.download('punkt')

lex = RootLexicon.from_lines(["adak", "elma", "beyaz [P:Adj]", "meyve"])


@pytest.fixture(scope='session')
def lex_from_lines():
    return RootLexicon.from_lines(["adak", "elma", "beyaz [P:Adj]", "meyve"])


@pytest.fixture(scope='session')
def mt_lexicon():
    """Connects morphotactics graph and returns full lexicon"""
    lemmer = MorphAnalyzer()
    return lemmer.lexicon


@pytest.fixture(scope='session')
def searchpath_dict_item_with_tail_and_RA_voicing(mt_lexicon):
    adak = mt_lexicon.get_item_by_id('adak_Noun')  # , elma, beyaz, meyve
    stem_transition = StemTransition(adak, noun_S, calculate_phonetic_attributes(adak.pronunciation), surface='adağ')
    print(f"Stem transition: {stem_transition}")
    path = SearchPath.initial(stem_transition, 'a')
    print(f"Path {path}")
    return path


@pytest.fixture()
def simple_condition():
    return has(PhoneticAttribute.CannotTerminate)


@pytest.mark.parametrize("text_input, expected", [
    # (simple_condition, 1),
    (has(PhoneticAttribute.CannotTerminate), 1),
    (CombinedCondition('AND', [simple_condition, simple_condition]), 2),
    (CombinedCondition('OR', [simple_condition, simple_condition]), 2),
    (CombinedCondition('AND', [CombinedCondition('AND', [simple_condition, simple_condition]), simple_condition]), 3)
])
def test_condition_len(text_input, expected):
    condition = text_input
    assert len(condition) == expected


@pytest.mark.parametrize("test_input, expected_op_len", [
    ([has(PhoneticAttribute.CannotTerminate), has(RootAttribute.CompoundP3sgRoot)], ['AND', 2]),

    ([has(PhoneticAttribute.CannotTerminate),
      CombinedCondition('AND', [has(RootAttribute.CompoundP3sgRoot), has(PhoneticAttribute.CannotTerminate)])],
     ['AND', 3]),

    ([CombinedCondition('AND', [has(RootAttribute.CompoundP3sgRoot), has(PhoneticAttribute.CannotTerminate)]),
      has(PhoneticAttribute.CannotTerminate)], ['AND', 3]),

    ([has(PhoneticAttribute.CannotTerminate),
      CombinedCondition('OR', [has(RootAttribute.CompoundP3sgRoot), has(PhoneticAttribute.CannotTerminate)])],
     ['AND', 3]),

    ([CombinedCondition('OR', [has(RootAttribute.CompoundP3sgRoot), has(PhoneticAttribute.CannotTerminate)]),
      has(PhoneticAttribute.CannotTerminate)], ['AND', 3])

])
def test_and_condition(test_input, expected_op_len):
    cond1, cond2 = test_input
    operator, length = expected_op_len
    and_cond = cond1.and_(cond2)
    assert len(and_cond) == length
    assert and_cond.operator == operator


@pytest.mark.parametrize("test_input, expected_op_len", [
    ([has(PhoneticAttribute.CannotTerminate), has(RootAttribute.CompoundP3sgRoot)], ['OR', 2]),

    ([has(PhoneticAttribute.CannotTerminate),
      CombinedCondition('AND', [has(RootAttribute.CompoundP3sgRoot), has(PhoneticAttribute.CannotTerminate)])],
     ['OR', 3]),

    ([CombinedCondition('AND', [has(RootAttribute.CompoundP3sgRoot), has(PhoneticAttribute.CannotTerminate)]),
      has(PhoneticAttribute.CannotTerminate)], ['OR', 3]),

    ([has(PhoneticAttribute.CannotTerminate),
      CombinedCondition('OR', [has(RootAttribute.CompoundP3sgRoot), has(PhoneticAttribute.CannotTerminate)])],
     ['OR', 3]),

    ([CombinedCondition('OR', [has(RootAttribute.CompoundP3sgRoot), has(PhoneticAttribute.CannotTerminate)]),
      has(PhoneticAttribute.CannotTerminate)], ['OR', 3])

])
def test_or_condition(test_input, expected_op_len):
    cond1, cond2 = test_input
    operator, length = expected_op_len
    and_cond = cond1.or_(cond2)
    assert len(and_cond) == length
    assert and_cond.operator == operator


def test_dict_item_conditions(searchpath_dict_item_with_tail_and_RA_voicing):
    """Tests HasRootAttribute, has for RootAttribute"""
    # Adak has Voicing attribute, others have none
    path = searchpath_dict_item_with_tail_and_RA_voicing
    assert has(RootAttribute.Voicing).accept(path)
    assert not has(RootAttribute.Aorist_A).accept(path)
    assert HasRootAttribute(RootAttribute.Voicing).accept(path)
    assert not HasRootAttribute(RootAttribute.Aorist_A).accept(path)
    assert not_have(RootAttribute.ProgressiveVowelDrop).accept(path)
    assert not not_have(RootAttribute.Voicing).accept(path)


def test_has_phonetic_attributes(searchpath_dict_item_with_tail_and_RA_voicing):
    """Tests HasPHoneticAttribute, has for PhoneticAttribute"""
    path = searchpath_dict_item_with_tail_and_RA_voicing
    assert has(PhoneticAttribute.LastVowelBack).accept(path)
    assert not has(PhoneticAttribute.LastVowelFrontal).accept(path)
    assert HasPhoneticAttribute(PhoneticAttribute.LastVowelBack).accept(path)
    assert not HasPhoneticAttribute(PhoneticAttribute.LastVowelFrontal).accept(path)
    assert not_have(PhoneticAttribute.LastVowelFrontal).accept(path)
    assert not not_have(PhoneticAttribute.LastVowelBack).accept(path)


def test_DictionaryItemIs(searchpath_dict_item_with_tail_and_RA_voicing,
                          lex_from_lines):
    """Tests DictionaryItemIs"""
    path = searchpath_dict_item_with_tail_and_RA_voicing
    adak = lex_from_lines.get_item_by_id('adak_Noun')
    assert DictionaryItemIs(adak).accept(path)

    elma = lex_from_lines.get_item_by_id('elma_Noun')
    assert not DictionaryItemIs(elma).accept(path)


def test_DictionaryItemIsAny(mt_lexicon,
                             searchpath_dict_item_with_tail_and_RA_voicing):
    path = searchpath_dict_item_with_tail_and_RA_voicing
    adak = mt_lexicon.get_item_by_id('adak_Noun')
    elma = mt_lexicon.get_item_by_id('elma_Noun')
    assert not DictionaryItemIsAny(elma).accept(path)
    assert DictionaryItemIsAny(elma, adak).accept(path)
    assert DictionaryItemIsAny(adak).accept(path)
    assert DictionaryItemIsAny([elma, adak])


@pytest.fixture(scope='session')
def beyazlastirici_paths(mt_lexicon):
    beyaz = mt_lexicon.get_item_by_id('beyaz_Adj')
    assert beyaz is not None

    states = [(become_S, 'laş'), (verbRoot_S, ''), (vCausTir_S, 'tır'), (verbRoot_S, ''),
              (vAgt_S, 'ıcı'), (noun_S, ''), (a3sg_S, ''), (pnon_S, ''), (nom_ST, '')]
    stem_transition = StemTransition(beyaz, adjectiveRoot_ST)
    surface_transitions = [SurfaceTransition(stem_transition.surface, stem_transition)]
    path = SearchPath.initial(stem_transition, 'laştırıcı')
    paths = [path]
    previous_state = adjectiveRoot_ST
    attrs = path.phonetic_attributes
    for state in states:
        st, surface = state
        transition = SurfaceTransition(surface, SuffixTransition(previous_state, st))
        surface_transitions.append(transition)
        new_attrs = calculate_phonetic_attributes(surface, frozenset(attrs))
        new_path = paths[-1].copy(transition, new_attrs)
        paths.append(new_path)
        previous_state = st
        attrs = new_attrs

    # < (beyaz_Adj)(-)(beyaz: adjectiveRoot_ST + laş:become_S + verbRoot_S + tır: vCausTır_S + verbRoot_S
    # + ıcı:vAgt_S + noun_S + a3sg_S + pnon_S + nom_ST) >
    for path in paths:
        print(path)
    return paths


def test_has_derivation(beyazlastirici_paths):
    """Tests  HasDerivation"""
    paths = beyazlastirici_paths
    assert not HasDerivation().accept(paths[0])
    # WHEN las: become_S is added
    assert HasDerivation().accept(paths[1])
    assert HasDerivation().accept(paths[-1])


def test_NoSurfaceAfterDerivation(beyazlastirici_paths):
    """Tests NoSurfaceAfterDerivation"""
    paths = beyazlastirici_paths
    # <(beyaz_Adj)(-tırıcı)(beyaz:adjectiveRoot_ST + laş:become_S)>, tail: tırıcı
    assert NoSurfaceAfterDerivation().accept(paths[0])
    # < (beyaz_Adj)(-tırıcı)(beyaz: adjectiveRoot_ST + laş:become_S + verbRoot_S) >, tail: tırıcı
    assert NoSurfaceAfterDerivation().accept(paths[1])
    # <(beyaz_Adj)(-ıcı)(beyaz:adjectiveRoot_ST + laş:become_S + verbRoot_S + tır:vCausTır_S)>, tail: ıcı
    assert NoSurfaceAfterDerivation().accept(paths[2])
    # WHEN verbRoot with no surface added
    # <(beyaz_Adj)(-ıcı)(beyaz:adjectiveRoot_ST + laş:become_S + verbRoot_S + tır:vCausTır_S + verbRoot_S)>, tail: ıcı
    assert NoSurfaceAfterDerivation().accept(paths[3])


def test_HasTail(beyazlastirici_paths):
    """Tests  HasTail"""
    paths = beyazlastirici_paths
    assert HasTail().accept(paths[0])
    assert HasTail().accept(paths[1])
    assert HasTail().accept(paths[2])
    assert not HasTail().accept(paths[-1])


def test_HasDerivation(beyazlastirici_paths):
    """Tests HasDerivation"""
    paths = beyazlastirici_paths
    assert not HasDerivation().accept(paths[0])
    assert HasDerivation().accept(paths[1])
    assert HasDerivation().accept(paths[2])
    assert HasDerivation().accept(paths[3])


def test_HasAnySuffixSurface(beyazlastirici_paths):
    """Tests HasAnySuffixSurface"""
    # TODO: add a different path with more transitions without surface
    paths = beyazlastirici_paths

    assert not HasAnySuffixSurface().accept(paths[0])
    # WHEN 'las' is added
    assert HasAnySuffixSurface().accept(paths[1])
    assert HasAnySuffixSurface().accept(paths[2])


def test_PreviousMorphemeIs(beyazlastirici_paths):
    """Tests PreviousMorphemeIs"""
    paths = beyazlastirici_paths
    assert PreviousMorphemeIs(verb).accept(paths[3])
    assert not PreviousMorphemeIs(past).accept(paths[3])


def test_PreviousStateIs(beyazlastirici_paths):
    """Tests PreviousStateIs"""
    paths = beyazlastirici_paths
    assert PreviousStateIs(verbRoot_S).accept(paths[3])
    assert not PreviousStateIsNot(verbRoot_S).accept(paths[3])
    assert PreviousStateIsNot(become_S).accept(paths[3])
    assert not PreviousStateIs(vPast_S).accept(paths[3])


def test_LastDerivationIs(beyazlastirici_paths):
    """Tests PreviousStateIs"""
    paths = beyazlastirici_paths
    assert LastDerivationIs(become_S).accept(paths[1])
    assert LastDerivationIs(become_S).accept(paths[2])
    assert not LastDerivationIs(vPast_S).accept(paths[2])
    # WHEN beyaz:adjectiveRoot_ST + laş:become_S + verbRoot_S +
    # tır:vCausTır_S + verbRoot_S
    assert LastDerivationIs(vCausTir_S).accept(paths[4])
    assert not LastDerivationIs(vAgt_S).accept(paths[4])
    # WHEN beyaz:adjectiveRoot_ST + laş:become_S + verbRoot_S +
    # tır:vCausTır_S + verbRoot_S + ıcı:vAgt_S
    assert LastDerivationIs(vAgt_S).accept(paths[5])
    assert not LastDerivationIs(vCausTir_S).accept(paths[5])


def test_HasTailSequence(beyazlastirici_paths):
    path = beyazlastirici_paths[-1]
    assert HasTailSequence(agt, noun, a3sg, pnon, nom).accept(path)
    assert not HasTailSequence(agt, noun, a3sg, pnon).accept(path)
    assert HasTailSequence(pnon, nom).accept(path)


def test_ContainsMorphemeSequence(beyazlastirici_paths):
    path = beyazlastirici_paths[3]

    assert ContainsMorphemeSequence(morphemes['Adj'],
                                    morphemes['Become'],
                                    morphemes['Verb']
                                    ).accept(path)
    assert ContainsMorphemeSequence(morphemes['Adj'],
                                    morphemes['Become']
                                    ).accept(path)
    assert ContainsMorphemeSequence(morphemes['Become'],
                                    morphemes['Verb'],
                                    morphemes['Caus']
                                    ).accept(path)

    assert ContainsMorphemeSequence(morphemes['Become']).accept(path)
    assert not ContainsMorphemeSequence(morphemes['Become'], morphemes['Caus']).accept(path)


def test_LastDerivationIsAny(beyazlastirici_paths):
    path = beyazlastirici_paths[3]
    assert LastDerivationIsAny(vCausTir_S, vPass_S, vAble_S).accept(path)
    assert not LastDerivationIsAny(become_S).accept(path)


def test_CurrentGroupContainsAny(beyazlastirici_paths):
    path = beyazlastirici_paths[5]
    # WHERE the last inflection group is ici:vAgt_S
    print(path)
    assert not CurrentGroupContainsAny(vCausTir_S).accept(path)
    assert CurrentGroupContainsAny(vAgt_S).accept(path)
    path = beyazlastirici_paths[-1]
    # WHERE the last inflection group is ici:vAgt_S+noun_S+a3sg_S+pnon_S+nom_ST
    print(path)
    assert not CurrentGroupContainsAny(vCausTir_S).accept(path)
    assert CurrentGroupContainsAny(vAgt_S).accept(path)


def test_PreviousGroupContainsAny(beyazlastirici_paths):
    path = beyazlastirici_paths[4]
    # WHERE the previous infl group is: become_S + verbRoot_S
    # the current inflection group is ici:vCausTir_S+verbRoot_S
    assert not PreviousGroupContains(vCausTir_S).accept(path)
    assert PreviousGroupContains(become_S).accept(path)
    assert PreviousGroupContains(verbRoot_S).accept(path)
    path = beyazlastirici_paths[-1]
    # WHERE the previous inflection group is: vCausTir_S+verbRoot_S
    # the current inflection group is ici:vAgt_S+noun_S+a3sg_S+pnon_S+nom_ST
    assert PreviousGroupContains(vCausTir_S).accept(path)
    assert not PreviousGroupContains(vAgt_S).accept(path)
    assert not PreviousGroupContains(become_S).accept(path)


def test_PreviousGroupContainsMorpheme(beyazlastirici_paths):
    path = beyazlastirici_paths[4]
    # WHERE the previous infl group is: become_S + verbRoot_S
    # the current inflection group is ici:vCausTir_S+verbRoot_S
    assert not PreviousGroupContainsMorpheme(morphemes['Caus']).accept(path)
    assert PreviousGroupContainsMorpheme(morphemes['Become']).accept(path)
    assert PreviousGroupContainsMorpheme(morphemes['Verb']).accept(path)


def test_ContainsMorpheme(beyazlastirici_paths):
    path = beyazlastirici_paths[4]
    assert ContainsMorpheme(morphemes['Verb']).accept(path)
    assert ContainsMorpheme(morphemes['Agt']).not_().accept(path)
    assert not ContainsMorpheme(morphemes['JustLike']).accept(path)


def test_PreviousMorphemeIsAny(beyazlastirici_paths):
    path = beyazlastirici_paths[4]
    # WHERE path end is: become_S + verbRoot_S+ici:vCausTir_S+verbRoot_S
    assert not PreviousMorphemeIsAny(morphemes['Verb'],
                                     morphemes['Noun']).accept(path)
    assert PreviousMorphemeIsAny(morphemes['Caus']).accept(path)


def test_PreviousStateIsAny(beyazlastirici_paths):
    path = beyazlastirici_paths[4]
    # WHERE path end is: become_S + verbRoot_S+ici:vCausTir_S+verbRoot_S
    assert not PreviousStateIsAny(morphemes['Verb'],
                                  morphemes['Noun']).accept(path)
    assert PreviousMorphemeIsAny(morphemes['Caus']).accept(path)

# TODO: SecondaryPosIs
# TODO: RootSurfaceIs
# TODO: RootSurfaceIsAny
