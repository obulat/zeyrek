from zeyrek import MorphAnalyzer
import nltk
nltk.download('punkt')


def run_examples():
    analyzer = MorphAnalyzer()

    with open('text.txt', encoding='utf-8') as text_file:
        text = text_file.read()

    # Analyze text from the file and print out formatted parses of each word.
    result = analyzer.analyze(text)
    for word_result in result:
        print(word_result[0].word)
        for parse in word_result:
            print(parse.formatted)
        print()


if __name__ == '__main__':
    run_examples()
