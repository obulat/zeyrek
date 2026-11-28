# Zeyrek: Morphological Analyzer and Lemmatizer

![PyPI - Version](https://img.shields.io/pypi/v/zeyrek)

Zeyrek is a partial port of the [Zemberek library](https://github.com/ahmetaa/zemberek-nlp) to Python for lemmatizing
and analyzing Turkish language words. It is in alpha stage, and the API
will probably change.


* Free software: MIT license
* Documentation: https://zeyrek.readthedocs.io.


## Basic Usage

Install Zeyrek and the NLTK tokenizer data it uses:

```shell
pip install zeyrek
python -m nltk.downloader punkt_tab
```

To use Zeyrek, first create an instance of `MorphAnalyzer` class:

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

A word often has several analyses, and the right one depends on the sentence. `disambiguate`
returns the most likely analysis of each word, chosen with Zemberek's disambiguation model.
`kitabı` is "the book" as an object in the first sentence, and "his book" in the second:

```pycon
>>> for parse in analyzer.disambiguate("Bu kitabı okudum. Ali'nin kitabı masada."):
...     print(parse.formatted)
[bu:Det] bu:Det
[kitap:Noun] kitab:Noun+A3sg+ı:Acc
[okumak:Verb] oku:Verb+du:Past+m:A1sg
[.:Punc] .:Punc
[Ali:Noun,Prop] ali:Noun+A3sg+nin:Gen
[kitap:Noun] kitab:Noun+A3sg+ı:P3sg
[masa:Noun] masa:Noun+A3sg+da:Loc
[.:Punc] .:Punc
```

If you only need the base form of words, or lemmas, you can call `lemmatize`. It returns
the lemma of the most likely analysis of each word:

```pycon
>>> analyzer.lemmatize("Mektup onun tarafından yazıldı.")
['mektup', 'o', 'taraf', 'yazmak', '.']
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


## Credits

This package is a Python port of part of the [Zemberek](https://github.com/ahmetaa/zemberek-nlp) package by [Ahmet A. Akın](https://github.com/ahmetaa)
and Mehmet D. Akın. Its dictionaries and disambiguation model come from Zemberek, which is under the Apache License 2.0.
See [LICENSE-zemberek](LICENSE-zemberek).


This package was created with
[Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage)
project template.

