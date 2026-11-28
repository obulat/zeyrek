"""
Morphological disambiguation: choosing the analysis of each word of a sentence from
its context.

This is a port of Zemberek's `FastPerceptronAmbiguityResolver`. It uses Zemberek's
trained model, `resources/tr/ambiguity/model_15k_v25.bin`. The model gives a weight
to each feature of three consecutive analyses, such as the lemma of the previous word
and the morphemes of this one, and the Viterbi search picks the analyses of the
sentence with the highest total weight.
"""

import functools
import itertools
import struct
from array import array
from pathlib import Path
from typing import NamedTuple

from zeyrek.attributes import PrimaryPos, SecondaryPos
from zeyrek.rulebasedanalyzer import SingleAnalysis

MODEL_PATH = (
    Path(__file__).parent / "resources" / "tr" / "ambiguity" / "model_15k_v25.bin"
)

_MAGIC = 0xCAFEBEEF
_MPHF_SEED = 0x811C9DC5
_MPHF_MULTIPLIER = 16777619


def _utf16_units(text: str) -> tuple[int, ...]:
    """Java strings are hashed by their UTF-16 code units."""
    data = text.encode("utf-16-be")
    return struct.unpack(f">{len(data) // 2}H", data)


def _java_hash(units: tuple[int, ...]) -> int:
    """`String.hashCode` in Java, as an unsigned 32-bit number."""
    h = 0
    for unit in units:
        h = (31 * h + unit) & 0xFFFFFFFF
    return h


def _mphf_hash(units: tuple[int, ...], seed: int) -> int:
    d = seed if seed > 0 else _MPHF_SEED
    for unit in units:
        d = ((d ^ unit) * _MPHF_MULTIPLIER) & 0xFFFFFFFF
    return d & 0x7FFFFFFF


class _HashLevel(NamedTuple):
    key_count: int
    bucket_count: int
    seeds: bytes
    failed_indexes: array


def _read_ints(data: memoryview, offset: int, count: int) -> tuple[array, int]:
    ints = array("i")
    ints.frombytes(data[offset : offset + 4 * count])
    if ints.itemsize != 4:
        raise RuntimeError("32-bit integers are needed to read the model.")
    if struct.pack("=i", 1) != struct.pack(">i", 1):
        ints.byteswap()
    return ints, offset + 4 * count


class Weights:
    """
    The feature weights of Zemberek's `LossyIntLookup`: a minimal perfect hash
    gives the index of a feature, and a fingerprint of the feature at that index
    tells whether the model has it. Features the model doesn't have weigh 0.
    """

    def __init__(self, path: Path = MODEL_PATH):
        data = memoryview(Path(path).read_bytes())
        magic, length = struct.unpack_from(">Ii", data)
        if magic != _MAGIC:
            raise ValueError(f"{path} is not a Zemberek model file.")
        self._data, offset = _read_ints(data, 8, length)
        (level_count,) = struct.unpack_from(">i", data, offset)
        offset += 4
        self._levels = []
        for _ in range(level_count):
            key_count, bucket_count = struct.unpack_from(">ii", data, offset)
            offset += 8
            seeds = bytes(data[offset : offset + bucket_count])
            offset += bucket_count
            (failed_count,) = struct.unpack_from(">i", data, offset)
            failed, offset = _read_ints(data, offset + 4, failed_count)
            self._levels.append(_HashLevel(key_count, bucket_count, seeds, failed))
        self.get = functools.lru_cache(maxsize=1_000_000)(self._get)

    def __len__(self):
        return len(self._data) // 2

    def _index(self, units: tuple[int, ...]) -> int:
        initial_hash = _mphf_hash(units, -1)
        for i, level in enumerate(self._levels):
            seed = level.seeds[initial_hash % level.bucket_count]
            if seed:
                index = _mphf_hash(units, seed) % level.key_count
                return index if i == 0 else self._levels[i - 1].failed_indexes[index]
        raise ValueError("The model's hash levels are broken.")

    def _get(self, feature: str) -> float:
        units = _utf16_units(feature)
        fingerprint = _java_hash(units) & 0x7FFFFFF
        index = self._index(units) * 2
        if self._data[index] != fingerprint:
            return 0.0
        return struct.unpack(">f", struct.pack(">i", self._data[index + 1]))[0]


class _Word(NamedTuple):
    """The parts of an analysis the features are made of."""

    analysis: "SingleAnalysis | None"
    lemma: str
    groups: tuple[str, ...]
    lemma_and_groups: str
    is_verb: bool
    ends_sentence: bool
    upper_proper: bool
    lower_proper: bool

    @property
    def last_group(self) -> str:
        return self.groups[-1]


def _boundary(token: str) -> _Word:
    return _Word(None, token, (token,), f"{token}+{token}", False, False, False, False)


SENTENCE_BEGIN = _boundary("<s>")
SENTENCE_END = _boundary("</s>")._replace(ends_sentence=True)


def _word(analysis: SingleAnalysis) -> _Word:
    item = analysis.dict_item
    boundaries = [*analysis.group_boundaries, len(analysis.morphemes)]
    groups = [
        "".join(morpheme.id_ for morpheme, _ in analysis.morphemes[start:end])
        for start, end in itertools.pairwise(boundaries)
    ]
    if item.secondary_pos != SecondaryPos.NONE:
        groups[0] = item.secondary_pos.name + groups[0]
    surface = "".join(surface for _, surface in analysis.morphemes)
    proper = item.secondary_pos == SecondaryPos.ProperNoun and surface
    return _Word(
        analysis,
        item.lemma,
        tuple(groups),
        f"{item.lemma}+{'+'.join(groups)}",
        item.primary_pos == PrimaryPos.Verb,
        surface == ".",
        bool(proper and surface[0].isupper()),
        bool(proper and surface[0].islower()),
    )


def _unknown(token: str) -> _Word:
    """Zemberek's `SingleAnalysis.unknown`, for a word without analyses."""
    return _Word(
        None, "UNK", ("UnknownSecUnknown",), "UNK+UnknownSecUnknown", *[False] * 4
    )._replace(ends_sentence=token == ".")


class Disambiguator:
    def __init__(self, weights: "Weights | None" = None):
        self.weights = weights or default_weights()

    def _unigram(self, word: _Word, sentence_initial: bool) -> float:
        get = self.weights.get
        score = (
            get(f"4:{word.lemma_and_groups}")
            + get(f"10:{word.lemma}")
            + get(f"22:{len(word.groups)}")
        )
        score += sum(get(f"20:{k}-{group}") for k, group in enumerate(word.groups))
        if word.upper_proper:
            if sentence_initial:
                score += get(f"P:INIT_PROPER:{word.lemma}")
            else:
                score += get("P:PROPER") + get(f"P:PROPER:{word.lemma}")
        elif word.lower_proper:
            score += get("P:LOWER_PROPER")
        return score

    def _bigram(self, previous: _Word, word: _Word) -> float:
        get = self.weights.get
        score = (
            get(f"3:{previous.lemma_and_groups}-{word.lemma_and_groups}")
            + get(f"9:{previous.lemma}-{word.lemma}")
            + get(f"10b:{previous.lemma}")
        )
        score += sum(get(f"17:{previous.last_group}-{group}") for group in word.groups)
        if word.ends_sentence and previous.is_verb:
            score += get("P:ENDSVERB")
        return score

    def _trigram(self, first: _Word, previous: _Word, word: _Word) -> float:
        get = self.weights.get
        score = get(f"2:{first.lemma_and_groups}-{word.lemma_and_groups}") + get(
            f"10c:{first.lemma}"
        )
        prefix = f"15:{first.last_group}-{previous.last_group}-"
        return score + sum(get(prefix + group) for group in word.groups)

    def best_analyses(
        self, tokens: list[str], analyses: list[list[SingleAnalysis]]
    ) -> "list[SingleAnalysis | None]":
        """
        The analysis with the highest score in its sentence for each token, or None
        for tokens without analyses.

        A Viterbi search over pairs of consecutive analyses, as the features look at
        three words at a time.
        """
        words = [[SENTENCE_BEGIN], [SENTENCE_BEGIN]]
        words += [
            [_word(a) for a in word_analyses] or [_unknown(token)]
            for token, word_analyses in zip(tokens, analyses, strict=True)
        ]
        words.append([SENTENCE_END])
        # A state is the indexes of the analyses of the last two words, with the
        # score of the best path to it and that path.
        states = {(0, 0): (0.0, ())}
        for position in range(2, len(words)):
            sentence_initial = position == 2
            firsts, previous_words, candidates = words[position - 2 : position + 1]
            unigrams = [self._unigram(word, sentence_initial) for word in candidates]
            bigrams = {}
            next_states = {}
            for (i, j), (score, path) in states.items():
                first, previous = firsts[i], previous_words[j]
                if j not in bigrams:
                    bigrams[j] = [self._bigram(previous, word) for word in candidates]
                for k, word in enumerate(candidates):
                    total = (
                        score
                        + unigrams[k]
                        + bigrams[j][k]
                        + self._trigram(first, previous, word)
                    )
                    if (j, k) not in next_states or total > next_states[j, k][0]:
                        next_states[j, k] = (total, (*path, k))
            states = next_states
        _, path = max(states.values(), key=lambda state: state[0])
        return [
            words[position][k].analysis for position, k in enumerate(path[:-1], start=2)
        ]


@functools.cache
def default_weights() -> Weights:
    return Weights(MODEL_PATH)
