"""
Measures the disambiguator on the annotated sentences in `data/disambiguation-gold.txt`.

    uv run python -m tests.evaluate_disambiguation
    uv run python -m tests.evaluate_disambiguation --errors

The file has the format of Zemberek's gold files: a line `S:<sentence>` starts each
sentence, then each token is followed by its analyses, and the correct analysis of an
ambiguous token ends with "*".
"""

import argparse
from pathlib import Path
from typing import NamedTuple

from zeyrek import MorphAnalyzer

GOLD = Path(__file__).parent / "data" / "disambiguation-gold.txt"


class Token(NamedTuple):
    word: str
    gold: "str | None"


class Result(NamedTuple):
    ambiguous: int
    model: int
    old_rule: int
    # Sentence number, word, correct analysis, the disambiguator's choice.
    errors: list[tuple[int, str, str, str]]
    # Tokens whose correct analysis zeyrek no longer gives.
    missing: list[tuple[int, str, str]]


def read_gold(path: Path = GOLD) -> list[list[Token]]:
    sentences: list[list[Token]] = []
    for line in path.read_text(encoding="utf8").splitlines():
        if not line or line.startswith("#"):
            continue
        if line.startswith("S:"):
            sentences.append([])
        elif line.startswith("["):
            if line.endswith("*"):
                sentences[-1][-1] = sentences[-1][-1]._replace(gold=line[:-1])
        else:
            sentences[-1].append(Token(line, None))
    return sentences


def evaluate(analyzer: MorphAnalyzer, path: Path = GOLD) -> Result:
    """
    Compares the disambiguator, and the rule `lemmatize` used before it, with the
    annotations of the ambiguous tokens.
    """
    fmt = analyzer.formatter.format
    ambiguous = model = old_rule = 0
    errors, missing = [], []
    for number, sentence in enumerate(read_gold(path), 1):
        words = [token.word for token in sentence]
        best = analyzer._best_analyses(words)
        for token, analysis in zip(sentence, best, strict=True):
            if token.gold is None:
                continue
            candidates = list(analyzer._parse(token.word))
            if token.gold not in [fmt(a) for a in candidates]:
                missing.append((number, token.word, token.gold))
                continue
            ambiguous += 1
            chosen = fmt(analysis)
            if chosen == token.gold:
                model += 1
            else:
                errors.append((number, token.word, token.gold, chosen))
            old = analyzer.filter_proper_nouns(token.word, candidates)[0]
            old_rule += fmt(old) == token.gold
    return Result(ambiguous, model, old_rule, errors, missing)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--errors", action="store_true", help="list the mistakes")
    parser.add_argument("--gold", type=Path, default=GOLD, help="annotated file")
    args = parser.parse_args()
    result = evaluate(MorphAnalyzer(), args.gold)
    total = result.ambiguous
    print(f"Ambiguous tokens: {total}")
    print(f"Disambiguator:    {result.model} ({result.model / total:.1%})")
    print(f"Old rule:         {result.old_rule} ({result.old_rule / total:.1%})")
    if result.missing:
        print(f"Skipped {len(result.missing)} tokens whose annotated analysis is gone:")
        for number, word, gold in result.missing:
            print(f"  {number}: {word}  {gold}")
    if args.errors:
        for number, word, gold, chosen in result.errors:
            print(f"{number}: {word}\n  annotated: {gold}\n  chosen:    {chosen}")


if __name__ == "__main__":
    main()
