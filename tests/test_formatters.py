import pytest

from zeyrek.morphology import MorphAnalyzer


@pytest.fixture(scope="module")
def analyzer():
    return MorphAnalyzer(formatter="UD")


def adjective_features(analyzer, word):
    return [
        parse.formatted
        for parse in analyzer.analyze_word(word)
        if parse.morphemes[0] == "Adj"
    ]


@pytest.mark.parametrize(
    ("word", "features"),
    [
        ("ek", "_"),
        ("kırmızıya", "Case=Dat|Number=Sing|Person=3"),
        (
            "güzeldi",
            "Aspect=Perf|Mood=Ind|Number=Sing|Person=3|Polarity=Pos|Tense=Past",
        ),
    ],
)
def test_ud_features_of_adjectives(analyzer, word, features):
    assert features in adjective_features(analyzer, word)


def test_ud_formatter_does_not_fall_back_to_default_format(analyzer):
    # https://github.com/obulat/zeyrek/issues/41
    sentence = (
        "Ek olarak yaşlılar birbirleriyle sosyalleşebilsin ve Amerikan hayatının "
        "aktif üyeleri olarak kalabilsinler diye birçok topluluk kurulmuştur."
    )
    for word in sentence.rstrip(".").split():
        for parse in analyzer.analyze_word(word):
            if parse.morphemes[0] == "Adj":
                assert not parse.formatted.startswith("["), (word, parse.formatted)


def ud_features(analyzer, word, morphemes):
    return [
        parse.formatted
        for parse in analyzer.analyze_word(word)
        if parse.morphemes == morphemes
    ]


@pytest.mark.parametrize(
    ("word", "morphemes", "features"),
    [
        (
            "güzeldi",
            ["Noun", "A3sg", "Zero", "Verb", "Past", "A3sg"],
            "Aspect=Perf|Mood=Ind|Number=Sing|Person=3|Polarity=Pos|Tense=Past",
        ),
        (
            "evdeyim",
            ["Noun", "A3sg", "Loc", "Zero", "Verb", "Pres", "A1sg"],
            "Aspect=Perf|Case=Loc|Mood=Ind|Number=Sing|Person=1|Polarity=Pos|Tense=Pres",
        ),
    ],
)
def test_ud_features_of_a_noun_that_becomes_a_verb(analyzer, word, morphemes, features):
    assert ud_features(analyzer, word, morphemes) == [features]


@pytest.mark.parametrize(
    ("morphemes", "features"),
    [
        (
            ["Noun", "A3sg", "Loc", "Rel", "Adj", "Zero", "Noun", "A3pl"],
            "Case=Nom|Number=Plur|Person=3",
        ),
        (
            ["Noun", "A3sg", "Loc", "Rel", "Adj", "Zero", "Verb", "Pres", "A3pl"],
            "Aspect=Perf|Mood=Ind|Number=Plur|Person=3|Polarity=Pos|Tense=Pres",
        ),
    ],
)
def test_ud_case_before_a_derivation_is_dropped(analyzer, morphemes, features):
    assert ud_features(analyzer, "evdekiler", morphemes) == [features]


def test_ud_future_tense_with_evidential(analyzer):
    assert ud_features(analyzer, "okuyacakmışsın", ["Verb", "Fut", "Narr", "A2sg"]) == [
        "Aspect=Perf|Evident=Nfh|Mood=Ind|Number=Sing|Person=2|Polarity=Pos|Tense=Fut"
    ]
