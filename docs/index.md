# Zeyrek

Zeyrek is a python morphological analyzer and lemmatizer for Turkish.
It is a partial port of the [Zemberek-NLP Tools (Morphology)](https://github.com/ahmetaa/zemberek-nlp)
Zeyrek can perform morphological analysis of Turkish text, returning all
possible parses for each word, and lemmatize words, returning all possible
base (non-inflected) forms of words.

## Usage

To use Zeyrek, first create an instance of MorphAnalyzer class:

```pycon
>>> import zeyrek
>>> analyzer = zeyrek.MorphAnalyzer()
```

Then, you can call its `analyze` method on words or texts to get all possible analyses:

```pycon
>>> for parse in analyzer.analyze("benim")[0]:
...     print(parse)
Parse(word='benim', lemma='ben', pos='Noun', morphemes=['Noun', 'A3sg', 'P1sg'], formatted='[ben:Noun] ben:Noun+A3sg+im:P1sg')
Parse(word='benim', lemma='ben', pos='Pron', morphemes=['Pron', 'A1sg', 'Gen'], formatted='[ben:Pron,Pers] ben:Pron+A1sg+im:Gen')
Parse(word='benim', lemma='ben', pos='Verb', morphemes=['Noun', 'A3sg', 'Zero', 'Verb', 'Pres', 'A1sg'], formatted='[ben:Noun] ben:Noun+A3sg|Zero→Verb+Pres+im:A1sg')
Parse(word='benim', lemma='ben', pos='Verb', morphemes=['Pron', 'A1sg', 'Zero', 'Verb', 'Pres', 'A1sg'], formatted='[ben:Pron,Pers] ben:Pron+A1sg|Zero→Verb+Pres+im:A1sg')
```

If you only need the base form of words, or lemmas, you can call `lemmatize`. It returns
the most likely lemma for each word of the text:

```pycon
>>> analyzer.lemmatize("benim evim")
['ben', 'ev']
```

To get every possible lemma, create the analyzer with `return_all_lemmas=True`. `lemmatize`
then returns a list of tuples, with each word and a list of its possible lemmas:

```pycon
>>> zeyrek.MorphAnalyzer(return_all_lemmas=True).lemmatize("benim")
[('benim', ['ben'])]
```

A lemma is the root of the word, and derivational suffixes can change its meaning a lot. `derived_lemmas`
returns, for each analysis of a word, the lemmas from the root to the stem after the last derivational
suffix. The last one is the word without its inflectional suffixes:

```pycon
>>> analyzer.derived_lemmas("çekilişle")
[['çekiliş'], ['çekil', 'çekiliş'], ['çek', 'çekil', 'çekiliş']]
```

## Installation

To install Zeyrek, run this command in your terminal:

```shell
$ pip install zeyrek
```

Zeyrek uses NLTK's Punkt tokenizer to split texts into sentences and words. Download its data once:

```shell
$ python -m nltk.downloader punkt_tab
```

## User Guide

Zeyrek's morphological analyzer returns instances of Parse object (based on pymorphy2's Parse),
which is a wrapper of namedtuple class.

Parse object fields include:

- `word`: the word itself
- `lemma`: base form of the word, as found in a dictionary
- `pos`: part of speech of the word. Note: Turkish is an agglutinative language, which makes it
  quite different from widespread European languages. A word can usually be much longer,
  made of Inflection Groups (IG), which can correspond to words in other languages. Each of these
  IGs can have its own part of speech, and the part of speech of the word as a whole is determined
  by the part of speech of the last IG.
- `morphemes`: sequence of morphemes in the word, a list of strings - abbreviations of English names of morphemes.
- `formatted`: the analysis as a string, written by the analyzer's formatter. See [Formatters](#formatters).

## Formatters

A formatter turns an analysis into the `formatted` string of a `Parse`. Zeyrek has two formatters.

### Default formatter

The default formatter writes the analysis the way Zemberek does:

```pycon
>>> analyzer.analyze_word("kitaplarımdan")[0].formatted
'[kitap:Noun] kitap:Noun+lar:A3pl+ım:P1sg+dan:Abl'
```

- `[kitap:Noun]` is the dictionary item: its lemma and part of speech. A secondary part of speech
  follows a comma, as in `[ben:Pron,Pers]` or `[Ankara:Noun,Prop]`.
- `kitap:Noun` is the stem of the word, then its first morpheme.
- `+lar:A3pl` is the next morpheme, with the letters it adds to the word before the colon.
  A morpheme with no letters, such as `A3sg`, is written without a colon.
- `|` starts a new inflectional group, and `→` follows the derivational morpheme that changes the part of
  speech. In `güzeldi`, the adjective becomes a verb:

```pycon
>>> analyzer.analyze_word("güzeldi")[0].formatted
'[güzel:Adj] güzel:Adj|Zero→Verb+di:Past+A3sg'
```

To leave the surfaces out, set a `DefaultFormatter` with `add_surface=False`:

```pycon
>>> from zeyrek.formatters import DefaultFormatter
>>> analyzer.formatter = DefaultFormatter(add_surface=False)
>>> analyzer.analyze_word("kitaplarımdan")[0].formatted
'[kitap:Noun] Noun+A3pl+P1sg+Abl'
```

### Universal Dependencies formatter

`formatter="UD"` writes the features of the word as
[Universal Dependencies](https://universaldependencies.org/u/feat/index.html) features, the format of the
Turkish UD treebanks:

```pycon
>>> ud_analyzer = zeyrek.MorphAnalyzer(formatter="UD")
>>> ud_analyzer.analyze_word("kitaplarımdan")[0].formatted
'Case=Abl|Number=Plur|Number[psor]=Sing|Person=3|Person[psor]=1'
>>> ud_analyzer.analyze_word("geliyorum")[0].formatted
'Aspect=Prog|Mood=Ind|Number=Sing|Person=1|Polarity=Pos|Polite=Infm|Tense=Pres'
>>> ud_analyzer.analyze_word("okuyacakmışsın")[0].formatted
'Aspect=Perf|Evident=Nfh|Mood=Ind|Number=Sing|Person=2|Polarity=Pos|Tense=Fut'
>>> ud_analyzer.analyze_word("üç")[0].formatted
'NumType=Card'
```

A word gets the features of the part of speech it ends in. `evdeyim`, "I am at home", is a noun that
becomes a verb, so it gets the features of a verb and keeps the case of the noun:

```pycon
>>> ud_analyzer.analyze_word("evdeyim")[0].formatted
'Aspect=Perf|Case=Loc|Mood=Ind|Number=Sing|Person=1|Polarity=Pos|Tense=Pres'
```

A derivational suffix makes a new word with its own case. In `evdekiler`, "the ones at home", the
locative belongs to `evde`, and the word after `-ki` is in the nominative. Each analysis has its own features:

```pycon
>>> for parse in ud_analyzer.analyze_word("evdekiler"):
...     print(parse.pos, parse.formatted)
Verb Aspect=Perf|Mood=Ind|Number=Plur|Person=3|Polarity=Pos|Tense=Pres
Noun Case=Nom|Number=Plur|Person=3
```

The UD formatter writes features for nouns, verbs, pronouns, numerals and adjectives. Other parts of speech,
such as conjunctions, are written in the default format:

```pycon
>>> ud_analyzer.analyze_word("ve")[0].formatted
'[ve:Conj] ve:Conj'
```

### Writing your own formatter

A formatter is a subclass of `zeyrek.formatters.Formatter` with a `format` method that takes an analysis
and returns a string. The analysis has the dictionary item in `dict_item`, the stem in `stem`,
and the morphemes with their surfaces in `morphemes`:

```pycon
>>> from zeyrek.formatters import Formatter
>>> class MorphemeIds(Formatter):
...     def format(self, analysis):
...         return " ".join(morpheme.id_ for morpheme, _ in analysis.morphemes)
>>> analyzer.formatter = MorphemeIds()
>>> analyzer.analyze_word("kitaplarımdan")[0].formatted
'Noun A3pl P1sg Abl'
```

## License

Licensed under MIT License.
Zemberek, from parts of which Zeyrek was ported, is under Apache License, Version 2.0.

## Disclaimer

This project is in alpha stage, so the API can change.
