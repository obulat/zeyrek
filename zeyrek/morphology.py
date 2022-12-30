# -*- coding: utf-8 -*-
import collections

from nltk.tokenize import word_tokenize, sent_tokenize
from zeyrek import tr
from zeyrek.attributes import SecondaryPos
from zeyrek.formatters import UDFormatter, DefaultFormatter
from zeyrek.lexicon import RootLexicon
from zeyrek.morphotactics import TurkishMorphotactics, Morpheme
from zeyrek.rulebasedanalyzer import RuleBasedAnalyzer, SingleAnalysis
from typing import NamedTuple

"""Main module."""


class Parse(NamedTuple):
    word: str
    lemma: str
    pos: str
    morphemes: list[Morpheme]
    formatted: str
    """
    Parse result wrapper. Based on https://github.com/kmike/pymorphy2/blob/master/pymorphy2/analyzer.py
    """

    def __contains__(self, item: str) -> bool:
        """
        Checks if a morpheme is contained in Parse morphemes
        :param item: id of a morpheme, e.g. 'Noun', 'Acc', 'FutPart'
        :return: True if morpheme is contained in Parse morphemes
        """
        return item in self.morphemes

    def __len__(self):
        """
        :return: number of morphemes in the Parse
        """
        return len(self.morphemes)


def _normalize(word: str) -> str:
    word = tr.normalize_circumflex(tr.lower(word))
    # TODO: Decide what to do with apostrophes
    word = word.replace("'", "")
    return word


def _tokenize_text(text: str) -> list[str]:
    return word_tokenize(text.replace("'", "").replace("’", ""), language="turkish")


class MorphAnalyzer:
    """
    Morphological analyzer for Turkish language.

    It analyzes each word to suggest all possible morphological analyses.

    Create a :class:`TrLemmer` object ::

        >>> import zeyrek
        >>> lemmer = zeyrek.MorphAnalyzer()

    Analyzer uses default text dictionaries from Zemberek-NLP. All dictionaries are
    in resources/tr folder (TODO: add unknown word analyzer).
    You can also add your own dictionary files in .txt format, with
    each word on its own line.

        >>> lemmer.add_dictionary('/path/to/file')

    TrLemmer can analyze or lemmatize words and sentences.

        >>> lemmer.lemmatize('beyazlaştırmak')
        ['beyaz']

    #TODO: Add analysis for words with apostrophes
    Methods should be:
    analyze: public method, takes in a string with one/more words, returns list of lists of Parses.
    lemmatize: public method, takes in a string with one/more words, returns list of lists of strings: lemmas

    Each method uses method _parse to get SingleAnalysis for the word
    """

    formatters = {"UD": UDFormatter}

    def __init__(
        self,
        lexicon: "RootLexicon | None" = None,
        formatter: "Formatter | None" = None,
        return_all_lemmas: bool = False,
    ):
        self.lexicon = lexicon or RootLexicon.default_text_dictionaries()

        self.morphotactics = TurkishMorphotactics(self.lexicon)
        self.analyzer = RuleBasedAnalyzer(self.morphotactics)
        self.formatter = (
            DefaultFormatter(True)
            if formatter is None
            else MorphAnalyzer.formatters[formatter]()
        )
        self.return_all_lemmas = return_all_lemmas

    def _parse(self, word: str) -> list[SingleAnalysis]:
        """ Parses a word and returns SingleAnalysis result. """
        normalized_word = _normalize(word)
        return self.analyzer.analyze(normalized_word)

    def _analyze_text(self, text, verbose=False):
        result = []
        sentences = sent_tokenize(text, language="turkish")
        for sentence in sentences:
            sentence_analysis = self.analyze(sentence)
            result.append((sentence, sentence_analysis))
        return result

    def analyze(self, text: str) -> list[list[Parse]]:
        """
        Public method that returns a list of analyses for each word in given text
        :param text: Text to analyze
        :return: List of lists of Parse objects for each word
        """
        result = []
        for word in _tokenize_text(text):
            analysis = self._parse(word)
            if len(analysis) == 0:
                result.append([Parse(word, 'Unk', 'Unk', ['Unk'], 'Unk')])
            word_analysis = []
            for a in analysis:
                if a is not None:
                    formatted = self.formatter.format(a)
                    morpheme_list = [m[0].id_ for m in a.morphemes]
                    word_analysis.append(Parse(word, a.dict_item.lemma, a.pos.value, morpheme_list, formatted))
                else:
                    word_analysis.append(Parse(word, 'Unk', 'Unk', ["Unk"], 'Unk'))
            result.append(word_analysis)
        return result

    def lemmatize(self, text: str) -> "list[tuple[str, list]] | list[str]":
        """
        This method will eventually use some form of disambiguation for lemmatizing.
        Currently, it simply returns all lemmas available for each word of the text.
        :param text: The text which needs lemmatization.
        :return: A list of tuples: sentence and a list of list of
        lemmas for all words of the text
        """
        return_all_lemmas = self.return_all_lemmas
        result = []
        words = _tokenize_text(text)
        for word in words:
            analysis = self._parse(word)
            if return_all_lemmas:
                if len(analysis) == 0:
                    word_lemmas = [word]
                else:
                    analysis_lemmas = [a.dict_item.lemma for a in analysis]
                    filtered_lemmas = list(set(analysis_lemmas))
                    word_lemmas = filtered_lemmas
                result.append((word, word_lemmas))

            else:
                analysis = self.filter_proper_nouns(word, analysis)
                result.append(analysis[0].dict_item.lemma if analysis else word)
        return result

    @staticmethod
    def filter_proper_nouns(word: str, analysis: list[SingleAnalysis]):
        if word[0].isupper():
            only_proper_nouns = [a for a in analysis if a.dict_item.secondary_pos == SecondaryPos.ProperNoun]
            analysis = only_proper_nouns if only_proper_nouns else analysis
        else:
            without_proper_nouns = [a for a in analysis if a.dict_item.secondary_pos != SecondaryPos.ProperNoun]
            if without_proper_nouns:
                analysis = without_proper_nouns
        return analysis

    def add_dictionary(self, path_to_dictionary: str):
        """
        Adds a user-defined dictionary to use for analysis.
        Dictionary should be a text file with one word per line.

        Each word should have attributes on its line:
        - part of speech (a word without part of speech is assumed to be a noun)
        - secondary part of speech and root attributes (NoVoicing, etc.)
        example dictionary line: `biyomedikal [P:Adj; A:InverseHarmony]`
        List of possible root attributes can be found in :py:mod:`attributes.py`
        in :py:class:`~RootAttribute`

        :param path_to_dictionary: string path to the dictionary file
        """
        lexicon_from_path = self.lexicon.add_dictionary_from_path(path_to_dictionary)
        self.morphotactics.stem_transitions.add_lexicon_items(lexicon_from_path.items)
