from enum import Enum
from pathlib import Path
from typing import List, Set

from zeyrek.attributes import RootAttribute, PrimaryPos, SecondaryPos, parse_attr_data, infer_morphemic_attributes
from zeyrek import tr
from zeyrek.lexicon_helpers import to_turkish_letter_pronunciation, guess_for_abbreviation, \
    parse_line_data, generate_dict_id, generate_root, get_pos_data


class MetaDataId(Enum):
    POS = "P"
    ATTRIBUTES = "A"
    REF_ID = "Ref"
    ROOTS = "Roots"
    PRONUNCIATION = "Pr"
    SUFFIX = "S"
    INDEX = "Index"


class TextLexiconProcessor:
    """
    Class that processes dictionary lines and returns RootLexicon.
    Main method is ``process_lines``.
    """

    def __init__(self):
        self.lexicon = RootLexicon()
        self.late_entries = []

    def process_lines(self, lines: List) -> 'RootLexicon':
        late_entries = []
        for line in lines:
            line = line.strip()
            if len(line) > 0 and not line.startswith("##"):
                line = line.strip()
                line_data = parse_line_data(line)

                # if a line contains references to other lines, we add them to lexicon later.
                if MetaDataId.REF_ID not in line_data['metadata'] and MetaDataId.ROOTS not in line_data['metadata']:
                    dict_item = self._parse_dict_item(line_data)
                    if dict_item is not None:
                        self.lexicon.add(dict_item)
                    else:
                        print(f"Dict item is none: {line_data}")
                else:
                    late_entries.append(line_data)
        self._process_late_entries()
        return self.lexicon

    def _parse_dict_item(self, line_data):
        word = line_data['word']
        metadata = line_data['metadata']
        pos_info = get_pos_data(metadata.get(MetaDataId.POS), word)
        clean_word = generate_root(word, pos_info)
        index_str = metadata.get(MetaDataId.INDEX)
        index = 0 if index_str is None else int(index_str)
        pronunciation = metadata.get(MetaDataId.PRONUNCIATION)
        pronunciation_guessed = False
        secondary_pos = pos_info.secondary_pos
        if pronunciation is None:
            pronunciation_guessed = True
            if pos_info.primary_pos == PrimaryPos.Punctuation:
                pronunciation = "a"
            elif secondary_pos == SecondaryPos.Abbreviation:
                pronunciation = guess_for_abbreviation(clean_word)
            elif tr.contains_vowel(clean_word):
                pronunciation = clean_word
            else:
                pronunciation = to_turkish_letter_pronunciation(clean_word)
        else:
            pronunciation = tr.lower(pronunciation)

        attr_data = metadata.get(MetaDataId.ATTRIBUTES)
        parsed_attributes = parse_attr_data(attr_data) if attr_data is not None else None
        attributes = infer_morphemic_attributes(pronunciation, pos_info, parsed_attributes)
        if pronunciation_guessed and (secondary_pos in [SecondaryPos.ProperNoun, SecondaryPos.Abbreviation]):
            attributes.add(RootAttribute.PronunciationGuessed)
            # here if there is an item with same lemma and pos values but attributes are different,
            # we increment the index.
        while True:
            id_ = generate_dict_id(word, pos_info.primary_pos, secondary_pos, index)
            existing_item = self.lexicon.id_dict.get(id_)

            if existing_item is not None and id_ == existing_item.id_:
                if attributes & existing_item.attributes == attributes:
                    print(f"Item already defined: {existing_item}")
                else:
                    index += 1
            else:
                break
        try:
            return DictionaryItem(lemma=word, root=clean_word,
                                  primary_pos=pos_info.primary_pos,
                                  secondary_pos=secondary_pos,
                                  attrs=attributes,
                                  pronunciation=pronunciation,
                                  index=index)
        except Exception as e:
            print(f"Could not create {word}/{index}/ {type(index)} dictionary item, error: {e} ")

    def _process_late_entries(self):
        for entry in self.late_entries:
            if MetaDataId.REF_ID in entry['metadata']:
                reference_id = entry['metadata'].get(MetaDataId.REF_ID)
                if '_' not in reference_id:
                    reference_id = f"{reference_id}_Noun"

                ref_item = self.lexicon.id_dict.get(reference_id)
                if ref_item is None:
                    print("Cannot find reference item id " + reference_id)
                item = self._parse_dict_item(entry)
                item.ref_item = ref_item
                self.lexicon.add(item)
            # this is a compound lemma with P3sg in it. Such as atkuyruğu
            if MetaDataId.ROOTS in entry['metadata']:
                pos_data_str = entry['metadata'].get(MetaDataId.POS)
                pos_info = get_pos_data(pos_data_str, entry['word'])
                generated_id = f"{entry['word']}_{pos_info.primary_pos.value}"
                item = self.lexicon.id_dict.get(generated_id)
                if item is None:
                    item = self._parse_dict_item(entry)
                    self.lexicon.add(item)
                r = entry['metadata'].get(MetaDataId.ROOTS)  # at-kuyruk
                root = r.replace("-", "")  # atkuyruk
                if "-" in r:
                    r = r[r.index('-') + 1:]
                ref_items = self.lexicon.get_matching_items(r)  # check lexicon for [kuyruk]
                if len(ref_items) > 0:
                    ref_item = sorted(ref_items, key=lambda ref_item: ref_item.index)[0]
                    attr_set = ref_item.attributes.copy()
                else:
                    attr_set = infer_morphemic_attributes(root, pos_info, set())
                attr_set.add(RootAttribute.CompoundP3sgRoot)
                if RootAttribute.Ext in item.attributes:
                    attr_set.add(RootAttribute.Ext)
                index = 0
                dict_item_id = f"{root}_{item.primary_pos.value}"
                if self.lexicon.id_dict.get(dict_item_id) is not None:
                    index = 1
                    # generate a fake lemma for atkuyruk, use kuyruk's attributes.
                    # But do not allow voicing.
                fake_root = DictionaryItem(root, root, item.primary_pos, item.secondary_pos, attr_set, root, index)
                fake_root.attributes.add(RootAttribute.Dummy)
                if RootAttribute.Voicing in fake_root.attributes:
                    fake_root.attributes.remove(RootAttribute.Voicing)
                fake_root.reference_item = item
                self.lexicon.add(fake_root)


class DictionaryItem:
    """
    This is a class for dictionary items in Lexicon.
    :param lemma: The exact surface form of the item used in dictionary.
    :type lemma: str
    :param root: Form which will be used during graph generation. Such as,
        dictionary Item [gelmek Verb]'s root is "gel"
    :type root: str
    :param primary_pos: Primary POS information
    :type primary_pos: PrimaryPos
    :param secondary_pos: Secondary POS information
    :type secondary_pos: SecondaryPos
    :param attrs: Attributes that this item carries. Such as voicing or vowel drop.
    :type attrs: RootAttribute
    :param pronunciation: Pronunciations of the item. TODO: This should be
    converted to an actual 'Pronunciation' item
    :type pronunciation: str

    :param index:
    :type: int
    """

    def __init__(self, lemma: str,
                 root: str,
                 primary_pos: PrimaryPos,
                 secondary_pos: SecondaryPos,
                 attrs: Set,
                 pronunciation: str,
                 index: int):
        """
        :id_(str)is the unique ID of the item. It is generated from Pos and lemma.
        If there are multiple items with same POS and Lemma user needs to add an index for
        distinction. Structure of the ID: lemma_POS or lemma_POS_index
        """
        self.pronunciation = pronunciation
        self.lemma = lemma
        self.primary_pos = primary_pos
        self.secondary_pos = secondary_pos
        # normalized_lemma: if this is a Verb, removes -mek -mak suffix.Otherwise returns the `lemma`
        self.normalized_lemma = self.lemma[:-3] if self.primary_pos == PrimaryPos.Verb else self.lemma
        self.attributes = attrs
        self.root = root
        self.index = index
        self.id_ = self.generate_id()
        self.ref_item = None

    def __str__(self):
        return f"{self.lemma} [P:{self.primary_pos.value}]"

    def __repr__(self):
        return f"DictionaryItem({self.id_})"

    def has_any_attribute(self, root_attrs):

        return bool(set(root_attrs) & self.attributes)

    def has_attribute(self, attr):
        return attr in self.attributes

    def generate_id(self):
        result = [self.lemma, self.primary_pos.value]  # shortForm is value
        if self.secondary_pos is not None and self.secondary_pos != SecondaryPos.NONE:
            result.append(self.secondary_pos.value)
        if self.index > 0:
            result.append(str(self.index))
        return '_'.join(result)

    def __hash__(self):
        return hash((self.id_, self.lemma, self.index))

    def __eq__(self, other):
        return self.id_ == other.id_ and self.lemma == other.lemma and self.index == other.index


class RootLexicon:
    RESOURCES_DIR = Path(__file__).parent / 'resources'
    DEFAULT_DICTIONARY_RESOURCES = [
        "tr/master-dictionary.dict",
        "tr/non-tdk.dict",
        "tr/proper.dict",
        "tr/proper-from-corpus.dict",
        "tr/abbreviations.dict",
        "tr/person-names.dict"
    ]

    def __init__(self):
        self.item_set = set()
        self.id_dict = {}
        self.item_dict = {}

    def add_lexicon(self, additional_lexicon):
        for dict_item in additional_lexicon.items:
            self.add(dict_item)

    def add_dictionary_from_path(self, path_to_dictionary: str) -> 'RootLexicon':
        # TODO: Add error checking
        dictionary_lines = Path(path_to_dictionary).read_text(encoding='utf8').split('\n')
        processor = TextLexiconProcessor()
        lexicon_from_path = processor.process_lines(dictionary_lines)
        self.add_lexicon(lexicon_from_path)
        return lexicon_from_path

    @classmethod
    def default_text_dictionaries(cls):
        lines = []
        for resource in cls.DEFAULT_DICTIONARY_RESOURCES:
            dict_path = cls.RESOURCES_DIR / resource
            new_lines = Path(dict_path).read_text(encoding='utf8').split('\n')
            lines.extend(new_lines)
        processor = TextLexiconProcessor()
        return processor.process_lines(lines)

    @classmethod
    def from_lines(cls, lines: List):
        processor = TextLexiconProcessor()
        return processor.process_lines(lines)

    def add(self, item):
        if item.id_ in self.id_dict:
            print(f"Duplicated item id_ of {item}: {item.id_} with {self.id_dict.get(item.id_)}")
            return
        self.item_set.add(item)
        self.id_dict[item.id_] = item
        if item.lemma in self.item_dict:
            self.item_dict[item.lemma].append(item)
        else:
            self.item_dict[item.lemma] = [item]

    def get_matching_items(self, lemma):
        items = self.item_dict.get(lemma)
        return [] if items is None else items

    def get_item_by_id(self, id_):
        return self.id_dict.get(id_, None)

    def remove(self, item):
        self.item_dict.get(item.lemma)  # TODO: test if works
        self.id_dict.pop(item.id_)
        self.item_set.remove(item)

    def __len__(self):
        return len(self.item_dict)

    @property
    def items(self):
        return list(self.item_set)
