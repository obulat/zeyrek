"""Main module."""

import functools
import itertools
import re
from typing import ClassVar, NamedTuple

from zeyrek import tr
from zeyrek.attributes import PrimaryPos, SecondaryPos
from zeyrek.formatters import DefaultFormatter, Formatter, UDFormatter
from zeyrek.lexicon import DictionaryItem, RootLexicon
from zeyrek.lexicon_helpers import (
    to_turkish_letter_pronunciation,
    turkish_numbers_to_string,
)
from zeyrek.morphotactics import Morpheme, StemTransition, TurkishMorphotactics
from zeyrek.rulebasedanalyzer import RuleBasedAnalyzer, SingleAnalysis

NUMBER = re.compile(r"[+-]?\d+(?:[.,]\d+)*")
THOUSANDS = re.compile(r"[+-]?\d{1,3}(?:\.\d{3})+")
APOSTROPHE_ROOTS = (SecondaryPos.ProperNoun, SecondaryPos.Abbreviation)
# Ottoman Turkish joins nouns with the Persian izafet, "bakiye-i ömür", and the
# Arabic article, "Şeyh-ül İslam", written after a hyphen.
OTTOMAN_LINK = re.compile(r"(\w+)-(?:ı|i|u|ü|ul|ül)")


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
    word = word.replace("'", "").replace("’", "")
    return word


def _tokenize_text(text: str) -> list[str]:
    from nltk.tokenize import word_tokenize

    # NLTK keeps "Ankara'da" in one token, but splits "Ankara’da" in three.
    return word_tokenize(text.replace("’", "'"), language="turkish")


def _read_number(number: str) -> tuple[str, SecondaryPos]:
    """
    How a number is read, which decides the vowels of its suffixes, and whether it is
    a whole number. "1.000" is "bin", and "3,5" ends in "beş".
    """
    number = number.lstrip("+-")
    if THOUSANDS.fullmatch(number):
        return turkish_numbers_to_string(number.replace(".", "")), SecondaryPos.Cardinal
    *whole, last = re.split(r"[.,]", number)
    kind = SecondaryPos.Real if whole else SecondaryPos.Cardinal
    return turkish_numbers_to_string(last), kind


def _derived_lemmas(analysis: SingleAnalysis) -> list[str]:
    """
    The lemma, then the stem after each derivational suffix, as Zemberek's
    `SingleAnalysis.getLemmas` does.
    """

    def unvoice(stem: str) -> str:
        # "çocukluğ-umuz" is "çocukluk" without its suffixes.
        return stem[:-1] + "k" if stem.endswith("ğ") else stem

    lemmas = [analysis.dict_item.normalized_lemma]
    surfaces = [surface for _, surface in analysis.morphemes]
    boundaries = [*analysis.group_boundaries, len(surfaces)]
    stem = "".join(surfaces[: boundaries[1]])
    for start, end in itertools.pairwise(boundaries[1:]):
        lemma = unvoice(stem + surfaces[start])
        if lemma not in lemmas:
            lemmas.append(lemma)
        stem += "".join(surfaces[start:end])
    return lemmas


class MorphAnalyzer:
    """
    Morphological analyzer for Turkish language.

    It analyzes each word to suggest all possible morphological analyses.

    Create a :class:`TrLemmer` object ::

        >>> import zeyrek
        >>> lemmer = zeyrek.MorphAnalyzer()

    Analyzer uses default text dictionaries from Zemberek-NLP. All dictionaries are
    in resources/tr folder. Numbers, and unknown proper nouns written with an
    apostrophe, such as "Melik'in", are analyzed too. You can also add your own dictionary files in .txt format, with
    each word on its own line.

        >>> lemmer.add_dictionary('/path/to/file')

    The analyses of the last `cache_size` words are cached, so repeated words are
    analyzed once. Pass `cache_size=0` to turn the cache off.

    TrLemmer can analyze or lemmatize words and sentences.

        >>> lemmer.lemmatize('beyazlaştırmak')
        ['beyaz']

    Methods should be:
    analyze: public method, takes in a string with one/more words, returns list of lists of Parses.
    lemmatize: public method, takes in a string with one/more words, returns list of lists of strings: lemmas

    Each method uses method _parse to get SingleAnalysis for the word
    """

    formatters: ClassVar[dict[str, type[Formatter]]] = {"UD": UDFormatter}

    def __init__(
        self,
        lexicon: "RootLexicon | None" = None,
        formatter: "Formatter | None" = None,
        return_all_lemmas: bool = False,
        cache_size: int = 10_000,
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
        # Texts repeat the same words a lot, so the analyses of the latest words are
        # kept.
        self._cached_analyses = functools.lru_cache(maxsize=cache_size)(
            lambda word: tuple(self._analyze(word))
        )

    def _parse(self, word: str) -> list[SingleAnalysis]:
        """Parses a word and returns SingleAnalysis result."""
        return list(self._cached_analyses(word))

    def _analyze(self, word: str) -> list[SingleAnalysis]:
        stem, apostrophe, ending = word.replace("’", "'").partition("'")
        if NUMBER.fullmatch(stem):
            return self._parse_number(stem, _normalize(ending))
        normalized_word = _normalize(word)
        analyses = self.analyzer.analyze(normalized_word) or self._parse_ottoman_link(
            normalized_word
        )
        if not (apostrophe and stem):
            return analyses
        # An apostrophe separates a proper noun or an abbreviation from its suffixes,
        # so the root is the part before it.
        root = _normalize(stem)
        proper = [
            a
            for a in analyses
            if a.stem == root and a.dict_item.secondary_pos in APOSTROPHE_ROOTS
        ]
        # In Ottoman words like "Mün'im", the apostrophe stands for a letter instead.
        return proper or self._parse_proper_noun(stem, _normalize(ending)) or analyses

    def _analyze_unknown_stem(self, item: DictionaryItem, ending: str):
        transition = StemTransition(item, self.morphotactics.get_root_state(item))
        return self.analyzer.analyze_with_stem(transition, ending)

    def _parse_proper_noun(self, stem: str, ending: str) -> list[SingleAnalysis]:
        root = _normalize(stem)
        if not root.isalpha():
            return []
        if stem.isupper() and len(stem) > 1 or not tr.contains_vowel(root):
            kind = SecondaryPos.Abbreviation
            pronunciation = to_turkish_letter_pronunciation(root)
        else:
            kind, pronunciation = SecondaryPos.ProperNoun, root
        item = DictionaryItem(
            stem, root, PrimaryPos.Noun, kind, set(), pronunciation, 0
        )
        return self._analyze_unknown_stem(item, ending)

    def _parse_number(self, number: str, ending: str) -> list[SingleAnalysis]:
        reading, kind = _read_number(number)
        pronunciation = reading.replace(" ", "")
        item = DictionaryItem(
            number, number, PrimaryPos.Numeral, kind, set(), pronunciation, 0
        )
        return self._analyze_unknown_stem(item, ending)

    def _parse_ottoman_link(self, word: str) -> list[SingleAnalysis]:
        """Analyzes the noun of "bakiye-i", without the izafet after the hyphen."""
        match = OTTOMAN_LINK.fullmatch(word)
        return self.analyzer.analyze(match[1]) if match else []

    def _analyze_text(self, text, verbose=False):
        from nltk.tokenize import sent_tokenize

        result = []
        sentences = sent_tokenize(text, language="turkish")
        for sentence in sentences:
            sentence_analysis = self.analyze(sentence)
            result.append((sentence, sentence_analysis))
        return result

    def analyze_word(self, word: str) -> list[Parse]:
        """
        Public method that returns the analyses of a single word, without tokenizing it,
        so NLTK's tokenizer data is not needed.
        :param word: Word to analyze
        :return: List of Parse objects; a single 'Unk' Parse if the word is unknown
        """
        analysis = [a for a in self._parse(word) if a is not None]
        if not analysis:
            return [Parse(word, "Unk", "Unk", ["Unk"], "Unk")]
        return [
            Parse(
                word,
                a.dict_item.lemma,
                a.pos.value,
                [m[0].id_ for m in a.morphemes],
                self.formatter.format(a),
            )
            for a in analysis
        ]

    def analyze(self, text: str) -> list[list[Parse]]:
        """
        Public method that returns a list of analyses for each word in given text
        :param text: Text to analyze
        :return: List of lists of Parse objects for each word
        """
        return [self.analyze_word(word) for word in _tokenize_text(text)]

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

    def derived_lemmas(self, word: str) -> list[list[str]]:
        """
        Lemmas of a word for each of its analyses, from the root to the stem after
        the last derivational suffix. That last stem is the word without its
        inflectional suffixes, so it keeps the word's meaning.

            >>> analyzer.derived_lemmas("çekilişle")
            [['çekiliş'], ['çekil', 'çekiliş'], ['çek', 'çekil', 'çekiliş']]

        :param word: Word to analyze
        :return: A list of lemmas for each analysis; empty if the word is unknown
        """
        result = []
        for analysis in self._parse(word):
            lemmas = _derived_lemmas(analysis)
            if lemmas not in result:
                result.append(lemmas)
        return result

    @staticmethod
    def filter_proper_nouns(word: str, analysis: list[SingleAnalysis]):
        if word[0].isupper():
            only_proper_nouns = [
                a
                for a in analysis
                if a.dict_item.secondary_pos == SecondaryPos.ProperNoun
            ]
            analysis = only_proper_nouns if only_proper_nouns else analysis
        else:
            without_proper_nouns = [
                a
                for a in analysis
                if a.dict_item.secondary_pos != SecondaryPos.ProperNoun
            ]
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
        self._cached_analyses.cache_clear()
