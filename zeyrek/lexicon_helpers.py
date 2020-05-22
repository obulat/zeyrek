import re
from pathlib import Path

from zeyrek import tr
from zeyrek.attributes import PrimaryPos, SecondaryPos, PosInfo, primary_pos_set, secondary_pos_set

RESOURCES_DIR = Path(__file__).parent / 'resources'


def load_dict(path):
    result = {}
    with open(path, 'r', encoding='utf8') as inf:
        for line in inf:
            if line.strip().startswith('##') or len(line.strip()) == 0:
                continue
            k, v = [_.strip() for _ in line.split('=')]
            result[k] = v
    return result


tr_letter_pron = load_dict(RESOURCES_DIR / "tr" / "phonetics" / "turkish-letter-names.txt")
en_letter_pron = load_dict(Path(RESOURCES_DIR / "tr" / "phonetics" / "turkish-letter-names.txt"))
en_phones_to_tr = load_dict(Path(RESOURCES_DIR / "tr" / "phonetics" / "english-phones-to-turkish.txt"))


def to_turkish_letter_pronunciation(word):
    if bool(re.search(r'\d', word)):
        return to_turkish_letter_pronunciation_with_digit(word)
    result = []
    for i in range(len(word)):
        c = word[i].lower()
        if c == '-':
            continue
        if c in tr_letter_pron:
            if i == len(word) - 1 and c == 'k':
                result.append("ka")
            else:
                result.append(tr_letter_pron[c])
        else:
            print(f"Cannot guess pronunciation of letter {c} in : {word}")
    return ''.join(result)


def to_turkish_letter_pronunciation_with_digit(word):
    pieces = re.split(r'(\d+)', word)
    result = []
    i = 0
    for piece in pieces:
        if bool(re.search(r'\d', piece)):
            result.append(turkish_numbers_to_string(piece))
            i += 1
            continue
        if i < len(pieces) - 1:
            result.append(to_turkish_letter_pronunciation(piece))
        else:
            result.append(replace_english_specific_chars(piece))
        i += 1

    return ''.join(result)  # replace('[ ]+', '')


singleDigitNumbers = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
tenToNinety = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
thousands = ["", "bin", "milyon", "milyar", "trilyon", "katrilyon"]


def convert_three_digit(threeDigitNumber):
    """
    converts a given three digit number.
    :param threeDigitNumber: a three digit number to convert to words.
    :return: turkish string representation of the input number.
    """
    result = ''

    hundreds = threeDigitNumber // 100
    tens = threeDigitNumber // 10
    single_digit = threeDigitNumber % 10

    if hundreds != 0:
        result = "yüz"

    if hundreds > 1:
        result = singleDigitNumbers[hundreds] + " " + result

    result = result + " " + tenToNinety[tens] + " " + singleDigitNumbers[single_digit]
    return result.strip()


def convert_to_string(number):
    """
    returns the Turkish representation of the input. if negative "eksi" string is prepended.
    @param input: input. must be between (including both) -999999999999999999L to
       * 999999999999999999L
       * @return Turkish representation of the input. if negative "eksi" string is prepended.
       * @throws IllegalArgumentException if input value is too low or high.
    """
    MIN_NUMBER = -999999999999999999
    MAX_NUMBER = 999999999999999999
    if number == 0:
        return "sıfır"
    if number < MIN_NUMBER or number > MAX_NUMBER:
        raise ValueError(f"Number is out of bounds: {number}")
    result = ""
    current_pos = abs(number)
    counter = 0
    while current_pos >= 1:
        group_of_three = int(current_pos % 1000)
        if group_of_three != 0:
            if group_of_three == 1 and counter == 1:
                result = thousands[counter] + " " + result
            else:
                result = convert_three_digit(group_of_three) + " " + thousands[counter] + " " + result
        counter += 1
        current_pos /= 1000

    if number < 0:
        return "eksi " + result.strip()
    else:
        return result.strip()


def turkish_numbers_to_string(word):
    """Methods converts a String containing an integer to a Strings."""
    if word.startswith("+"):
        word = word[1:]
    result = []
    i = 0
    for c in word:
        if c == '0':
            result.append("sıfır")
            i += 0
        else:
            break
    rest = word[i:]
    if len(rest) > 0:
        result.append(convert_to_string(int(rest)))  # TODO: probably error, was blank
    # result.append(int(rest))
    return ' '.join(result)


def replace_english_specific_chars(word):
    replacement = {'w': 'v',
                   'q': 'k',
                   'x': 'ks',
                   '-': '',
                   "\\": ''}
    return ''.join([replacement.get(sym, sym) for sym in word])


def guess_for_abbreviation(word):
    """Tries to guess turkish abbreviation pronunciation."""
    syllables = tr.vowel_count(word)

    first_two_cons = False
    if len(word) > 2:
        if tr.contains_vowel(word[:2]):
            first_two_cons = True
    if syllables == 0 or len(word) < 3 or first_two_cons:
        return to_turkish_letter_pronunciation(word)
    else:
        return replace_english_specific_chars(word)


#  A function that parses raw word and metadata information. Represents a single line in dictionary.
def parse_line_data(line):
    from .lexicon import MetaDataId
    word = line.split(" ")[0]
    metadata = {}
    if len(word) == 0:
        raise ValueError(f"Line {line} has no word data")
    meta = line[len(word):].strip()
    if len(meta) == 0:
        return {'word': word, 'metadata': metadata}
    if not meta.startswith('[') or not meta.endswith(']'):
        raise ValueError(f"Malformed metadata, missing brackets. Should be: [metadata]. Line: {line}")
    meta = meta[1:-1]
    for chunk in meta.split(';'):
        if ':' not in chunk:
            raise ValueError(f"Line {line} has malformed metadata chunk {chunk}. It should have a ':' symbol.")
        token_id_str, chunk_data = [_.strip() for _ in chunk.split(':')]
        if len(chunk_data) == 0:
            raise ValueError(f"Line {line} has malformed metadata chunk {chunk} with no chunk data available")
        data_id = MetaDataId(token_id_str)
        metadata[data_id] = chunk_data

    return {'word': word, 'metadata': metadata}


def generate_dict_id(lemma: str, primary_pos: PrimaryPos, secondary_pos: SecondaryPos, index: int):
    result = f"{lemma}_{primary_pos.name}"
    if secondary_pos is not None and secondary_pos != SecondaryPos.NONE:
        result = f"{result}_{secondary_pos.name}"
    if index > 0:
        result = f"{result}_{index}"
    return result


def is_verb(word):
    return len(word) > 3 and (word.endswith('mek') or word.endswith('mak')) and tr.is_lower(word[0])


def infer_primary_pos(word):
    return PrimaryPos.Verb if is_verb(word) else PrimaryPos.Noun


def infer_secondary_pos(word):
    if tr.is_upper(word[0]):
        return SecondaryPos.ProperNoun
    else:
        return SecondaryPos.NONE


def generate_root(word, pos_info):
    if pos_info.primary_pos == PrimaryPos.Punctuation:
        return word
    #  Strip -mek -mak from verbs.
    if pos_info.primary_pos == PrimaryPos.Verb and is_verb(word):
        word = word[:-3]

    #  TODO: not sure if we should remove diacritics or convert to lowercase.
    #  Lowercase and normalize diacritics.
    word = tr.normalize_circumflex(tr.lower(word))
    # Remove dashes
    word = word.replace("-", "")
    word = word.replace("'", "")

    return word


def get_pos_data(pos_str, word):
    if pos_str is None:
        # infer the type
        return PosInfo(infer_primary_pos(word),
                       infer_secondary_pos(word)
                       )
    else:
        primary_pos = None
        secondary_pos = None
        tokens = [_.strip() for _ in pos_str.split(',')]
        if len(tokens) > 2:
            raise ValueError(f"Only two POS tokens are allowed in data chunk: {pos_str}")
        for token in tokens:
            if token not in primary_pos_set and token not in secondary_pos_set:
                raise ValueError(f"Unrecognized pos data [{token}] in data chunk: {pos_str}")

        #  Ques POS causes some trouble here. Because it is defined in both primary and secondary pos.
        for token in tokens:
            if token in primary_pos_set:
                if primary_pos is None:
                    primary_pos = PrimaryPos(token)
                    continue
                else:
                    if pos_str == "Pron,Ques":
                        primary_pos = PrimaryPos("Pron")
                        secondary_pos = SecondaryPos("Ques")
                    else:
                        raise ValueError(f"Multiple primary pos in data chunk: {pos_str}")
            elif token in secondary_pos_set:
                if secondary_pos is None:
                    secondary_pos = SecondaryPos(token)  # TODO: Test this works
                    continue
                else:
                    raise ValueError(f"Multiple secondary pos in data chunk: {pos_str}")

        # If there are no primary or secondary pos defined, try to infer them.
        if primary_pos is None:
            primary_pos = infer_primary_pos(word)

        if secondary_pos is None:
            secondary_pos = infer_secondary_pos(word)

        return PosInfo(primary_pos, secondary_pos)
