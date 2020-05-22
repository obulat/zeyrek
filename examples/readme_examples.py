from zeyrek import MorphAnalyzer
lemmatizer = MorphAnalyzer()
lemmas = lemmatizer.lemmatize('beyazlaştıracak')
print(lemmas[0])

lemmatization = lemmatizer.lemmatize_text("Yarın doktora gideceğimizi öğrendi.")
for sentence, lemmas in lemmatization:
    print(sentence)
    for word, lemma in lemmas:
        print(f"{word}: {lemma}")

word_analysis = lemmatizer.analyze('beyazlaştıracak')
for variant in word_analysis:
    print(variant)

analysis = lemmatizer.analyze("Yarın doktora gideceğimizi öğrendi.")
for sentence, result in analysis:
    for word_parse in result:
        print(f"\n{word_parse[0].word}")
        for parse in word_parse:
            print(parse.formatted)
