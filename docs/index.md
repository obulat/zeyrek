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

`MorphAnalyzer` keeps the analyses of the last 10,000 words it saw, so repeated words in a text
are analysed once. Set the size with `cache_size`, or turn the cache off with `cache_size=0`:

```pycon
>>> analyzer = zeyrek.MorphAnalyzer(cache_size=50_000)
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
- `formatted`: a human-readable string representation of the analysis. There are several kinds of
  possible formats. Default formatter shows the dictionary item and its part of speech,
  and morphemes (with their surfaces, if available), divided into inflectional groups by `|` character.

## License

Licensed under MIT License.
Zemberek, from parts of which Zeyrek was ported, is under Apache License, Version 2.0.

## Disclaimer

This project is in alpha stage, so the API can change.
