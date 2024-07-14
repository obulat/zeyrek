# Zeyrek: Morphological Analyzer and Lemmatizer

![PyPI - Version](https://img.shields.io/pypi/v/zeyrek)

Zeyrek is a partial port of the [Zemberek library](https://github.com/ahmetaa/zemberek-nlp) to Python for lemmatizing
and analyzing Turkish language words. It is in alpha stage, and the API
will probably change.


* Free software: MIT license
* Documentation: https://zeyrek.readthedocs.io.


## Basic Usage

To use Zeyrek, first create an instance of `MorphAnalyzer` class:

```shell
import zeyrek
analyzer = zeyrek.MorphAnalyzer()
```

Then, you can call its `analyze` method on words or texts to get all possible analyses::

```shell
print(analyzer.analyze('benim'))
Parse(word='benim', lemma='ben', pos='Noun', morphemes=['Noun', 'A3sg', 'P1sg'], formatted='[ben:Noun] ben:Noun+A3sg+im:P1sg')
Parse(word='benim', lemma='ben', pos='Pron', morphemes=['Pron', 'A1sg', 'Gen'], formatted='[ben:Pron,Pers] ben:Pron+A1sg+im:Gen')
Parse(word='benim', lemma='ben', pos='Verb', morphemes=['Noun', 'A3sg', 'Zero', 'Verb', 'Pres', 'A1sg'], formatted='[ben:Noun] ben:Noun+A3sg|Zero→Verb+Pres+im:A1sg')
Parse(word='benim', lemma='ben', pos='Verb', morphemes=['Pron', 'A1sg', 'Zero', 'Verb', 'Pres', 'A1sg'], formatted='[ben:Pron,Pers] ben:Pron+A1sg|Zero→Verb+Pres+im:A1sg')
```
If you only need the base form of words, or lemmas, you can call `lemmatize`. It returns a list
of tuples, with word itself and a list of possible lemmas::

```shell
print(analyzer.lemmatize('benim'))
[('benim', ['ben'])]
```


## Credits

This package is a Python port of part of the [Zemberek](https://github.com/ahmetaa/zemberek-nlp) package by [Ahmet A. Akın](https://github.com/ahmetaa)


This package was created with
[Cookiecutter](https://github.com/audreyr/cookiecutter) and the
[audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage)
project template.

