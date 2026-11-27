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
