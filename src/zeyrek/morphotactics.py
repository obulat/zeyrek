from typing import ClassVar, NamedTuple

# sys.path.pop(0)
# print(sys.path)
# print(os.path.dirname(__file__))
from zeyrek import tr
from zeyrek.attributes import (
    PhoneticAttribute,
    PrimaryPos,
    RootAttribute,
    SecondaryPos,
    _cached_phonetic_attributes,
    calculate_phonetic_attributes,
)
from zeyrek.conditions import (
    Condition,
    ContainsMorpheme,
    ContainsMorphemeSequence,
    CurrentGroupContainsAny,
    DictionaryItemIs,
    DictionaryItemIsAny,
    HasAnySuffixSurface,
    HasPhoneticAttribute,
    HasRootAttribute,
    HasTail,
    HasTailSequence,
    LastDerivationIs,
    LastDerivationIsAny,
    NoSurfaceAfterDerivation,
    NotCondition,
    PreviousGroupContains,
    PreviousGroupContainsMorpheme,
    PreviousMorphemeIs,
    PreviousMorphemeIsAny,
    PreviousStateIs,
    PreviousStateIsAny,
    PreviousStateIsNot,
    RootSurfaceIs,
    RootSurfaceIsAny,
    SecondaryPosIs,
    has,
    not_have,
)
from zeyrek.lexicon import DictionaryItem, RootLexicon


class Morpheme(NamedTuple):
    name: str
    id_: str
    pos: "PrimaryPos | None"
    derivational: bool = False
    informal: bool = False

    def __eq__(self, other):
        return self.id_ == other.id_


class MorphemeState:
    def __init__(
        self,
        id_: str,
        morpheme: Morpheme,
        terminal=False,
        derivative=False,
        pos_root=False,
    ):
        self.id_ = id_
        self.morpheme = morpheme
        self.terminal = terminal
        self.derivative = derivative
        self.pos_root = pos_root
        self.outgoing: list[MorphemeTransition] = []
        self.incoming: list[SuffixTransition] = []

    def __str__(self):
        return f"[{self.id_}:{self.morpheme.id_}]"

    def __repr__(self):
        return f"MorphemeState({self.id_}, {self.morpheme.id_})"

    def add_outgoing(
        self, *suffix_transitions: "SuffixTransition | list[SuffixTransition]"
    ):
        for transition in suffix_transitions:
            if transition in self.outgoing:
                # Outgoing transition {transition} already exists in {self}")
                continue

            self.outgoing.append(transition)
        return self

    def add_incoming(self, suffix_transitions: list["SuffixTransition"]):
        for transition in suffix_transitions:
            if transition in self.incoming:
                print(f"Incoming transition {transition} already exists in {self}")
                continue
            self.incoming.append(transition)
        return self

    def add(
        self, to_: "MorphemeState", template: str, condition: "Condition | None" = None
    ):
        transition = SuffixTransition(self, to_, template, condition)
        self.add_outgoing(transition)
        return self

    def add_all(
        self,
        transitions: list[
            "tuple[MorphemeState, str, Condition] | tuple[MorphemeState, str]"
        ],
    ):
        for transition in transitions:
            self.add(*transition)

    def add_empty(self, to_, condition=None):
        transition = SuffixTransition(self, to_, "", condition)
        self.add_outgoing(transition)
        return self

    def copy_outgoing_transitions_from(self, state: "MorphemeState"):
        for transition in state.outgoing:
            if not isinstance(transition, SuffixTransition):
                continue
            copy = transition.get_copy()
            copy.from_ = self
            self.add_outgoing(transition)

    def remove_transitions_to(self, morpheme: Morpheme):
        transitions = [
            transition
            for transition in self.outgoing
            if transition.to_.morpheme == morpheme
        ]

        for transition in transitions:
            self.outgoing.remove(transition)


morphemes: dict[str, Morpheme] = {}


def add_morpheme(*data):
    morpheme = Morpheme(*data)
    morphemes[morpheme.id_] = morpheme
    return morpheme


root = add_morpheme("Root", "Root", None, False, False)

noun = add_morpheme("Noun", "Noun", PrimaryPos.Noun, False, False)
adj = add_morpheme("Adjective", "Adj", PrimaryPos.Adjective, False, False)
verb = add_morpheme("Verb", "Verb", PrimaryPos.Verb, False, False)
pron = add_morpheme("Pronoun", "Pron", PrimaryPos.Pronoun, False, False)
adv = add_morpheme("Adverb", "Adv", PrimaryPos.Adverb, False, False)
conj = add_morpheme("Conjunction", "Conj", PrimaryPos.Conjunction, False, False)
punc = add_morpheme("Punctuation", "Punc", PrimaryPos.Punctuation, False, False)
ques = add_morpheme("Question", "Ques", PrimaryPos.Question, False, False)
postp = add_morpheme("PostPositive", "Postp", PrimaryPos.PostPositive, False, False)
det = add_morpheme("Determiner", "Det", PrimaryPos.Determiner, False, False)
num = add_morpheme("Numeral", "Num", PrimaryPos.Numeral, False, False)
dup = add_morpheme("Duplicator", "Dup", PrimaryPos.Duplicator, False, False)
interj = add_morpheme("Interjection", "Interj", PrimaryPos.Interjection, False, False)

# Number-Person agreement.

a1sg = add_morpheme("FirstPersonSingular", "A1sg", None, False, False)
a2sg = add_morpheme("SecondPersonSingular", "A2sg", None, False, False)
a3sg = add_morpheme("ThirdPersonSingular", "A3sg", None, False, False)
a1pl = add_morpheme("FirstPersonPlural", "A1pl", None, False, False)
a2pl = add_morpheme("SecondPersonPlural", "A2pl", None, False, False)
a3pl = add_morpheme("ThirdPersonPlural", "A3pl", None, False, False)

# Possessive

# No possession suffix. This is not a real Morpheme but adds information to analysis. "elma = apple"
pnon = add_morpheme("NoPosession", "Pnon", None, False, False)

# First person singular possession suffix.  "elma-m = my apple"
p1sg = add_morpheme("FirstPersonSingularPossessive", "P1sg", None, False, False)

p2sg = add_morpheme("SecondPersonSingularPossessive", "P2sg", None, False, False)

# Third person singular possession suffix. "elma-sı = his/her apple"
p3sg = add_morpheme("ThirdPersonSingularPossessive", "P3sg", None, False, False)

# First person plural possession suffix.
p1pl = add_morpheme("FirstPersonPluralPossessive", "P1pl", None, False, False)

p2pl = add_morpheme("SecondPersonPluralPossessive", "P2pl", None, False, False)

p3pl = add_morpheme("ThirdPersonPluralPossessive", "P3pl", None, False, False)

# Case suffixes

# elma
nom = add_morpheme("Nominal", "Nom", None, False, False)
# elmaya
dat = add_morpheme("Dative", "Dat", None, False, False)
# elmayı
acc = add_morpheme("Accusative", "Acc", None, False, False)
# elmadan
abl = add_morpheme("Ablative", "Abl", None, False, False)
# elmada
loc = add_morpheme("Locative", "Loc", None, False, False)
# elmayla
ins = add_morpheme("Instrumental", "Ins", None, False, False)
# elmanın
gen = add_morpheme("Genitive", "Gen", None, False, False)
# elmaca
equ = add_morpheme("Equ", "Equ", None, False, False)

# Derivation suffixes

# elmacık (Noun)
dim = add_morpheme("Diminutive", "Dim", None, True, False)
# elmalık (Noun) TODO: Find better name.
ness = add_morpheme("Ness", "Ness", None, True, False)
# elmalı (Adj)
with_ = add_morpheme("With", "With", None, True, False)
# elmasız (Adj)
without = add_morpheme("Without", "Without", None, True, False)
# elmasal (Adj)
related = add_morpheme("Related", "Related", None, True, False)
# tahtamsı (Adj)
justLike = add_morpheme("JustLike", "JustLike", None, True, False)
# tahtadaki (Adj)
rel = add_morpheme("Relation", "Rel", None, True, False)
# elmacı (Noun)
agt = add_morpheme("Agentive", "Agt", None, True, False)
# tahtalaş (Verb)
become = add_morpheme("Become", "Become", None, True, False)
# tahtalan (Verb)
acquire = add_morpheme("Acquire", "Acquire", None, True, False)

# yeşilce (Adj->Adv)
ly = add_morpheme("Ly", "Ly", None, True, False)
# oku-t oku-t-tur (Verb)
caus = add_morpheme("Causative", "Caus", None, True, False)
# konuş-uş (Verb)
recip = add_morpheme("Reciprocal", "Recip", None, True, False)
# kaşınmak (Verb) For now Reflexive suffixes are only implicit. Meaning that
# dictionary contains "kaşınmak" with Reflexive attribute.
reflex = add_morpheme("Reflexive", "Reflex", None, True, False)
# oku-yabil (Verb)
able = add_morpheme("Ability", "Able", None, True, False)
# oku-n, oku-nul (Verb)
pass_ = add_morpheme("Passive", "Pass", None, True, False)
# okumak (Noun)
inf1 = add_morpheme("Infinitive1", "Inf1", None, True, False)
# okuma (Noun)
inf2 = add_morpheme("Infinitive2", "Inf2", None, True, False)
# okuyuş (Noun)
inf3 = add_morpheme("Infinitive3", "Inf3", None, True, False)
# okumaca (Noun)
actOf = add_morpheme("ActOf", "ActOf", None, True, False)
# okuduğum kitap (Adj, Noun)
pastPart = add_morpheme("PastParticiple", "PastPart", None, True, False)
# okumuşlarımız (Adj, Noun)
narrPart = add_morpheme("NarrativeParticiple", "NarrPart", None, True, False)
# okuyacağım kitap (Adj, Noun)
futPart = add_morpheme("FutureParticiple", "FutPart", None, True, False)
# okuyan (Adj, Noun)
presPart = add_morpheme("PresentParticiple", "PresPart", None, True, False)
# okurluk (Noun)
aorPart = add_morpheme("AoristParticiple", "AorPart", None, True, False)
# okumazlık - okumamazlık (Noun)
notState = add_morpheme("NotState", "NotState", None, True, False)
# okuyan (Adj, Noun)
feelLike = add_morpheme("FeelLike", "FeelLike", None, True, False)
# okuyagel (Verb)
everSince = add_morpheme("EverSince", "EverSince", None, True, False)
# okuyadur, okuyagör (Verb)
repeat = add_morpheme("Repeat", "Repeat", None, True, False)
# okuyayaz (Verb)
almost = add_morpheme("Almost", "Almost", None, True, False)
# okuyuver (Verb)
hastily = add_morpheme("Hastily", "Hastily", None, True, False)
# okuyakal (Verb)
stay = add_morpheme("Stay", "Stay", None, True, False)
# okuyakoy (Verb)
start = add_morpheme("Start", "Start", None, True, False)
# okurcasına (Adv,Adj)
asIf = add_morpheme("AsIf", "AsIf", None, True, False)
# okurken (Adv)
while_ = add_morpheme("While", "While", None, True, False)
# okuyunca (Adv)
when = add_morpheme("When", "When", None, True, False)
# okuyalı (Adv)
sinceDoingSo = add_morpheme("SinceDoingSo", "SinceDoingSo", None, True, False)
# okudukça (Adv)
asLongAs = add_morpheme("AsLongAs", "AsLongAs", None, True, False)
# okuyarak (Adv)
byDoingSo = add_morpheme("ByDoingSo", "ByDoingSo", None, True, False)
# okuyasıya (Adv)
adamantly = add_morpheme("Adamantly", "Adamantly", None, True, False)
# okuyup (Adv)
afterDoingSo = add_morpheme("AfterDoingSo", "AfterDoingSo", None, True, False)
# okumadan, okumaksızın (Adv)

withoutHavingDoneSo = add_morpheme(
    "WithoutHavingDoneSo", "WithoutHavingDoneSo", None, True, False
)
# okuyamadan (Adv)

withoutBeingAbleToHaveDoneSo = add_morpheme(
    "WithoutBeingAbleToHaveDoneSo", "WithoutBeingAbleToHaveDoneSo", None, True, False
)

# Zero derivation
zero = add_morpheme("Zero", "Zero", None, True, False)

# Verb specific
cop = add_morpheme("Copula", "Cop", None, False, False)

# Negative Verb
neg = add_morpheme("Negative", "Neg", None, False, False)
# Unable (Negative - Ability such as "okuyamıyorum - I cannot read, I am unable to read.")
unable = add_morpheme("Unable", "Unable", None, False, False)

# Tense
pres = add_morpheme("PresentTense", "Pres", None, False, False)
past = add_morpheme("PastTense", "Past", None, False, False)
narr = add_morpheme("NarrativeTense", "Narr", None, False, False)
cond = add_morpheme("Condition", "Cond", None, False, False)
# oku-yor
prog1 = add_morpheme("Progressive1", "Prog1", None, False, False)
# oku-makta
prog2 = add_morpheme("Progressive2", "Prog2", None, False, False)
# oku-r
aor = add_morpheme("Aorist", "Aor", None, False, False)
# oku-yacak
fut = add_morpheme("Future", "Fut", None, False, False)

# gel, gel-sin
imp = add_morpheme("Imparative", "Imp", None, False, False)
# oku-ya
opt = add_morpheme("Optative", "Opt", None, False, False)
# oku-sa
desr = add_morpheme("Desire", "Desr", None, False, False)
# oku-malı
neces = add_morpheme("Necessity", "Neces", None, False, False)

# -------------- States ----------------------------
# _ST = Terminal state _S = Non Terminal State.
# A terminal state means that a walk in the graph can end there.

# The root of the graph. Stem transitions start here and nothing connects to it,
# so all analyzers can share it.
root_S = MorphemeState("root_S", root, False, False, False)


class StemTransitionsMapBased:
    """
    Generates StemTransition objects from the dictionary item.
    Most of the time a single StemNode is generated.
    """

    modifiers: ClassVar[set[RootAttribute]] = {
        RootAttribute.Doubling,
        RootAttribute.LastVowelDrop,
        RootAttribute.ProgressiveVowelDrop,
        RootAttribute.InverseHarmony,
        RootAttribute.Voicing,
        RootAttribute.CompoundP3sg,
        RootAttribute.CompoundP3sgRoot,
    }
    special_roots: ClassVar[set[str]] = {
        "içeri_Noun",
        "içeri_Adj",
        "dışarı_Adj",
        "şura_Noun",
        "bura_Noun",
        "ora_Noun",
        "dışarı_Noun",
        "dışarı_Postp",
        "yukarı_Noun",
        "yukarı_Adj",
        "ileri_Noun",
        "ben_Pron_Pers",
        "sen_Pron_Pers",
        "demek_Verb",
        "yemek_Verb",
        "imek_Verb",
        "birbiri_Pron_Quant",
        "çoğu_Pron_Quant",
        "öbürü_Pron_Quant",
        "birçoğu_Pron_Quant",
    }

    def __init__(self, morphotactics: "TurkishMorphotactics"):
        self.lexicon: RootLexicon = morphotactics.lexicon
        self.morphotactics = morphotactics
        self.multi_stems: dict[str, list[StemTransition]] = {}
        self.single_stems: dict[str, StemTransition] = {}
        self.different_stem_items: dict[DictionaryItem, list[StemTransition]] = {}
        self.add_lexicon_items(self.lexicon.items)

    def add_lexicon_items(self, items: list[DictionaryItem]):
        for dict_item in items:
            if dict_item is None:
                print(dict_item)
            else:
                self.add_dict_item(dict_item)

    def generate_transitions(self, dict_item: DictionaryItem) -> list["StemTransition"]:

        def has_modifier_attribute(item: DictionaryItem):
            return any(
                attr in StemTransitionsMapBased.modifiers for attr in item.attributes
            )

        if dict_item.id_ in StemTransitionsMapBased.special_roots:
            return self.handle_special_roots(dict_item)
        if has_modifier_attribute(dict_item):
            return self.generate_modified_root_nodes(dict_item)
        else:
            transition = StemTransition(
                dict_item, self.morphotactics.get_root_state(dict_item)
            )
        return [transition]

    def generate_modified_root_nodes(
        self, dict_item: DictionaryItem
    ) -> list["StemTransition"]:
        result = list(dict_item.pronunciation)
        original_attrs = calculate_phonetic_attributes(dict_item.pronunciation)
        modified_attrs = original_attrs.copy()
        modified_root_state_value: MorphemeState | None = None
        unmodified_root_state = None
        for attr in sorted(dict_item.attributes, key=lambda attribute: attribute.value):
            if attr == RootAttribute.Voicing:
                last = dict_item.pronunciation[-1]
                voiced = tr.voice(last)
                if last == voiced:
                    raise ValueError(
                        f"Voicing letter is not proper in {dict_item}: {last} - {voiced}"
                    )
                if dict_item.lemma.endswith("nk"):
                    voiced = "g"
                result[-1] = voiced
                if PhoneticAttribute.LastLetterVoicelessStop in modified_attrs:
                    modified_attrs.discard(PhoneticAttribute.LastLetterVoicelessStop)
                original_attrs.add(PhoneticAttribute.ExpectsConsonant)
                modified_attrs.add(PhoneticAttribute.ExpectsVowel)
                modified_attrs.add(PhoneticAttribute.CannotTerminate)
            elif attr == RootAttribute.Doubling:
                result.append(result[-1])
                original_attrs.add(PhoneticAttribute.ExpectsConsonant)
                modified_attrs.add(PhoneticAttribute.ExpectsVowel)
                modified_attrs.add(PhoneticAttribute.CannotTerminate)
            elif attr == RootAttribute.LastVowelDrop:
                last_letter = result[-1]
                if tr.is_vowel(last_letter):
                    result.pop()
                    modified_attrs.add(PhoneticAttribute.ExpectsConsonant)
                    modified_attrs.add(PhoneticAttribute.CannotTerminate)
                else:
                    result.pop(-2)
                    if dict_item.primary_pos != PrimaryPos.Verb:
                        original_attrs.add(PhoneticAttribute.ExpectsConsonant)
                    else:
                        unmodified_root_state = (
                            self.morphotactics.verbLastVowelDropUnmodRoot_S
                        )
                        modified_root_state_value = (
                            self.morphotactics.verbLastVowelDropModRoot_S
                        )
                modified_attrs.add(PhoneticAttribute.ExpectsVowel)
                modified_attrs.add(PhoneticAttribute.CannotTerminate)
            elif attr == RootAttribute.InverseHarmony:
                original_attrs.add(PhoneticAttribute.LastVowelFrontal)
                if PhoneticAttribute.LastVowelBack in original_attrs:
                    original_attrs.discard(PhoneticAttribute.LastVowelBack)
                modified_attrs.add(PhoneticAttribute.LastVowelFrontal)
                if PhoneticAttribute.LastVowelBack in modified_attrs:
                    modified_attrs.discard(PhoneticAttribute.LastVowelBack)
            elif attr == RootAttribute.ProgressiveVowelDrop:
                if len(result) > 1:
                    result.pop()
                    if tr.contains_vowel("".join(result)):
                        modified_attrs = calculate_phonetic_attributes("".join(result))
                    modified_attrs.add(PhoneticAttribute.LastLetterDropped)
            else:
                continue
        if unmodified_root_state is None:
            unmodified_root_state = self.morphotactics.get_root_state(
                dict_item, original_attrs
            )
        original = StemTransition(dict_item, unmodified_root_state, original_attrs)
        modified_root_state: MorphemeState = (
            modified_root_state_value
            or self.morphotactics.get_root_state(dict_item, modified_attrs)
        )
        modified = StemTransition(
            dict_item, modified_root_state, modified_attrs, surface="".join(result)
        )

        if original == modified:
            return [original]
        else:
            return [original, modified]

    def handle_special_roots(self, dict_item: DictionaryItem) -> list["StemTransition"]:
        special_item_dict = {
            "birbiri_Pron_Quant": "birbir",
            "çoğu_Pron_Quant": "çok",
            "öbürü_Pron_Quant": "öbürü",
            "birçoğu_Pron_Quant": "birçok",
        }
        item_id = dict_item.id_
        original_attrs = calculate_phonetic_attributes(dict_item.pronunciation)
        unmodified_root_state = self.morphotactics.get_root_state(
            dict_item, original_attrs
        )

        if item_id in [
            "içeri_Noun",
            "içeri_Adj",
            "dışarı_Adj",
            "dışarı_Noun",
            "dışarı_Postp",
            "yukarı_Noun",
            "ileri_Noun",
            "yukarı_Adj",
            "şura_Noun",
            "bura_Noun",
            "ora_Noun",
        ]:
            original = StemTransition(dict_item, unmodified_root_state, original_attrs)
            # TODO: check postpositive case. Maybe it is not required.
            root_for_modified = {
                PrimaryPos.Noun: self.morphotactics.nounLastVowelDropRoot_S,
                PrimaryPos.Adjective: self.morphotactics.adjLastVowelDropRoot_S,
                PrimaryPos.PostPositive: self.morphotactics.adjLastVowelDropRoot_S,
            }.get(dict_item.primary_pos)
            if root_for_modified is None:
                raise ValueError(f"No root morpheme state found for {dict_item}")

            m = dict_item.root[:-1]
            modified = StemTransition(
                dict_item,
                root_for_modified,
                calculate_phonetic_attributes(m),
                surface=m,
            )
            modified.attrs.add(PhoneticAttribute.ExpectsConsonant)
            modified.attrs.add(PhoneticAttribute.CannotTerminate)
            return [original, modified]
        elif item_id in ["ben_Pron_Pers", "sen_Pron_Pers"]:
            original = StemTransition(dict_item, unmodified_root_state, original_attrs)
            if dict_item.lemma == "ben":
                modified = StemTransition(
                    dict_item,
                    self.morphotactics.pronPers_Mod_S,
                    calculate_phonetic_attributes("ban"),
                    surface="ban",
                )
            else:
                modified = StemTransition(
                    dict_item,
                    self.morphotactics.pronPers_Mod_S,
                    calculate_phonetic_attributes("san"),
                    surface="san",
                )
            original.attrs.add(PhoneticAttribute.UnModifiedPronoun)
            modified.attrs.add(PhoneticAttribute.ModifiedPronoun)
            return [original, modified]
        elif item_id in ["demek_Verb", "yemek_Verb"]:
            original = StemTransition(
                dict_item, self.morphotactics.vDeYeRoot_S, original_attrs
            )
            if dict_item.lemma == "demek":
                modified = StemTransition(
                    dict_item,
                    self.morphotactics.vDeYeRoot_S,
                    calculate_phonetic_attributes("di"),
                    surface="di",
                )
            else:
                modified = StemTransition(
                    dict_item,
                    self.morphotactics.vDeYeRoot_S,
                    calculate_phonetic_attributes("yi"),
                    surface="yi",
                )
            return [original, modified]
        elif item_id == "imek_Verb":
            original = StemTransition(
                dict_item, self.morphotactics.imekRoot_S, original_attrs
            )
            return [original]
        elif item_id in special_item_dict:
            original = StemTransition(
                dict_item, self.morphotactics.pronQuant_S, original_attrs
            )
            modified_root = special_item_dict[item_id]
            modified = StemTransition(
                dict_item,
                self.morphotactics.pronQuantModified_S,
                calculate_phonetic_attributes(modified_root),
                surface=modified_root,
            )
            original.attrs.add(PhoneticAttribute.UnModifiedPronoun)
            modified.attrs.add(PhoneticAttribute.ModifiedPronoun)
            return [original, modified]
        else:
            raise ValueError(
                f"Lexicon Item with special stem change cannot be handled: {dict_item}"
            )

    def add_stem_transition(self, stem_transition: "StemTransition"):
        surface_form = stem_transition.surface
        if surface_form in self.multi_stems:
            self.multi_stems[surface_form].append(stem_transition)
        elif surface_form in self.single_stems:
            existing_form = self.single_stems.get(surface_form)
            self.multi_stems[surface_form] = [existing_form, stem_transition]
            self.single_stems.pop(surface_form)
        else:
            self.single_stems[surface_form] = stem_transition

    def remove_stem_node(self, stem_transition: "StemTransition"):
        surface_form = stem_transition.surface
        if surface_form in self.multi_stems:
            self.multi_stems["surface_form"].remove(stem_transition)
        elif (
            surface_form in self.single_stems
            and self.single_stems["surface_form"].dict_item == stem_transition.dict_item
        ):
            self.single_stems.pop(surface_form)

        # if (!differentStemItems.containsEntry(stemTransition.item, stemTransition)) {
        #   differentStemItems.remove(stemTransition.item, stemTransition)

    def transitions_from_stem(self, stem: str) -> list["StemTransition"]:
        if stem in self.single_stems:
            return [self.single_stems.get(stem)]
        elif stem in self.multi_stems:
            return self.multi_stems.get(stem)
        else:
            return []

    def prefix_matches(self, prefix: str) -> list["StemTransition"]:
        matches = []
        current_string = ""
        for letter in prefix:
            current_string += letter
            matches.extend(self.transitions_from_stem(current_string))
        return matches

    def transitions_from_item(
        self, dict_item: DictionaryItem
    ) -> list["StemTransition"]:
        if dict_item in self.different_stem_items:
            return self.different_stem_items.get(dict_item)
        transitions = self.transitions_from_stem(dict_item.root)
        return [
            transition
            for transition in transitions
            if transition.dict_item == dict_item
        ]

    def add_dict_item(self, dict_item: DictionaryItem):
        transitions = self.generate_transitions(dict_item)
        if transitions is None:
            print(f"Transitions are none for {dict_item}")
        for transition in transitions:
            self.add_stem_transition(transition)
        if len(transitions) > 1 or (
            len(transitions) == 1 and dict_item.root != transitions[0].surface
        ):
            self.different_stem_items[dict_item] = transitions

    def remove_dict_item(self, dict_item: DictionaryItem):
        transitions = self.generate_transitions(dict_item)
        for transition in transitions:
            self.remove_stem_node(transition)
        if dict_item in self.different_stem_items:
            self.different_stem_items.pop(dict_item)


class TurkishMorphotactics:
    def __init__(self, lexicon: RootLexicon):
        self.lexicon = lexicon
        self.make_states()
        self.make_graph()
        self.item_root_states = {
            "değil_Verb": self.nVerbDegil_S,
            "imek_Verb": self.imekRoot_S,
            "su_Noun": self.nounSuRoot_S,
            "akarsu_Noun": self.nounSuRoot_S,
            "öyle_Adv": self.advForVerbDeriv_ST,
            "böyle_Adv": self.advForVerbDeriv_ST,
            "şöyle_Adv": self.advForVerbDeriv_ST,
        }
        self.stem_transitions = StemTransitionsMapBased(self)

    def make_states(self):
        """
        Creates the states of the graph. Each analyzer has its own states, so the
        transitions that one analyzer adds don't change the others.
        """
        self.puncRoot_ST = MorphemeState("puncRoot_ST", punc, True, False, True)

        # -------------- Noun States ------------------------

        self.noun_S = MorphemeState("noun_S", noun, False, False, True)
        self.nounCompoundRoot_S = MorphemeState(
            "nounCompoundRoot_S", noun, False, False, True
        )
        self.nounSuRoot_S = MorphemeState("nounSuRoot_S", noun, False, False, True)
        self.nounInf1Root_S = MorphemeState("nounInf1Root_S", noun, False, False, True)
        self.nounActOfRoot_S = MorphemeState(
            "nounActOfRoot_S", noun, False, False, True
        )

        # Number-Person agreement

        self.a3sg_S = MorphemeState("a3sg_S", a3sg, False, False, False)
        self.a3sgSu_S = MorphemeState("a3sgSu_S", a3sg, False, False, False)
        self.a3sgCompound_S = MorphemeState("a3sgCompound_S", a3sg, False, False, False)
        self.a3sgInf1_S = MorphemeState("a3sgInf1_S", a3sg, False, False, False)
        self.a3sgActOf_S = MorphemeState("a3sgActOf_S", a3sg, False, False, False)
        self.a3pl_S = MorphemeState("a3pl_S", a3pl, False, False, False)
        self.a3plActOf_S = MorphemeState("a3plActOf_S", a3pl, False, False, False)
        self.a3plCompound_S = MorphemeState("a3plCompound_S", a3pl, False, False, False)
        self.a3plCompound2_S = MorphemeState(
            "a3plCompound2_S", a3pl, False, False, False
        )

        # Possessive

        self.pnon_S = MorphemeState("pnon_S", pnon, False, False, False)
        self.pnonCompound_S = MorphemeState("pnonCompound_S", pnon, False, False, False)
        self.pnonCompound2_S = MorphemeState(
            "pnonCompound2_S", pnon, False, False, False
        )
        self.pnonInf1_S = MorphemeState("pnonInf1_S", pnon, False, False, False)
        self.pnonActOf = MorphemeState("pnonActOf", pnon, False, False, False)
        self.p1sg_S = MorphemeState("p1sg_S", p1sg, False, False, False)
        self.p2sg_S = MorphemeState("p2sg_S", p2sg, False, False, False)
        self.p3sg_S = MorphemeState("p3sg_S", p3sg, False, False, False)
        self.p1pl_S = MorphemeState("p1pl_S", p1pl, False, False, False)
        self.p2pl_S = MorphemeState("p2pl_S", p2pl, False, False, False)
        self.p3pl_S = MorphemeState("p3pl_S", p3pl, False, False, False)

        # Case

        self.nom_ST = MorphemeState("nom_ST", nom, True, False, False)
        self.nom_S = MorphemeState("nom_S", nom, False, False, False)

        self.dat_ST = MorphemeState("dat_ST", dat, True, False, False)
        self.abl_ST = MorphemeState("abl_ST", abl, True, False, False)
        self.loc_ST = MorphemeState("loc_ST", loc, True, False, False)
        self.ins_ST = MorphemeState("ins_ST", ins, True, False, False)
        self.acc_ST = MorphemeState("acc_ST", acc, True, False, False)
        self.gen_ST = MorphemeState("gen_ST", gen, True, False, False)
        self.equ_ST = MorphemeState("equ_ST", equ, True, False, False)

        # Derivation

        self.dim_S = MorphemeState("dim_S", dim, False, True, False)
        self.ness_S = MorphemeState("ness_S", ness, False, True, False)
        self.agt_S = MorphemeState("agt_S", agt, False, True, False)
        self.related_S = MorphemeState("related_S", related, False, True, False)
        self.rel_S = MorphemeState("rel_S", rel, False, True, False)
        self.relToPron_S = MorphemeState("relToPron_S", rel, False, True, False)
        self.with_S = MorphemeState("with_S", with_, False, True, False)
        self.without_S = MorphemeState("without_S", without, False, True, False)
        self.justLike_S = MorphemeState("justLike_S", justLike, False, True, False)
        self.nounZeroDeriv_S = MorphemeState(
            "nounZeroDeriv_S", zero, False, True, False
        )
        self.become_S = MorphemeState("become_S", become, False, True, False)
        self.acquire_S = MorphemeState("acquire_S", acquire, False, True, False)

        # -------- Morphotactics for modified forms of words like "içeri->içerde"
        self.nounLastVowelDropRoot_S = MorphemeState(
            "nounLastVowelDropRoot_S", noun, False, False, True
        )
        self.adjLastVowelDropRoot_S = MorphemeState(
            "adjLastVowelDropRoot_S", adj, False, False, True
        )
        self.postpLastVowelDropRoot_S = MorphemeState(
            "postpLastVowelDropRoot_S", postp, False, False, True
        )
        self.a3PlLastVowelDrop_S = MorphemeState(
            "a3PlLastVowelDrop_S", a3pl, False, False, False
        )
        self.a3sgLastVowelDrop_S = MorphemeState(
            "a3sgLastVowelDrop_S", a3sg, False, False, False
        )
        self.pNonLastVowelDrop_S = MorphemeState(
            "pNonLastVowelDrop_S", pnon, False, False, False
        )
        self.zeroLastVowelDrop_S = MorphemeState(
            "zeroLastVowelDrop_S", zero, False, True, False
        )

        self.nounProper_S = MorphemeState("nounProper_S", noun, False, False, True)
        self.nounAbbrv_S = MorphemeState("nounAbbrv_S", noun, False, False, True)
        # this will be used for proper noun separation.
        self.puncProperSeparator_S = MorphemeState(
            "puncProperSeparator_S", punc, False, False, False
        )

        self.nounNoSuffix_S = MorphemeState("nounNoSuffix_S", noun, False, False, True)
        self.nounA3sgNoSuffix_S = MorphemeState(
            "nounA3sgNoSuffix_S", a3sg, False, False, False
        )
        self.nounPnonNoSuffix_S = MorphemeState(
            "nounPnonNoSuffix_S", pnon, False, False, False
        )
        self.nounNomNoSuffix_ST = MorphemeState(
            "nounNomNoSuffix_S", nom, True, False, False
        )

        # -------------- Adjective States ------------------------

        self.adjectiveRoot_ST = MorphemeState(
            "adjectiveRoot_ST", adj, True, False, True
        )
        self.adjAfterVerb_S = MorphemeState("adjAfterVerb_S", adj, False, False, True)
        self.adjAfterVerb_ST = MorphemeState("adjAfterVerb_ST", adj, True, False, True)

        self.adjZeroDeriv_S = MorphemeState("adjZeroDeriv_S", zero, False, True, False)

        # After verb->adj derivations Adj can get possesive suffixes.
        # Such as "oku-duğ-um", "okuyacağı"
        self.aPnon_ST = MorphemeState("aPnon_ST", pnon, True, False, False)
        self.aP1sg_ST = MorphemeState("aP1sg_ST", p1sg, True, False, False)
        self.aP2sg_ST = MorphemeState("aP2sg_ST", p2sg, True, False, False)
        self.aP3sg_ST = MorphemeState("aP3sg_ST", p3sg, True, False, False)
        self.aP1pl_ST = MorphemeState("aP3sg_ST", p1pl, True, False, False)
        self.aP2pl_ST = MorphemeState("aP2pl_ST", p2pl, True, False, False)
        self.aP3pl_ST = MorphemeState("aP3pl_ST", p3pl, True, False, False)

        self.aLy_S = MorphemeState("aLy_S", ly, False, True, False)
        self.aAsIf_S = MorphemeState("aAsIf_S", asIf, False, True, False)
        self.aAgt_S = MorphemeState("aAgt_S", agt, False, True, False)

        # --------------------- Numeral Root --------------------------------------------------
        self.numeralRoot_ST = MorphemeState("numeralRoot_ST", num, True, False, True)
        self.numZeroDeriv_S = MorphemeState("numZeroDeriv_S", zero, False, True, False)

        # -------------- Adjective-Noun connected Verb States ------------------------

        self.nVerb_S = MorphemeState("nVerb_S", verb, False, False, True)
        self.nVerbDegil_S = MorphemeState("nVerbDegil_S", verb, False, False, True)

        self.nPresent_S = MorphemeState("nPresent_S", pres, False, False, False)
        self.nPast_S = MorphemeState("nPast_S", past, False, False, False)
        self.nNarr_S = MorphemeState("nNarr_S", narr, False, False, False)
        self.nCond_S = MorphemeState("nCond_S", cond, False, False, False)
        self.nA1sg_ST = MorphemeState("nA1sg_ST", a1sg, True, False, False)
        self.nA2sg_ST = MorphemeState("nA2sg_ST", a2sg, True, False, False)
        self.nA1pl_ST = MorphemeState("nA1pl_ST", a1pl, True, False, False)
        self.nA2pl_ST = MorphemeState("nA2pl_ST", a2pl, True, False, False)
        self.nA3sg_ST = MorphemeState("nA3sg_ST", a3sg, True, False, False)
        self.nA3sg_S = MorphemeState("nA3sg_S", a3sg, False, False, False)
        self.nA3pl_ST = MorphemeState("nA3pl_ST", a3pl, True, False, False)

        self.nCop_ST = MorphemeState("nCop_ST", cop, True, False, False)
        self.nCopBeforeA3pl_S = MorphemeState(
            "nCopBeforeA3pl_S", cop, False, False, False
        )

        self.nNeg_S = MorphemeState("nNeg_S", neg, False, False, False)

        # ----------- Pronoun states --------------------------

        # Pronouns have states similar with Nouns.
        self.pronPers_S = MorphemeState("pronPers_S", pron, False, False, True)

        self.pronDemons_S = MorphemeState("pronDemons_S", pron, False, False, True)
        self.pronQuant_S = MorphemeState("pronQuant_S", pron, False, False, True)
        self.pronQuantModified_S = MorphemeState(
            "pronQuantModified_S", pron, False, False, True
        )
        self.pronQues_S = MorphemeState("pronQues_S", pron, False, False, True)
        self.pronReflex_S = MorphemeState("pronReflex_S", pron, False, False, True)

        # used for ben-sen modification
        self.pronPers_Mod_S = MorphemeState("pronPers_Mod_S", pron, False, False, True)
        # A root for noun->Rel->Pron derivation.
        self.pronAfterRel_S = MorphemeState("pronAfterRel_S", pron, False, False, True)

        self.pA1sg_S = MorphemeState("pA1sg_S", a1sg, False, False, False)
        self.pA2sg_S = MorphemeState("pA2sg_S", a2sg, False, False, False)

        self.pA1sgMod_S = MorphemeState(
            "pA1sgMod_S", a1sg, False, False, False
        )  # for modified ben
        self.pA2sgMod_S = MorphemeState(
            "pA2sgMod_S", a2sg, False, False, False
        )  # for modified sen

        self.pA3sg_S = MorphemeState("pA3sg_S", a3sg, False, False, False)
        self.pA3sgRel_S = MorphemeState("pA3sgRel_S", a3sg, False, False, False)
        self.pA1pl_S = MorphemeState("pA1pl_S", a1pl, False, False, False)
        self.pA2pl_S = MorphemeState("pA2pl_S", a2pl, False, False, False)

        self.pA3pl_S = MorphemeState("pA3pl_S", a3pl, False, False, False)
        self.pA3plRel_S = MorphemeState("pA3plRel_S", a3pl, False, False, False)

        self.pQuantA3sg_S = MorphemeState("pQuantA3sg_S", a3sg, False, False, False)
        self.pQuantA3pl_S = MorphemeState("pQuantA3pl_S", a3pl, False, False, False)
        self.pQuantModA3pl_S = MorphemeState(
            "pQuantModA3pl_S", a3pl, False, False, False
        )  # for birbirleri etc.
        self.pQuantA1pl_S = MorphemeState("pQuantA1pl_S", a1pl, False, False, False)
        self.pQuantA2pl_S = MorphemeState("pQuantA2pl_S", a2pl, False, False, False)

        self.pQuesA3sg_S = MorphemeState("pQuesA3sg_S", a3sg, False, False, False)
        self.pQuesA3pl_S = MorphemeState("pQuesA3pl_S", a3pl, False, False, False)

        self.pReflexA3sg_S = MorphemeState("pReflexA3sg_S", a3sg, False, False, False)
        self.pReflexA3pl_S = MorphemeState("pReflexA3pl_S", a3pl, False, False, False)
        self.pReflexA1sg_S = MorphemeState("pReflexA1sg_S", a1sg, False, False, False)
        self.pReflexA2sg_S = MorphemeState("pReflexA2sg_S", a2sg, False, False, False)
        self.pReflexA1pl_S = MorphemeState("pReflexA1pl_S", a1pl, False, False, False)
        self.pReflexA2pl_S = MorphemeState("pReflexA2pl_S", a2pl, False, False, False)

        # Possessive

        self.pPnon_S = MorphemeState("pPnon_S", pnon, False, False, False)
        self.pPnonRel_S = MorphemeState("pPnonRel_S", pnon, False, False, False)
        self.pPnonMod_S = MorphemeState(
            "pPnonMod_S", pnon, False, False, False
        )  # for modified ben-sen
        self.pP1sg_S = MorphemeState("pP1sg_S", p1sg, False, False, False)  # kimim
        self.pP2sg_S = MorphemeState("pP2sg_S", p2sg, False, False, False)
        self.pP3sg_S = MorphemeState(
            "pP3sg_S", p3sg, False, False, False
        )  # for `birisi` etc
        self.pP1pl_S = MorphemeState(
            "pP1pl_S", p1pl, False, False, False
        )  # for `birbirimiz` etc
        self.pP2pl_S = MorphemeState(
            "pP2pl_S", p2pl, False, False, False
        )  # for `birbiriniz` etc
        self.pP3pl_S = MorphemeState(
            "pP3pl_S", p3pl, False, False, False
        )  # for `birileri` etc

        # Case

        self.pNom_ST = MorphemeState("pNom_ST", nom, True, False, False)
        self.pDat_ST = MorphemeState("pDat_ST", dat, True, False, False)
        self.pAcc_ST = MorphemeState("pAcc_ST", acc, True, False, False)
        self.pAbl_ST = MorphemeState("pAbl_ST", abl, True, False, False)
        self.pLoc_ST = MorphemeState("pLoc_ST", loc, True, False, False)
        self.pGen_ST = MorphemeState("pGen_ST", gen, True, False, False)
        self.pIns_ST = MorphemeState("pIns_ST", ins, True, False, False)
        self.pEqu_ST = MorphemeState("pEqu_ST", equ, True, False, False)

        self.pronZeroDeriv_S = MorphemeState(
            "pronZeroDeriv_S", zero, False, True, False
        )

        self.pvPresent_S = MorphemeState("pvPresent_S", pres, False, False, False)
        self.pvPast_S = MorphemeState("pvPast_S", past, False, False, False)
        self.pvNarr_S = MorphemeState("pvNarr_S", narr, False, False, False)
        self.pvCond_S = MorphemeState("pvCond_S", cond, False, False, False)
        self.pvA1sg_ST = MorphemeState("pvA1sg_ST", a1sg, True, False, False)
        self.pvA2sg_ST = MorphemeState("pvA2sg_ST", a2sg, True, False, False)
        self.pvA3sg_ST = MorphemeState("pvA3sg_ST", a3sg, True, False, False)
        self.pvA3sg_S = MorphemeState("pvA3sg_S", a3sg, False, False, False)
        self.pvA1pl_ST = MorphemeState("pvA1pl_ST", a1pl, True, False, False)
        self.pvA2pl_ST = MorphemeState("pvA2pl_ST", a2pl, True, False, False)
        self.pvA3pl_ST = MorphemeState("pvA3pl_ST", a3pl, True, False, False)

        self.pvCopBeforeA3pl_S = MorphemeState(
            "pvCopBeforeA3pl_S", cop, False, False, False
        )
        self.pvCop_ST = MorphemeState("pvCop_ST", cop, True, False, False)

        self.pvVerbRoot_S = MorphemeState("pvVerbRoot_S", verb, False, False, True)
        # ------------- Adverbs -----------------

        self.advRoot_ST = MorphemeState("advRoot_ST", adv, True, False, True)
        self.advNounRoot_ST = MorphemeState("advRoot_ST", adv, True, False, True)
        self.advForVerbDeriv_ST = MorphemeState(
            "advForVerbDeriv_ST", adv, True, False, True
        )

        self.avNounAfterAdvRoot_ST = MorphemeState(
            "advToNounRoot_ST", noun, False, False, True
        )
        self.avA3sg_S = MorphemeState("avA3sg_S", a3sg, False, False, False)
        self.avPnon_S = MorphemeState("avPnon_S", pnon, False, False, False)
        self.avDat_ST = MorphemeState("avDat_ST", dat, True, False, False)

        self.avZero_S = MorphemeState("avZero_S", zero, False, True, False)
        self.avZeroToVerb_S = MorphemeState("avZeroToVerb_S", zero, False, True, False)
        # ------------- Interjection, Conjunctions, Determiner and Duplicator  -----------------

        self.conjRoot_ST = MorphemeState("conjRoot_ST", conj, True, False, True)
        self.interjRoot_ST = MorphemeState("interjRoot_ST", interj, True, False, True)
        self.detRoot_ST = MorphemeState("detRoot_ST", det, True, False, True)
        self.dupRoot_ST = MorphemeState("dupRoot_ST", dup, True, False, True)

        # ------------- Post Positive ------------------------------------------------

        self.postpRoot_ST = MorphemeState("postpRoot_ST", postp, True, False, True)
        self.postpZero_S = MorphemeState("postpZero_S", zero, False, True, False)

        self.po2nRoot_S = MorphemeState("po2nRoot_S", noun, False, False, False)

        self.po2nA3sg_S = MorphemeState("po2nA3sg_S", a3sg, False, False, False)
        self.po2nA3pl_S = MorphemeState("po2nA3pl_S", a3pl, False, False, False)

        self.po2nP3sg_S = MorphemeState("po2nP3sg_S", p3sg, False, False, False)
        self.po2nP1sg_S = MorphemeState("po2nP1sg_S", p1sg, False, False, False)
        self.po2nP2sg_S = MorphemeState("po2nP2sg_S", p2sg, False, False, False)
        self.po2nP1pl_S = MorphemeState("po2nP1pl_S", p1pl, False, False, False)
        self.po2nP2pl_S = MorphemeState("po2nP2pl_S", p2pl, False, False, False)
        self.po2nPnon_S = MorphemeState("po2nPnon_S", pnon, False, False, False)

        self.po2nNom_ST = MorphemeState("po2nNom_ST", nom, True, False, False)
        self.po2nDat_ST = MorphemeState("po2nDat_ST", dat, True, False, False)
        self.po2nAbl_ST = MorphemeState("po2nAbl_ST", abl, True, False, False)
        self.po2nLoc_ST = MorphemeState("po2nLoc_ST", loc, True, False, False)
        self.po2nIns_ST = MorphemeState("po2nIns_ST", ins, True, False, False)
        self.po2nAcc_ST = MorphemeState("po2nAcc_ST", acc, True, False, False)
        self.po2nGen_ST = MorphemeState("po2nGen_ST", gen, True, False, False)
        self.po2nEqu_ST = MorphemeState("po2nEqu_ST", equ, True, False, False)

        # ------------- Verbs -----------------------------------

        self.verbRoot_S = MorphemeState("verbRoot_S", verb, False, False, True)
        self.verbLastVowelDropModRoot_S = MorphemeState(
            "verbLastVowelDropModRoot_S", verb, False, False, True
        )
        self.verbLastVowelDropUnmodRoot_S = MorphemeState(
            "verbLastVowelDropUnmodRoot_S", verb, False, False, True
        )

        self.vA1sg_ST = MorphemeState("vA1sg_ST", a1sg, True, False, False)
        self.vA2sg_ST = MorphemeState("vA2sg_ST", a2sg, True, False, False)
        self.vA3sg_ST = MorphemeState("vA3sg_ST", a3sg, True, False, False)
        self.vA1pl_ST = MorphemeState("vA1pl_ST", a1pl, True, False, False)
        self.vA2pl_ST = MorphemeState("vA2pl_ST", a2pl, True, False, False)
        self.vA3pl_ST = MorphemeState("vA3pl_ST", a3pl, True, False, False)

        self.vPast_S = MorphemeState("vPast_S", past, False, False, False)
        self.vNarr_S = MorphemeState("vNarr_S", narr, False, False, False)
        self.vCond_S = MorphemeState("vCond_S", cond, False, False, False)
        self.vCondAfterPerson_ST = MorphemeState(
            "vCondAfterPerson_ST", cond, True, False, False
        )
        self.vPastAfterTense_S = MorphemeState(
            "vPastAfterTense_S", past, False, False, False
        )
        self.vNarrAfterTense_S = MorphemeState(
            "vNarrAfterTense_S", narr, False, False, False
        )

        # terminal cases are used if A3pl comes before NarrAfterTense, PastAfterTense or vCond
        self.vPastAfterTense_ST = MorphemeState(
            "vPastAfterTense_ST", past, True, False, False
        )
        self.vNarrAfterTense_ST = MorphemeState(
            "vNarrAfterTense_ST", narr, True, False, False
        )
        self.vCond_ST = MorphemeState("vCond_ST", cond, True, False, False)

        self.vProgYor_S = MorphemeState("vProgYor_S", prog1, False, False, False)
        self.vProgMakta_S = MorphemeState("vProgMakta_S", prog2, False, False, False)
        self.vFut_S = MorphemeState("vFut_S", fut, False, False, False)

        self.vCop_ST = MorphemeState("vCop_ST", cop, True, False, False)
        self.vCopBeforeA3pl_S = MorphemeState(
            "vCopBeforeA3pl_S", cop, False, False, False
        )

        self.vNeg_S = MorphemeState("vNeg_S", neg, False, False, False)
        self.vUnable_S = MorphemeState("vUnable_S", unable, False, False, False)
        # for negative before progressive-1 "Iyor"
        self.vNegProg1_S = MorphemeState("vNegProg1_S", neg, False, False, False)
        self.vUnableProg1_S = MorphemeState(
            "vUnableProg1_S", unable, False, False, False
        )

        self.vImp_S = MorphemeState("vImp_S", imp, False, False, False)
        self.vImpYemekYi_S = MorphemeState("vImpYemekYi_S", imp, False, False, False)
        self.vImpYemekYe_S = MorphemeState("vImpYemekYe_S", imp, False, False, False)

        self.vCausT_S = MorphemeState("vCaus_S", caus, False, True, False)
        self.vCausTir_S = MorphemeState("vCausTır_S", caus, False, True, False)

        self.vRecip_S = MorphemeState("vRecip_S", recip, False, True, False)
        self.vImplicitRecipRoot_S = MorphemeState(
            "vImplicitRecipRoot_S", verb, False, False, True
        )

        self.vReflex_S = MorphemeState("vReflex_S", reflex, False, True, False)
        self.vImplicitReflexRoot_S = MorphemeState(
            "vImplicitReflexRoot_S", verb, False, False, True
        )

        # for progressive vowel drop.
        self.verbRoot_VowelDrop_S = MorphemeState(
            "verbRoot_VowelDrop_S", verb, False, False, True
        )

        self.vAor_S = MorphemeState("vAor_S", aor, False, False, False)
        self.vAorNeg_S = MorphemeState("vAorNeg_S", aor, False, False, False)
        self.vAorNegEmpty_S = MorphemeState("vAorNegEmpty_S", aor, False, False, False)
        self.vAorPartNeg_S = MorphemeState("vAorPartNeg_S", aorPart, False, True, False)
        self.vAorPart_S = MorphemeState("vAorPart_S", aorPart, False, True, False)

        self.vAble_S = MorphemeState("vAble_S", able, False, True, False)
        self.vAbleNeg_S = MorphemeState("vAbleNeg_S", able, False, True, False)
        self.vAbleNegDerivRoot_S = MorphemeState(
            "vAbleNegDerivRoot_S", verb, False, False, True
        )

        self.vPass_S = MorphemeState("vPass_S", pass_, False, True, False)

        self.vOpt_S = MorphemeState("vOpt_S", opt, False, False, False)
        self.vDesr_S = MorphemeState("vDesr_S", desr, False, False, False)
        self.vNeces_S = MorphemeState("vNeces_S", neces, False, False, False)

        self.vInf1_S = MorphemeState("vInf1_S", inf1, False, True, False)
        self.vInf2_S = MorphemeState("vInf2_S", inf2, False, True, False)
        self.vInf3_S = MorphemeState("vInf3_S", inf3, False, True, False)

        self.vAgt_S = MorphemeState("vAgt_S", agt, False, True, False)
        self.vActOf_S = MorphemeState("vActOf_S", actOf, False, True, False)

        self.vPastPart_S = MorphemeState("vPastPart_S", pastPart, False, True, False)
        self.vFutPart_S = MorphemeState("vFutPart_S", futPart, False, True, False)
        self.vPresPart_S = MorphemeState("vPresPart_S", presPart, False, True, False)
        self.vNarrPart_S = MorphemeState("vNarrPart_S", narrPart, False, True, False)

        self.vFeelLike_S = MorphemeState("vFeelLike_S", feelLike, False, True, False)

        self.vNotState_S = MorphemeState("vNotState_S", notState, False, True, False)

        self.vEverSince_S = MorphemeState("vEverSince_S", everSince, False, True, False)
        self.vRepeat_S = MorphemeState("vRepeat_S", repeat, False, True, False)
        self.vAlmost_S = MorphemeState("vAlmost_S", almost, False, True, False)
        self.vHastily_S = MorphemeState("vHastily_S", hastily, False, True, False)
        self.vStay_S = MorphemeState("vStay_S", stay, False, True, False)
        self.vStart_S = MorphemeState("vStart_S", start, False, True, False)

        self.vWhile_S = MorphemeState("vWhile_S", while_, False, True, False)
        self.vWhen_S = MorphemeState("vWhen_S", when, False, True, False)
        self.vAsIf_S = MorphemeState("vAsIf_S", asIf, False, True, False)
        self.vSinceDoingSo_S = MorphemeState(
            "vSinceDoingSo_S", sinceDoingSo, False, True, False
        )
        self.vAsLongAs_S = MorphemeState("vAsLongAs_S", asLongAs, False, True, False)
        self.vByDoingSo_S = MorphemeState("vByDoingSo_S", byDoingSo, False, True, False)
        self.vAdamantly_S = MorphemeState("vAdamantly_S", adamantly, False, True, False)
        self.vAfterDoing_S = MorphemeState(
            "vAfterDoing_S", afterDoingSo, False, True, False
        )
        self.vWithoutHavingDoneSo_S = MorphemeState(
            "vWithoutHavingDoneSo_S", withoutHavingDoneSo, False, True, False
        )
        self.vWithoutBeingAbleToHaveDoneSo_S = MorphemeState(
            "vWithoutBeingAbleToHaveDoneSo_S",
            withoutBeingAbleToHaveDoneSo,
            False,
            True,
            False,
        )

        self.vDeYeRoot_S = MorphemeState("vDeYeRoot_S", verb, False, False, True)
        # -------- Question (mi) -----------------------------------------------

        self.qPresent_S = MorphemeState("qPresent_S", pres, False, False, False)
        self.qPast_S = MorphemeState("qPast_S", past, False, False, False)
        self.qNarr_S = MorphemeState("qNarr_S", narr, False, False, False)
        self.qA1sg_ST = MorphemeState("qA1sg_ST", a1sg, True, False, False)
        self.qA2sg_ST = MorphemeState("qA2sg_ST", a2sg, True, False, False)
        self.qA3sg_ST = MorphemeState("qA3sg_ST", a3sg, True, False, False)
        self.qA1pl_ST = MorphemeState("qA1pl_ST", a1pl, True, False, False)
        self.qA2pl_ST = MorphemeState("qA2pl_ST", a2pl, True, False, False)
        self.qA3pl_ST = MorphemeState("qA3pl_ST", a3pl, True, False, False)

        self.qCopBeforeA3pl_S = MorphemeState(
            "qCopBeforeA3pl_S", cop, False, False, False
        )
        self.qCop_ST = MorphemeState("qCop_ST", cop, True, False, False)

        self.questionRoot_S = MorphemeState("questionRoot_S", ques, False, False, True)
        # -------- Verb `imek` -----------------------------------------------

        self.imekRoot_S = MorphemeState("imekRoot_S", verb, False, False, True)

        self.imekPast_S = MorphemeState("imekPast_S", past, False, False, False)
        self.imekNarr_S = MorphemeState("imekNarr_S", narr, False, False, False)

        self.imekCond_S = MorphemeState("imekCond_S", cond, False, False, False)

        self.imekA1sg_ST = MorphemeState("imekA1sg_ST", a1sg, True, False, False)
        self.imekA2sg_ST = MorphemeState("imekA2sg_ST", a2sg, True, False, False)
        self.imekA3sg_ST = MorphemeState("imekA3sg_ST", a3sg, True, False, False)
        self.imekA1pl_ST = MorphemeState("imekA1pl_ST", a1pl, True, False, False)
        self.imekA2pl_ST = MorphemeState("imekA2pl_ST", a2pl, True, False, False)
        self.imekA3pl_ST = MorphemeState("imekA3pl_ST", a3pl, True, False, False)

        self.imekCop_ST = MorphemeState("qCop_ST", cop, True, False, False)

    def make_graph(self):
        self.connect_noun_states()
        self.connect_proper_nouns_and_abbreviations()
        self.connect_adjective_states()
        self.connect_numeral_states()
        self.connect_verb_after_noun_adj_states()
        self.connect_pronoun_states()
        self.connect_verb_after_pronoun()
        self.connect_verbs()
        self.connect_question()
        self.connect_adverbs()
        self.connect_last_vowel_drop_words()
        self.connect_postpositives()
        self.connect_imek()
        self.handle_post_processing_connections()

    def connect_noun_states(self):
        """
        Turkish Nouns always have Noun-Person-Possession-Case morphemes, even if there are no suffix
        characters. elma -> Noun:elma - A3sg:ε - Pnon:ε - Nom:ε (Third person singular: No possession,
        Nominal Case)
        """

        # ev-ε-?-?
        self.noun_S.add_empty(self.a3sg_S, not_have(RootAttribute.ImplicitPlural))

        # ev-ler-?-?.
        self.noun_S.add(
            self.a3pl_S,
            "lAr",
            not_have(RootAttribute.ImplicitPlural).and_(
                not_have(RootAttribute.CompoundP3sg)
            ),
        )

        # Allow only implicit plural `hayvanat`.
        self.noun_S.add_empty(self.a3pl_S, has(RootAttribute.ImplicitPlural))

        # --- Compound Handling ---------
        # for compound roots like "zeytinyağ-" generate two transitions
        # NounCompound--(ε)--> a3sgCompound --(ε)--> pNonCompound_S --> Nom_S
        self.nounCompoundRoot_S.add_empty(
            self.a3sgCompound_S, has(RootAttribute.CompoundP3sgRoot)
        )

        self.a3sgCompound_S.add_empty(self.pnonCompound_S)
        self.a3sgCompound_S.add(self.p3pl_S, "lArI")

        # ---- For compound derivations -----------------
        self.pnonCompound_S.add_empty(self.nom_S)
        self.nom_S.add(self.become_S, "lAş")
        self.nom_S.add(self.acquire_S, "lAn")
        # for "zeytinyağlı"
        self.nom_S.add(self.with_S, "lI", ContainsMorpheme(with_, without).not_())
        # for "zeytinyağsız"
        self.nom_S.add(self.without_S, "sIz", ContainsMorpheme(with_, without).not_())
        # for "zeytinyağlık"
        not_ = NotCondition
        containsNess = ContainsMorpheme(ness)
        self.nom_S.add(self.ness_S, "lI~k", not_(containsNess))
        self.nom_S.add(self.ness_S, "lI!ğ", not_(containsNess))
        # for "zeytinyağcı"
        self.nom_S.add(self.agt_S, ">cI", not_(ContainsMorpheme(agt)))
        # for "zeytinyağsı"
        self.nom_S.add(self.justLike_S, "+msI", not_(ContainsMorpheme(justLike)))
        # for "zeytinyağcık"
        self.nom_S.add(
            self.dim_S,
            ">cI~k",
            HasAnySuffixSurface().not_().and_not(ContainsMorpheme(dim)),
        )
        self.nom_S.add(
            self.dim_S,
            ">cI!ğ",
            HasAnySuffixSurface().not_().and_not(ContainsMorpheme(dim)),
        )
        # "zeytinyağcağız"
        self.nom_S.add(self.dim_S, "cAğIz", HasAnySuffixSurface().not_())

        # for compound roots like "zeytinyağ-lar-ı" generate two transition
        # NounCompound--(lAr)--> a3plCompound ---> self.p3sg_S, P1sg etc.
        self.nounCompoundRoot_S.add(
            self.a3plCompound_S, "lAr", has(RootAttribute.CompoundP3sgRoot)
        )

        # but for pnon connection, we use lArI
        self.nounCompoundRoot_S.add(
            self.a3plCompound2_S, "lArI", has(RootAttribute.CompoundP3sgRoot)
        )

        self.a3plCompound_S.add_all(
            [
                (self.p3sg_S, "I"),
                (self.p2sg_S, "In"),
                (self.p1sg_S, "Im"),
                (self.p1pl_S, "ImIz"),
                (self.p2pl_S, "InIz"),
                (self.p3pl_S, "I"),
            ]
        )

        # this path is used for plural analysis (A3pl+Pnon+Nom) of compound words.
        self.a3plCompound2_S.add_empty(self.pnonCompound2_S)
        self.pnonCompound2_S.add_empty(self.nom_ST)

        # ------

        # do not allow possessive suffixes for abbreviations or words like "annemler"

        abbreviation = SecondaryPosIs(SecondaryPos.Abbreviation)
        possessionCond = not_have(RootAttribute.FamilyMember).and_not(abbreviation)

        self.a3sg_S.add_all(
            [
                (self.pnon_S, "", not_have(RootAttribute.FamilyMember)),  # ev
                (self.p1sg_S, "Im", possessionCond),  # evim
                (
                    self.p2sg_S,
                    "In",
                    possessionCond.and_not(PreviousGroupContainsMorpheme(justLike)),
                ),  # evin
                (self.p3sg_S, "+sI", possessionCond),  # evi, odası
                (
                    self.p3sg_S,
                    "",
                    has(RootAttribute.CompoundP3sg),
                ),  # "zeytinyağı" has two analyses. Pnon and P3sg.
                (self.p1pl_S, "ImIz", possessionCond),  # evimiz
                (
                    self.p2pl_S,
                    "InIz",
                    possessionCond.and_not(PreviousGroupContainsMorpheme(justLike)),
                ),  # eviniz
                (self.p3pl_S, "lArI", possessionCond),
            ]
        )  # evleri

        # ev-ler-ε-?
        self.a3pl_S.add_empty(self.pnon_S, not_have(RootAttribute.FamilyMember))

        # ev-ler-im-?
        self.a3pl_S.add_all(
            [
                (self.p1sg_S, "Im", possessionCond),
                (self.p2sg_S, "In", possessionCond),
                (
                    self.p1sg_S,
                    "",
                    has(RootAttribute.ImplicitP1sg),
                ),  # for words like "annemler"
                (
                    self.p2sg_S,
                    "",
                    has(RootAttribute.ImplicitP2sg),
                ),  # for words like "annenler"
                (self.p3sg_S, "I", possessionCond),
                (self.p1pl_S, "ImIz", possessionCond),
                (self.p2pl_S, "InIz", possessionCond),
                (self.p3pl_S, "I", possessionCond),
            ]
        )

        # --- handle su - akarsu roots. ----
        self.nounSuRoot_S.add_empty(self.a3sgSu_S)
        self.nounSuRoot_S.add(self.a3pl_S, "lar")
        self.a3sgSu_S.add_all(
            [
                (self.pnon_S, ""),
                (self.p1sg_S, "yum"),
                (self.p2sg_S, "yun"),
                (self.p3sg_S, "yu"),
                (self.p1pl_S, "yumuz"),
                (self.p2pl_S, "yunuz"),
                (self.p3pl_S, "lArI"),
            ]
        )

        # ev-?-ε-ε (ev, evler).
        self.pnon_S.add_empty(self.nom_ST, not_have(RootAttribute.FamilyMember))

        equCond1 = (
            ContainsMorpheme(adj, futPart, presPart, narrPart, pastPart)
            .not_()
            .or_(ContainsMorphemeSequence(able, verb, pastPart))
        )

        equCond = PreviousMorphemeIs(a3pl).or_(equCond1)  # allow `yapabildiğince`

        # Not allow "zetinyağı-ya" etc.
        self.pnon_S.add_all(
            [
                (self.dat_ST, "+yA", not_have(RootAttribute.CompoundP3sg)),  # ev-e
                (self.abl_ST, ">dAn", not_have(RootAttribute.CompoundP3sg)),  # ev-den
                (self.loc_ST, ">dA", not_have(RootAttribute.CompoundP3sg)),  # evde
                (self.acc_ST, "+yI", not_have(RootAttribute.CompoundP3sg)),  # evi
                (
                    self.gen_ST,
                    "+nIn",
                    PreviousStateIsNot(self.a3sgSu_S),
                ),  # evin, zeytinyağının
                (self.gen_ST, "yIn", PreviousStateIs(self.a3sgSu_S)),  # suyun
                (
                    self.equ_ST,
                    ">cA",
                    not_have(RootAttribute.CompoundP3sg).and_(equCond),
                ),  # evce
                (self.ins_ST, "+ylA"),  # evle, zeytinyağıyla
            ]
        )
        self.pnon_S.add_all(
            [
                (
                    self.dat_ST,
                    "+nA",
                    HasRootAttribute(RootAttribute.CompoundP3sg),
                ),  # zeytinyağı-na
                (
                    self.abl_ST,
                    "+ndAn",
                    HasRootAttribute(RootAttribute.CompoundP3sg),
                ),  # zeytinyağı-ndan
                (
                    self.loc_ST,
                    "+ndA",
                    HasRootAttribute(RootAttribute.CompoundP3sg),
                ),  # zeytinyağı-nda
                (
                    self.equ_ST,
                    "+ncA",
                    HasRootAttribute(RootAttribute.CompoundP3sg).and_(equCond),
                ),  # zeytinyağı-nca
                (
                    self.acc_ST,
                    "+nI",
                    HasRootAttribute(RootAttribute.CompoundP3sg),
                ),  # zeytinyağı-nı
            ]
        )
        # This transition is for words like "içeri" or "dışarı".
        # Those words implicitly contains Dative suffix.
        # But It is also possible to add dative suffix +yA to those words such as "içeri-ye".
        self.pnon_S.add_empty(
            self.dat_ST, HasRootAttribute(RootAttribute.ImplicitDative)
        )

        self.p1sg_S.add_all(
            [
                (self.nom_ST, ""),  # evim
                (self.dat_ST, "A"),  # evime
                (self.loc_ST, "dA"),  # evimde
                (self.abl_ST, "dAn"),  # evimden
                (self.ins_ST, "lA"),  # evimle
                (self.gen_ST, "In"),  # evimin
                (self.equ_ST, "cA", equCond.or_(ContainsMorpheme(pastPart))),  # evimce
                (self.acc_ST, "I"),  # evimi
            ]
        )

        self.p2sg_S.add_all(
            [
                (self.nom_ST, ""),  # evin
                (self.dat_ST, "A"),  # evine
                (self.loc_ST, "dA"),  # evinde
                (self.abl_ST, "dAn"),  # evinden
                (self.ins_ST, "lA"),  # evinle
                (self.gen_ST, "In"),  # evinin
                (self.equ_ST, "cA", equCond.or_(ContainsMorpheme(pastPart))),  # evince
                (self.acc_ST, "I"),  # evini
            ]
        )

        self.p3sg_S.add_all(
            [
                (self.nom_ST, ""),  # evi
                (self.dat_ST, "nA"),  # evine
                (self.loc_ST, "ndA"),  # evinde
                (self.abl_ST, "ndAn"),  # evinden
                (self.ins_ST, "ylA"),  # eviyle
                (self.gen_ST, "nIn"),  # evinin
                (self.equ_ST, "ncA", equCond.or_(ContainsMorpheme(pastPart))),  # evince
                (self.acc_ST, "nI"),  # evini
            ]
        )

        self.p1pl_S.add_all(
            [
                (self.nom_ST, ""),  # evimiz
                (self.dat_ST, "A"),  # evimize
                (self.loc_ST, "dA"),  # evimizde
                (self.abl_ST, "dAn"),  # evimizden
                (self.ins_ST, "lA"),  # evimizden
                (self.gen_ST, "In"),  # evimizin
                (
                    self.equ_ST,
                    "cA",
                    equCond.or_(ContainsMorpheme(pastPart)),
                ),  # evimizce
                (self.acc_ST, "I"),  # evimizi
            ]
        )
        self.p2pl_S.add_all(
            [
                (self.nom_ST, ""),  # eviniz
                (self.dat_ST, "A"),  # evinize
                (self.loc_ST, "dA"),  # evinizde
                (self.abl_ST, "dAn"),  # evinizden
                (self.ins_ST, "lA"),  # evinizle
                (self.gen_ST, "In"),  # evinizin
                (
                    self.equ_ST,
                    "cA",
                    equCond.or_(ContainsMorpheme(pastPart)),
                ),  # evinizce
                (self.acc_ST, "I"),  # evinizi
            ]
        )

        self.p3pl_S.add_all(
            [
                (self.nom_ST, ""),  # evleri
                (self.dat_ST, "nA"),  # evlerine
                (self.loc_ST, "ndA"),  # evlerinde
                (self.abl_ST, "ndAn"),  # evlerinden
                (self.ins_ST, "ylA"),  # evleriyle
                (self.gen_ST, "nIn"),  # evlerinin
                # For now we omit equCond check because adj+..+A3pl+..+Equ fails.
                (self.equ_ST, "+ncA"),  # evlerince.
                (self.acc_ST, "nI"),  # evlerini
            ]
        )

        # ev-ε-ε-ε-cik (evcik). Disallow this path if visitor contains any non empty surface suffix.
        # There are two almost identical suffix transitions with templates ">cI~k" and ">cI!ğ"
        # This was necessary for some simplification during analysis. This way there will be only one
        # surface form generated for each transition.
        self.nom_ST.add(
            self.dim_S, ">cI~k", HasAnySuffixSurface().not_().and_not(abbreviation)
        )
        self.nom_ST.add(
            self.dim_S, ">cI!ğ", HasAnySuffixSurface().not_().and_not(abbreviation)
        )

        # ev-ε-ε-ε-ceğiz (evceğiz)
        self.nom_ST.add(
            self.dim_S, "cAğIz", HasAnySuffixSurface().not_().and_not(abbreviation)
        )

        # connect dim to the noun root.
        self.dim_S.add_empty(self.noun_S)

        emptyAdjNounSeq = ContainsMorphemeSequence(adj, zero, noun, a3sg, pnon, nom)

        self.nom_ST.add(
            self.ness_S,
            "lI~k",
            NoSurfaceAfterDerivation()
            .and_not(containsNess)
            .and_not(emptyAdjNounSeq)
            .and_not(abbreviation),
        )
        self.nom_ST.add(
            self.ness_S,
            "lI!ğ",
            NoSurfaceAfterDerivation()
            .and_not(containsNess)
            .and_not(emptyAdjNounSeq)
            .and_not(abbreviation),
        )

        # connect `ness` to the noun root.
        self.ness_S.add_empty(self.noun_S)

        self.nom_ST.add(
            self.agt_S,
            ">cI",
            NoSurfaceAfterDerivation().and_not(ContainsMorpheme(adj, agt)),
        )

        # connect `ness` to the noun root.
        self.agt_S.add_empty(self.noun_S)

        # here we do not allow an adjective to pass here.
        # such as, adj->zero->noun->ε-ε-ε->zero->Verb is not acceptable because there is already a
        # adj->zero->Verb path.

        noun2VerbZeroDerivationCondition = HasTail().and_not(
            NoSurfaceAfterDerivation().and_(LastDerivationIs(self.adjZeroDeriv_S))
        )
        self.nom_ST.add_empty(self.nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-ya-yım elma-ya-ydı
        self.dat_ST.add_empty(self.nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-dan-ım elma-dan-dı
        self.abl_ST.add_empty(self.nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-da-yım elma-da-ydı
        self.loc_ST.add_empty(self.nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-yla-yım elma-yla-ydı
        self.ins_ST.add_empty(self.nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-nın-ım elma-nın-dı
        self.gen_ST.add_empty(self.nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        self.nounZeroDeriv_S.add_empty(self.nVerb_S)

        # meyve-li

        noSurfaceAfterDerivation = NoSurfaceAfterDerivation()
        self.nom_ST.add(
            self.with_S,
            "lI",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(with_, without)),
        )

        self.nom_ST.add(
            self.without_S,
            "sIz",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(with_, without, inf1)),
        )

        self.nom_ST.add(
            self.justLike_S,
            "+msI",
            noSurfaceAfterDerivation.and_not(
                ContainsMorpheme(justLike, futPart, pastPart, presPart, adj)
            ),
        )

        # TODO: test order
        self.nom_ST.add(
            self.justLike_S,
            "ImsI",
            not_have(PhoneticAttribute.LastLetterVowel)
            .and_(noSurfaceAfterDerivation)
            .and_not(ContainsMorpheme(justLike, futPart, pastPart, presPart, adj)),
        )

        self.nom_ST.add(
            self.related_S,
            "sAl",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(with_, without, related)),
        )

        # connect With to Adjective root.
        self.with_S.add_empty(self.adjectiveRoot_ST)
        self.without_S.add_empty(self.adjectiveRoot_ST)
        self.related_S.add_empty(self.adjectiveRoot_ST)

        self.justLike_S.add_empty(self.adjectiveRoot_ST)

        # meyve-de-ki
        notRelRepetition = HasTailSequence(rel, adj, zero, noun, a3sg, pnon, loc).not_()
        self.loc_ST.add(self.rel_S, "ki", notRelRepetition)
        self.rel_S.add_empty(self.adjectiveRoot_ST)

        # for covering dünkü, anki, yarınki etc. Unlike Oflazer, We also allow dündeki etc.
        # TODO: Use a more general grouping, not using Secondary Pos

        time = NoSurfaceAfterDerivation().and_(SecondaryPosIs(SecondaryPos.Time))

        dun = self.lexicon.get_item_by_id("dün_Noun_Time")
        gun = self.lexicon.get_item_by_id("gün_Noun_Time")
        bugun = self.lexicon.get_item_by_id("bugün_Noun_Time")
        ileri = self.lexicon.get_item_by_id("ileri_Noun")
        geri = self.lexicon.get_item_by_id("geri_Noun")
        ote = self.lexicon.get_item_by_id("öte_Noun")
        beri = self.lexicon.get_item_by_id("beri_Noun")

        time2 = DictionaryItemIsAny(dun, gun, bugun)
        self.nom_ST.add(self.rel_S, "ki", time.and_not(time2))
        self.nom_ST.add(self.rel_S, "ki", DictionaryItemIsAny(ileri, geri, ote, beri))
        self.nom_ST.add(self.rel_S, "kü", time2.and_(time))

        # After Genitive suffix, Rel suffix makes a Pronoun derivation.
        self.gen_ST.add(self.relToPron_S, "ki")
        self.relToPron_S.add_empty(self.pronAfterRel_S)

        verbDeriv = ContainsMorpheme(inf1, inf2, inf3, pastPart, futPart)

        self.nom_ST.add(
            self.become_S,
            "lAş",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(adj)).and_not(verbDeriv),
        )
        self.become_S.add_empty(self.verbRoot_S)

        self.nom_ST.add(
            self.acquire_S,
            "lAn",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(adj)).and_not(verbDeriv),
        )

        self.acquire_S.add_empty(self.verbRoot_S)

        # Inf1 mak makes noun derivation. However, it cannot get any possessive or plural suffix.
        # Also cannot be followed by Dat, Gen, Acc case suffixes.
        # So we create a path only for it.
        self.nounInf1Root_S.add_empty(self.a3sgInf1_S)
        self.a3sgInf1_S.add_empty(self.pnonInf1_S)
        self.pnonInf1_S.add_empty(self.nom_ST)
        self.pnonInf1_S.add(self.abl_ST, "tAn")

        self.pnonInf1_S.add(self.loc_ST, "tA")
        self.pnonInf1_S.add(self.ins_ST, "lA")

        self.nounActOfRoot_S.add_empty(self.a3sgActOf_S)
        self.nounActOfRoot_S.add(self.a3plActOf_S, "lar")
        self.a3sgActOf_S.add_empty(self.pnonActOf)
        self.a3plActOf_S.add_empty(self.pnonActOf)
        self.pnonActOf.add_empty(self.nom_ST)

    def connect_last_vowel_drop_words(self):
        self.nounLastVowelDropRoot_S.add_empty(self.a3sgLastVowelDrop_S)
        self.nounLastVowelDropRoot_S.add(self.a3PlLastVowelDrop_S, "lAr")
        self.a3sgLastVowelDrop_S.add_empty(self.pNonLastVowelDrop_S)
        self.a3PlLastVowelDrop_S.add_empty(self.pNonLastVowelDrop_S)
        self.pNonLastVowelDrop_S.add(self.loc_ST, ">dA")
        self.pNonLastVowelDrop_S.add(self.abl_ST, ">dAn")

        self.adjLastVowelDropRoot_S.add_empty(self.zeroLastVowelDrop_S)
        self.postpLastVowelDropRoot_S.add_empty(self.zeroLastVowelDrop_S)
        self.zeroLastVowelDrop_S.add_empty(self.nounLastVowelDropRoot_S)

    def connect_proper_nouns_and_abbreviations(self):
        # ---- Proper noun handling -------
        # TODO: consider adding single quote after an overhaul.
        # self.nounProper_S.add(self.puncProperSeparator_S, "'")
        self.nounProper_S.add_empty(self.a3sg_S)
        self.nounProper_S.add(self.a3pl_S, "lAr")
        self.puncProperSeparator_S.add_empty(self.a3sg_S)
        self.puncProperSeparator_S.add(self.a3pl_S, "lAr")

        # ---- Abbreviation Handling -------
        # TODO: consider restricting possessive, most derivation and plural suffixes.
        self.nounAbbrv_S.add_empty(self.a3sg_S)
        self.nounAbbrv_S.add(self.a3pl_S, "lAr")

        # ----- This is for catching words that cannot have a suffix.
        self.nounNoSuffix_S.add_empty(self.nounA3sgNoSuffix_S)
        self.nounA3sgNoSuffix_S.add_empty(self.nounPnonNoSuffix_S)
        self.nounPnonNoSuffix_S.add_empty(self.nounNomNoSuffix_ST)

    def connect_adjective_states(self):
        # zero morpheme derivation. Words like "yeşil-i" requires Adj to Noun conversion.
        # Since noun suffixes are not derivational a "Zero" morpheme is used for this.
        # Transition has a HasTail() condition because Adj->Zero->Noun+A3sg+Pnon+Nom) is not allowed.
        self.adjectiveRoot_ST.add_empty(self.adjZeroDeriv_S, HasTail())

        self.adjZeroDeriv_S.add_empty(self.noun_S)

        self.adjZeroDeriv_S.add_empty(self.nVerb_S)

        self.adjectiveRoot_ST.add(self.aLy_S, ">cA")
        self.aLy_S.add_empty(self.advRoot_ST)

        self.adjectiveRoot_ST.add(
            self.aAsIf_S, ">cA", ContainsMorpheme(asIf, ly, agt, with_, justLike).not_()
        )

        self.aAsIf_S.add_empty(self.adjectiveRoot_ST)

        self.adjectiveRoot_ST.add(
            self.aAgt_S, ">cI", ContainsMorpheme(asIf, ly, agt, with_, justLike).not_()
        )
        self.aAgt_S.add_empty(self.noun_S)

        self.adjectiveRoot_ST.add(
            self.justLike_S,
            "+msI",
            NoSurfaceAfterDerivation().and_(ContainsMorpheme(justLike).not_()),
        )

        self.adjectiveRoot_ST.add(
            self.justLike_S,
            "ImsI",
            not_have(PhoneticAttribute.LastLetterVowel)
            .and_(NoSurfaceAfterDerivation())
            .and_(ContainsMorpheme(justLike).not_()),
        )

        self.adjectiveRoot_ST.add(self.become_S, "lAş", NoSurfaceAfterDerivation())
        self.adjectiveRoot_ST.add(self.acquire_S, "lAn", NoSurfaceAfterDerivation())

        c1 = PreviousMorphemeIsAny(futPart, pastPart)

        self.adjAfterVerb_S.add_empty(self.aPnon_ST, c1)
        self.adjAfterVerb_S.add(self.aP1sg_ST, "Im", c1)
        self.adjAfterVerb_S.add(self.aP2sg_ST, "In", c1)
        self.adjAfterVerb_S.add(self.aP3sg_ST, "I", c1)
        self.adjAfterVerb_S.add(self.aP1pl_ST, "ImIz", c1)
        self.adjAfterVerb_S.add(self.aP2pl_ST, "InIz", c1)
        self.adjAfterVerb_S.add(self.aP3pl_ST, "lArI", c1)

        self.adjectiveRoot_ST.add(self.ness_S, "lI~k")
        self.adjectiveRoot_ST.add(self.ness_S, "lI!ğ")

        self.adjAfterVerb_ST.add(self.ness_S, "lI~k", PreviousMorphemeIs(aorPart))
        self.adjAfterVerb_ST.add(self.ness_S, "lI!ğ", PreviousMorphemeIs(aorPart))

    def connect_numeral_states(self):
        self.numeralRoot_ST.add(self.ness_S, "lI~k")
        self.numeralRoot_ST.add(self.ness_S, "lI!ğ")
        self.numeralRoot_ST.add_empty(self.numZeroDeriv_S, HasTail())
        self.numZeroDeriv_S.add_empty(self.noun_S)
        self.numZeroDeriv_S.add_empty(self.nVerb_S)

        self.numeralRoot_ST.add(
            self.justLike_S,
            "+msI",
            NoSurfaceAfterDerivation().and_(ContainsMorpheme(justLike).not_()),
        )

        self.numeralRoot_ST.add(
            self.justLike_S,
            "ImsI",
            not_have(PhoneticAttribute.LastLetterVowel)
            .and_(NoSurfaceAfterDerivation())
            .and_(ContainsMorpheme(justLike).not_()),
        )

    def connect_verb_after_noun_adj_states(self):
        # elma-..-ε-yım
        self.nVerb_S.add_empty(self.nPresent_S)

        # elma-ydı, çorap-tı
        self.nVerb_S.add(self.nPast_S, "+y>dI")
        # elma-ymış
        self.nVerb_S.add(self.nNarr_S, "+ymIş")

        self.nVerb_S.add(self.nCond_S, "+ysA")

        self.nVerb_S.add(self.vWhile_S, "+yken")

        # word "değil" is special. It contains negative suffix implicitly. Also it behaves like
        # noun->Verb Zero morpheme derivation. because it cannot have most Verb suffixes.
        # So we connect it to a separate root state "nVerbDegil" instead of Verb
        degilRoot = self.lexicon.get_item_by_id("değil_Verb")
        self.nVerbDegil_S.add_empty(self.nNeg_S, DictionaryItemIs(degilRoot))
        # copy transitions from self.nVerb_S
        self.nNeg_S.copy_outgoing_transitions_from(self.nVerb_S)

        noFamily = not_have(RootAttribute.FamilyMember)
        # for preventing elmamım, elmamdım
        # self.pP1sg_S, self.pDat_ST, self.pA1sg_S, self.pA1pl_S, self.pA3pl_S, self.pP2sg_S, self.pP1pl_S, self.pP3sg_S, self.pP1sg_S
        # TODO: below causes "beklemedeyiz" to fail.

        verbDeriv = ContainsMorpheme(inf1, inf2, inf3, pastPart, futPart)

        allowA1sgTrans = noFamily.and_not(ContainsMorphemeSequence(p1sg, nom)).and_not(
            verbDeriv
        )

        allowA2sgTrans = noFamily.and_not(ContainsMorphemeSequence(p2sg, nom)).and_not(
            verbDeriv
        )

        allowA3plTrans = (
            noFamily.and_not(PreviousGroupContains(self.a3pl_S))
            .and_not(ContainsMorphemeSequence(p3pl, nom))
            .and_not(verbDeriv)
        )

        allowA2plTrans = noFamily.and_not(ContainsMorphemeSequence(p2pl, nom)).and_not(
            verbDeriv
        )

        allowA1plTrans = (
            noFamily.and_not(ContainsMorphemeSequence(p1sg, nom))
            .and_not(ContainsMorphemeSequence(p1pl, nom))
            .and_not(verbDeriv)
        )
        # elma-yım
        self.nPresent_S.add(self.nA1sg_ST, "+yIm", allowA1sgTrans)
        self.nPresent_S.add(self.nA2sg_ST, "sIn", allowA2sgTrans)

        # elma-ε-ε-dır to non terminal A3sg. We do not allow ending with A3sg from empty Present tense.
        self.nPresent_S.add_empty(self.nA3sg_S)

        # we allow `değil` to end with terminal A3sg from Present tense.
        self.nPresent_S.add_empty(self.nA3sg_ST, DictionaryItemIs(degilRoot))

        # elma-lar, elma-da-lar as Verb.
        # TODO: consider disallowing this for "elmalar" case.
        self.nPresent_S.add(
            self.nA3pl_ST,
            "lAr",
            not_have(RootAttribute.CompoundP3sg)
            # do not allow "okumak-lar"
            .and_not(PreviousGroupContainsMorpheme(inf1))
            .and_(allowA3plTrans),
        )

        # elma-ydı-m. Do not allow "elmaya-yım" (Oflazer accepts this)
        self.nPast_S.add(self.nA1sg_ST, "m", allowA1sgTrans)
        self.nNarr_S.add(self.nA1sg_ST, "Im", allowA1sgTrans)

        self.nPast_S.add(self.nA2sg_ST, "n", allowA2sgTrans)
        self.nNarr_S.add(self.nA2sg_ST, "sIn", allowA2sgTrans)

        self.nPast_S.add(self.nA1pl_ST, "k", allowA1plTrans)
        self.nNarr_S.add(self.nA1pl_ST, "Iz", allowA1plTrans)
        self.nPresent_S.add(self.nA1pl_ST, "+yIz", allowA1plTrans)

        self.nPast_S.add(self.nA2pl_ST, "InIz", allowA2plTrans)
        self.nNarr_S.add(self.nA2pl_ST, "sInIz", allowA2plTrans)
        self.nPresent_S.add(self.nA2pl_ST, "sInIz", allowA2plTrans)

        # elma-ydı-lar.
        self.nPast_S.add(
            self.nA3pl_ST,
            "lAr",
            not_have(RootAttribute.CompoundP3sg).and_(allowA3plTrans),
        )
        # elma-ymış-lar.
        self.nNarr_S.add(
            self.nA3pl_ST,
            "lAr",
            not_have(RootAttribute.CompoundP3sg).and_(allowA3plTrans),
        )

        # elma-ydı-ε
        self.nPast_S.add_empty(self.nA3sg_ST)
        # elma-ymış-ε
        self.nNarr_S.add_empty(self.nA3sg_ST)

        # narr+cons is allowed but not past+cond
        self.nNarr_S.add(self.nCond_S, "sA")

        self.nCond_S.add(self.nA1sg_ST, "m", allowA1sgTrans)
        self.nCond_S.add(self.nA2sg_ST, "n", allowA2sgTrans)
        self.nCond_S.add(self.nA1pl_ST, "k", allowA1plTrans)
        self.nCond_S.add(self.nA2pl_ST, "nIz", allowA2plTrans)
        self.nCond_S.add_empty(self.nA3sg_ST)
        self.nCond_S.add(self.nA3pl_ST, "lAr")

        # for not allowing "elma-ydı-m-dır"

        rejectNoCopula = CurrentGroupContainsAny(
            self.nPast_S, self.nCond_S, self.nCopBeforeA3pl_S
        ).not_()

        # elma-yım-dır
        self.nA1sg_ST.add(self.nCop_ST, "dIr", rejectNoCopula)
        # elmasındır
        self.nA2sg_ST.add(self.nCop_ST, "dIr", rejectNoCopula)
        # elmayızdır
        self.nA1pl_ST.add(self.nCop_ST, "dIr", rejectNoCopula)
        # elmasınızdır
        self.nA2pl_ST.add(self.nCop_ST, "dIr", rejectNoCopula)

        self.nA3sg_S.add(self.nCop_ST, ">dIr", rejectNoCopula)

        self.nA3pl_ST.add(self.nCop_ST, "dIr", rejectNoCopula)

        asIfCond = PreviousMorphemeIsAny(narr)
        self.nA3sg_ST.add(self.vAsIf_S, ">cAsInA", asIfCond)
        self.nA1sg_ST.add(self.vAsIf_S, ">cAsInA", asIfCond)
        self.nA2sg_ST.add(self.vAsIf_S, ">cAsInA", asIfCond)
        self.nA1pl_ST.add(self.vAsIf_S, ">cAsInA", asIfCond)
        self.nA2pl_ST.add(self.vAsIf_S, ">cAsInA", asIfCond)
        self.nA3pl_ST.add(self.vAsIf_S, ">cAsInA", asIfCond)

        # Copula can come before A3pl.
        self.nPresent_S.add(self.nCopBeforeA3pl_S, ">dIr")
        self.nCopBeforeA3pl_S.add(self.nA3pl_ST, "lAr")

    def connect_pronoun_states(self):
        # ----------- Personal Pronouns ----------------------------

        ben = self.lexicon.get_item_by_id("ben_Pron_Pers")
        sen = self.lexicon.get_item_by_id("sen_Pron_Pers")
        o = self.lexicon.get_item_by_id("o_Pron_Pers")
        biz = self.lexicon.get_item_by_id("biz_Pron_Pers")
        siz = self.lexicon.get_item_by_id("siz_Pron_Pers")
        falan = self.lexicon.get_item_by_id("falan_Pron_Pers")
        falanca = self.lexicon.get_item_by_id("falanca_Pron_Pers")

        self.pronPers_S.add_empty(self.pA1sg_S, DictionaryItemIs(ben))
        self.pronPers_S.add_empty(self.pA2sg_S, DictionaryItemIs(sen))
        self.pronPers_S.add_empty(self.pA3sg_S, DictionaryItemIsAny(o, falan, falanca))
        self.pronPers_S.add(
            self.pA3pl_S, "nlAr", DictionaryItemIs(o)
        )  # Oflazer does not have "onlar" as Pronoun root.

        self.pronPers_S.add(self.pA3pl_S, "lAr", DictionaryItemIsAny(falan, falanca))
        self.pronPers_S.add_empty(self.pA1pl_S, DictionaryItemIs(biz))
        self.pronPers_S.add(self.pA1pl_S, "lAr", DictionaryItemIs(biz))
        self.pronPers_S.add_empty(self.pA2pl_S, DictionaryItemIs(siz))
        self.pronPers_S.add(self.pA2pl_S, "lAr", DictionaryItemIs(siz))

        # --- modified `ben-sen` special state and transitions
        self.pronPers_Mod_S.add_empty(self.pA1sgMod_S, DictionaryItemIs(ben))
        self.pronPers_Mod_S.add_empty(self.pA2sgMod_S, DictionaryItemIs(sen))
        self.pA1sgMod_S.add_empty(self.pPnonMod_S)
        self.pA2sgMod_S.add_empty(self.pPnonMod_S)
        self.pPnonMod_S.add(self.pDat_ST, "A")
        # ----

        # Possesive connecitons are not used.
        self.pA1sg_S.add_empty(self.pPnon_S)
        self.pA2sg_S.add_empty(self.pPnon_S)
        self.pA3sg_S.add_empty(self.pPnon_S)
        self.pA1pl_S.add_empty(self.pPnon_S)
        self.pA2pl_S.add_empty(self.pPnon_S)
        self.pA3pl_S.add_empty(self.pPnon_S)

        # ------------ Noun -> Rel -> Pron ---------------------------
        # masanınki
        self.pronAfterRel_S.add_empty(self.pA3sgRel_S)
        self.pronAfterRel_S.add(self.pA3plRel_S, "lAr")
        self.pA3sgRel_S.add_empty(self.pPnonRel_S)
        self.pA3plRel_S.add_empty(self.pPnonRel_S)
        self.pPnonRel_S.add_empty(self.pNom_ST)
        self.pPnonRel_S.add(self.pDat_ST, "+nA")
        self.pPnonRel_S.add(self.pAcc_ST, "+nI")
        self.pPnonRel_S.add(self.pAbl_ST, "+ndAn")
        self.pPnonRel_S.add(self.pLoc_ST, "+ndA")
        self.pPnonRel_S.add(self.pIns_ST, "+ylA")
        self.pPnonRel_S.add(self.pGen_ST, "+nIn")

        # ------------ Demonstrative pronouns. ------------------------

        bu = self.lexicon.get_item_by_id("bu_Pron_Demons")

        su = self.lexicon.get_item_by_id("şu_Pron_Demons")

        o_demons = self.lexicon.get_item_by_id("o_Pron_Demons")

        self.pronDemons_S.add_empty(self.pA3sg_S)
        self.pronDemons_S.add(self.pA3pl_S, "nlAr")

        # ------------ Quantitiva Pronouns ----------------------------

        birbiri = self.lexicon.get_item_by_id("birbiri_Pron_Quant")
        biri = self.lexicon.get_item_by_id("biri_Pron_Quant")
        bazi = self.lexicon.get_item_by_id("bazı_Pron_Quant")
        bircogu = self.lexicon.get_item_by_id("birçoğu_Pron_Quant")
        birkaci = self.lexicon.get_item_by_id("birkaçı_Pron_Quant")
        beriki = self.lexicon.get_item_by_id("beriki_Pron_Quant")
        cogu = self.lexicon.get_item_by_id("çoğu_Pron_Quant")
        cumlesi = self.lexicon.get_item_by_id("cümlesi_Pron_Quant")
        hep = self.lexicon.get_item_by_id("hep_Pron_Quant")
        herbiri = self.lexicon.get_item_by_id("herbiri_Pron_Quant")
        herkes = self.lexicon.get_item_by_id("herkes_Pron_Quant")
        hicbiri = self.lexicon.get_item_by_id("hiçbiri_Pron_Quant")
        hepsi = self.lexicon.get_item_by_id("hepsi_Pron_Quant")
        kimi = self.lexicon.get_item_by_id("kimi_Pron_Quant")
        kimse = self.lexicon.get_item_by_id("kimse_Pron_Quant")
        oburku = self.lexicon.get_item_by_id("öbürkü_Pron_Quant")
        oburu = self.lexicon.get_item_by_id("öbürü_Pron_Quant")
        tumu = self.lexicon.get_item_by_id("tümü_Pron_Quant")
        topu = self.lexicon.get_item_by_id("topu_Pron_Quant")
        umum = self.lexicon.get_item_by_id("umum_Pron_Quant")

        # we have separate A3pl and A3sg states for Quantitive Pronouns.
        # herkes and hep cannot be singular.
        self.pronQuant_S.add_empty(
            self.pQuantA3sg_S,
            DictionaryItemIsAny(
                herkes, umum, hepsi, cumlesi, hep, tumu, birkaci, topu
            ).not_(),
        )

        self.pronQuant_S.add(
            self.pQuantA3pl_S,
            "lAr",
            DictionaryItemIsAny(
                hep,
                hepsi,
                birkaci,
                umum,
                cumlesi,
                cogu,
                bircogu,
                herbiri,
                tumu,
                hicbiri,
                topu,
                oburu,
            ).not_(),
        )

        # bazılarınız -> A1pl+P1pl
        self.pronQuant_S.add(self.pQuantA1pl_S, "lAr", DictionaryItemIsAny(bazi))
        self.pronQuant_S.add(self.pQuantA2pl_S, "lAr", DictionaryItemIsAny(bazi))

        # Herkes is implicitly plural.
        self.pronQuant_S.add_empty(
            self.pQuantA3pl_S,
            DictionaryItemIsAny(
                herkes, umum, birkaci, hepsi, cumlesi, cogu, bircogu, tumu, topu
            ),
        )

        # connect "kimse" to Noun-A3sg and Noun-A3pl. It behaves like a noun.
        self.pronQuant_S.add_empty(self.a3sg_S, DictionaryItemIs(kimse))
        self.pronQuant_S.add(self.a3pl_S, "lAr", DictionaryItemIsAny(kimse))

        # for `birbiri-miz` `hep-imiz`
        self.pronQuant_S.add_empty(
            self.pQuantA1pl_S,
            DictionaryItemIsAny(
                biri,
                bazi,
                birbiri,
                birkaci,
                herbiri,
                hep,
                kimi,
                cogu,
                bircogu,
                tumu,
                topu,
                hicbiri,
            ),
        )

        # for `birbiri-niz` and `hep-iniz`
        self.pronQuant_S.add_empty(
            self.pQuantA2pl_S,
            DictionaryItemIsAny(
                biri,
                bazi,
                birbiri,
                birkaci,
                herbiri,
                hep,
                kimi,
                cogu,
                bircogu,
                tumu,
                topu,
                hicbiri,
            ),
        )

        # this is used for birbir-ler-i, çok-lar-ı, birçok-lar-ı separate root and A3pl states are
        # used for this.
        self.pronQuantModified_S.add_empty(self.pQuantModA3pl_S)
        self.pQuantModA3pl_S.add(self.pP3pl_S, "lArI")

        # both `biri-ne` and `birisi-ne` or `birbirine` and `birbirisine` are accepted.
        self.pQuantA3sg_S.add_empty(
            self.pP3sg_S,
            DictionaryItemIsAny(
                biri, birbiri, kimi, herbiri, hicbiri, oburu, oburku, beriki
            ).and_(not_have(PhoneticAttribute.ModifiedPronoun)),
        )

        self.pQuantA3sg_S.add(
            self.pP3sg_S,
            "sI",
            DictionaryItemIsAny(
                biri, bazi, kimi, birbiri, herbiri, hicbiri, oburku
            ).and_(not_have(PhoneticAttribute.ModifiedPronoun)),
        )

        # there is no connection from pQuantA3pl to Pnon for preventing `biriler` (except herkes)
        self.pQuantA3pl_S.add(
            self.pP3pl_S,
            "I",
            DictionaryItemIsAny(biri, bazi, birbiri, kimi, oburku, beriki),
        )
        self.pQuantA3pl_S.add_empty(
            self.pP3pl_S,
            DictionaryItemIsAny(hepsi, birkaci, cumlesi, cogu, tumu, topu, bircogu),
        )
        self.pQuantA3pl_S.add_empty(
            self.pPnon_S, DictionaryItemIsAny(herkes, umum, oburku, beriki)
        )

        self.pQuantA1pl_S.add(self.pP1pl_S, "ImIz")
        self.pQuantA2pl_S.add(self.pP2pl_S, "InIz")

        # ------------ Question Pronouns ----------------------------
        # `kim` (kim_Pron_Ques), `ne` and `nere`

        ne = self.lexicon.get_item_by_id("ne_Pron_Ques")
        nere = self.lexicon.get_item_by_id("nere_Pron_Ques")
        kim = self.lexicon.get_item_by_id("kim_Pron_Ques")
        self.pronQues_S.add_empty(self.pQuesA3sg_S)
        self.pronQues_S.add(self.pQuesA3pl_S, "lAr")

        self.pQuesA3sg_S.add_all(
            [
                (self.pPnon_S, ""),
                (self.pP3sg_S, "+sI"),
                (self.pP1sg_S, "Im", DictionaryItemIs(ne).not_()),
                (self.pP1sg_S, "yIm", DictionaryItemIs(ne)),
                (self.pP2sg_S, "In", DictionaryItemIs(ne).not_()),
                (self.pP2sg_S, "yIn", DictionaryItemIs(ne)),
                (self.pP1pl_S, "ImIz", DictionaryItemIs(ne).not_()),
                (self.pP1pl_S, "yImIz", DictionaryItemIs(ne)),
            ]
        )

        self.pQuesA3pl_S.add_all(
            [
                (self.pPnon_S, ""),
                (self.pP3sg_S, "I"),
                (self.pP1sg_S, "Im"),
                (self.pP1pl_S, "ImIz"),
            ]
        )

        # ------------ Reflexive Pronouns ----------------------------
        # `kendi`

        kendi = self.lexicon.get_item_by_id("kendi_Pron_Reflex")
        self.pronReflex_S.add_all(
            [
                (self.pReflexA1sg_S, ""),
                (self.pReflexA2sg_S, ""),
                (self.pReflexA3sg_S, ""),
                (self.pReflexA1pl_S, ""),
                (self.pReflexA2pl_S, ""),
                (self.pReflexA3pl_S, ""),
            ]
        )

        self.pReflexA1sg_S.add(self.pP1sg_S, "Im")
        self.pReflexA2sg_S.add(self.pP2sg_S, "In")
        self.pReflexA3sg_S.add(self.pP3sg_S, "+sI")
        self.pReflexA2sg_S.add_empty(self.pP3sg_S)
        self.pReflexA1pl_S.add(self.pP1pl_S, "ImIz")
        self.pReflexA2pl_S.add(self.pP2pl_S, "InIz")
        self.pReflexA3pl_S.add(self.pP3pl_S, "lArI")

        # ------------------------
        # Case connections for all

        nGroup = DictionaryItemIsAny(ne, nere, falan, falanca, hep, herkes).not_()

        yGroup = DictionaryItemIsAny(ne, nere, falan, falanca, hep, herkes)

        self.pPnon_S.add_all(
            [
                (self.pNom_ST, ""),
                # not allowing `ben-e` and `sen-e`. `ban-a` and `san-a` are using different states
                (
                    self.pDat_ST,
                    "+nA",
                    DictionaryItemIsAny(
                        ben, sen, ne, nere, falan, falanca, herkes
                    ).not_(),
                ),
                (self.pDat_ST, "+yA", yGroup),
                (self.pAcc_ST, "+nI", nGroup),
                (self.pAcc_ST, "+yI", yGroup),
                (self.pLoc_ST, "+ndA", nGroup),
                (self.pLoc_ST, ">dA", yGroup),
                (self.pAbl_ST, "+ndAn", nGroup),
                (self.pAbl_ST, ">dAn", yGroup),
                (
                    self.pGen_ST,
                    "+nIn",
                    nGroup.and_(DictionaryItemIsAny(biz, ben, sen).not_()),
                ),
                (
                    self.pGen_ST,
                    "im",
                    DictionaryItemIsAny(ben, biz),
                ),  # benim, senin, bizim are genitive.
                (self.pGen_ST, "in", DictionaryItemIs(sen)),
                (self.pGen_ST, "+yIn", yGroup.and_(DictionaryItemIsAny(biz).not_())),
                (self.pEqu_ST, ">cA", yGroup),
                (self.pEqu_ST, ">cA", nGroup),
                (self.pIns_ST, "+ylA", yGroup),
                (self.pIns_ST, "+nlA", nGroup),
                (
                    self.pIns_ST,
                    "+nInlA",
                    nGroup.and_(DictionaryItemIsAny(bu, su, o, sen)),
                ),
                (self.pIns_ST, "inle", DictionaryItemIs(siz)),
                (self.pIns_ST, "imle", DictionaryItemIsAny(biz, ben)),
            ]
        )

        conditionpP1sg_S = DictionaryItemIsAny(kim, ben, ne, nere, kendi)

        self.pP1sg_S.add_all(
            [
                (self.pNom_ST, ""),
                (self.pDat_ST, "+nA", nGroup),
                (self.pAcc_ST, "+nI", nGroup),
                (self.pDat_ST, "+yA", yGroup),
                (self.pAcc_ST, "+yI", yGroup),
                (self.pLoc_ST, "+ndA", DictionaryItemIsAny(kendi)),
                (self.pAbl_ST, "+ndAn", DictionaryItemIsAny(kendi)),
                (self.pEqu_ST, "+ncA", DictionaryItemIsAny(kendi)),
                (self.pIns_ST, "+nlA", conditionpP1sg_S),
                (self.pGen_ST, "+nIn", conditionpP1sg_S),
            ]
        )

        conditionP2sg = DictionaryItemIsAny(kim, sen, ne, nere, kendi)
        self.pP2sg_S.add_all(
            [
                (self.pNom_ST, ""),
                (self.pDat_ST, "+nA", nGroup),
                (self.pAcc_ST, "+nI", nGroup),
                (self.pDat_ST, "+yA", yGroup),
                (self.pAcc_ST, "+yI", yGroup),
                (self.pLoc_ST, "+ndA", DictionaryItemIsAny(kendi)),
                (self.pAbl_ST, "+ndAn", DictionaryItemIsAny(kendi)),
                (self.pEqu_ST, "+ncA", DictionaryItemIsAny(kendi)),
                (self.pIns_ST, "+nlA", conditionP2sg),
                (self.pGen_ST, "+nIn", conditionP2sg),
            ]
        )

        p3sgCond = DictionaryItemIsAny(
            kendi, kim, ne, nere, o, bazi, biri, birbiri, herbiri, hep, kimi, hicbiri
        )

        self.pP3sg_S.add_all(
            [
                (self.pNom_ST, ""),
                (self.pDat_ST, "+nA", nGroup),
                (self.pAcc_ST, "+nI", nGroup),
                (self.pDat_ST, "+yA", yGroup),
                (self.pAcc_ST, "+yI", yGroup),
                (self.pLoc_ST, "+ndA", p3sgCond),
                (self.pAbl_ST, "+ndAn", p3sgCond),
                (self.pGen_ST, "+nIn", p3sgCond),
                (self.pEqu_ST, "ncA", p3sgCond),
                (self.pIns_ST, "+ylA", p3sgCond),
            ]
        )

        hepCnd = DictionaryItemIsAny(
            kendi,
            kim,
            ne,
            nere,
            biz,
            siz,
            biri,
            birbiri,
            birkaci,
            herbiri,
            hep,
            kimi,
            cogu,
            bircogu,
            tumu,
            topu,
            bazi,
            hicbiri,
        )
        self.pP1pl_S.add_all(
            [
                (self.pNom_ST, ""),
                (self.pDat_ST, "+nA", nGroup),
                (self.pAcc_ST, "+nI", nGroup),
                (self.pDat_ST, "+yA", yGroup),
                (self.pAcc_ST, "+yI", yGroup),
                (self.pLoc_ST, "+ndA", hepCnd),
                (self.pAbl_ST, "+ndAn", hepCnd),
                (self.pGen_ST, "+nIn", hepCnd),
                (self.pEqu_ST, "+ncA", hepCnd),
                (self.pIns_ST, "+nlA", hepCnd),
            ]
        )

        self.pP2pl_S.add_all(
            [
                (self.pNom_ST, ""),
                (self.pDat_ST, "+nA", nGroup),
                (self.pAcc_ST, "+nI", nGroup),
                (self.pDat_ST, "+yA", yGroup),
                (self.pAcc_ST, "+yI", yGroup),
                (self.pLoc_ST, "+ndA", hepCnd),
                (self.pAbl_ST, "+ndAn", hepCnd),
                (self.pGen_ST, "+nIn", hepCnd),
                (self.pEqu_ST, "+ncA", hepCnd),
                (self.pIns_ST, "+nlA", hepCnd),
            ]
        )

        hepsi_cnd = DictionaryItemIsAny(
            kendi,
            kim,
            ne,
            nere,
            o,
            bazi,
            biri,
            herkes,
            umum,
            birkaci,
            hepsi,
            cumlesi,
            cogu,
            bircogu,
            birbiri,
            tumu,
            kimi,
            topu,
        )

        self.pP3pl_S.add_all(
            [
                (self.pNom_ST, ""),
                (self.pDat_ST, "+nA", nGroup),
                (self.pAcc_ST, "+nI", nGroup),
                (self.pDat_ST, "+yA", yGroup),
                (self.pAcc_ST, "+yI", yGroup),
                (self.pLoc_ST, "+ndA", hepsi_cnd),
                (self.pAbl_ST, "+ndAn", hepsi_cnd),
                (self.pGen_ST, "+nIn", hepsi_cnd.or_(DictionaryItemIsAny(sen, siz))),
                (self.pEqu_ST, "+ncA", hepsi_cnd),
                (self.pIns_ST, "+ylA", hepsi_cnd),
            ]
        )

        self.pNom_ST.add(
            self.with_S,
            "+nlI",
            DictionaryItemIsAny(bu, su, o_demons, ben, sen, o, biz, siz),
        )
        self.pNom_ST.add(self.with_S, "lI", DictionaryItemIsAny(nere))
        self.pNom_ST.add(self.with_S, "+ylI", DictionaryItemIsAny(ne))
        self.pNom_ST.add(
            self.without_S,
            "+nsIz",
            DictionaryItemIsAny(nere, bu, su, o_demons, ben, sen, o, biz, siz),
        )
        self.pNom_ST.add(self.without_S, "+ysIz", DictionaryItemIsAny(ne))
        self.pGen_ST.add(
            self.rel_S,
            "ki",
            DictionaryItemIsAny(nere, bu, su, o_demons, ne, sen, o, biz, siz),
        )

        notRelRepetition = HasTailSequence(rel, adj, zero, noun, a3sg, pnon, loc).not_()
        self.pLoc_ST.add(self.rel_S, "ki", notRelRepetition)

        self.pIns_ST.add(self.vWhile_S, "+yken")

        # ------------- Derivation connections ---------

        self.pNom_ST.add_empty(self.pronZeroDeriv_S, HasTail())
        self.pDat_ST.add_empty(self.pronZeroDeriv_S, HasTail())
        self.pLoc_ST.add_empty(self.pronZeroDeriv_S, HasTail())
        self.pAbl_ST.add_empty(self.pronZeroDeriv_S, HasTail())
        self.pGen_ST.add_empty(self.pronZeroDeriv_S, HasTail())
        self.pIns_ST.add_empty(self.pronZeroDeriv_S, HasTail())

        self.pronZeroDeriv_S.add_empty(self.pvVerbRoot_S)

    def connect_verb_after_pronoun(self):
        self.pvVerbRoot_S.add_empty(self.pvPresent_S)

        self.pvVerbRoot_S.add(self.vWhile_S, "+yken")

        self.pvVerbRoot_S.add(self.pvPast_S, "+ydI")

        self.pvVerbRoot_S.add(self.pvNarr_S, "+ymIş")

        self.pvVerbRoot_S.add(self.pvCond_S, "+ysA")

        # disallow `benin, bizim with A1sg analysis etc.`

        allowA1sgTrans = PreviousGroupContains(self.pA1pl_S, self.pP1sg_S).not_()

        allowA1plTrans = PreviousGroupContains(
            self.pA1sg_S, self.pA2sg_S, self.pP1sg_S, self.pP2sg_S
        ).not_()

        allowA2sgTrans = PreviousGroupContains(self.pA2pl_S, self.pP2sg_S).not_()

        allowA2plTrans = PreviousGroupContains(self.pA2sg_S, self.pP2pl_S).not_()

        self.pvPresent_S.add(self.pvA1sg_ST, "+yIm", allowA1sgTrans)
        self.pvPresent_S.add(self.pvA2sg_ST, "sIn", allowA2sgTrans)
        # We do not allow ending with A3sg from empty Present tense.
        self.pvPresent_S.add_empty(self.nA3sg_S)
        self.pvPresent_S.add(self.pvA1pl_ST, "+yIz", allowA1plTrans)
        self.pvPresent_S.add(self.pvA2pl_ST, "sInIz")
        self.pvPresent_S.add(self.pvA3pl_ST, "lAr", PreviousGroupContains(self.pLoc_ST))

        self.pvPast_S.add(self.pvA1sg_ST, "m", allowA1sgTrans)
        self.pvPast_S.add(self.pvA2sg_ST, "n", allowA2sgTrans)
        self.pvPast_S.add(self.pvA1pl_ST, "k", allowA1plTrans)
        self.pvPast_S.add(self.pvA2pl_ST, "InIz")
        self.pvPast_S.add(self.pvA3pl_ST, "lAr")
        self.pvPast_S.add_empty(self.pvA3sg_ST)

        self.pvNarr_S.add(self.pvA1sg_ST, "Im", allowA1sgTrans)
        self.pvNarr_S.add(self.pvA2sg_ST, "sIn", allowA2sgTrans)
        self.pvNarr_S.add(self.pvA1pl_ST, "Iz", allowA1plTrans)
        self.pvNarr_S.add(self.pvA2pl_ST, "sInIz")
        self.pvNarr_S.add(self.pvA3pl_ST, "lAr")
        self.pvNarr_S.add_empty(self.pvA3sg_ST)
        # narr+cons is allowed but not past+cond
        self.pvNarr_S.add(self.pvCond_S, "sA")

        self.pvCond_S.add(self.pvA1sg_ST, "m", allowA1sgTrans)
        self.pvCond_S.add(self.pvA2sg_ST, "n", allowA2sgTrans)
        self.pvCond_S.add(self.pvA1pl_ST, "k", allowA1plTrans)
        self.pvCond_S.add(self.pvA2pl_ST, "nIz", allowA2plTrans)
        self.pvCond_S.add_empty(self.pvA3sg_ST)
        self.pvCond_S.add(self.pvA3pl_ST, "lAr")

        rejectNoCopula = CurrentGroupContainsAny(
            self.pvPast_S, self.pvCond_S, self.pvCopBeforeA3pl_S
        ).not_()

        self.pvA1sg_ST.add(self.pvCop_ST, "dIr", rejectNoCopula)
        self.pvA2sg_ST.add(self.pvCop_ST, "dIr", rejectNoCopula)
        self.pvA1pl_ST.add(self.pvCop_ST, "dIr", rejectNoCopula)
        self.pvA2pl_ST.add(self.pvCop_ST, "dIr", rejectNoCopula)

        self.pvA3sg_S.add(self.pvCop_ST, ">dIr", rejectNoCopula)

        self.pvA3pl_ST.add(self.pvCop_ST, "dIr", rejectNoCopula)

        # Copula can come before A3pl.
        self.pvPresent_S.add(self.pvCopBeforeA3pl_S, ">dIr")
        self.pvCopBeforeA3pl_S.add(self.pvA3pl_ST, "lAr")

    def connect_adverbs(self):
        self.advNounRoot_ST.add_empty(self.avZero_S)
        self.avZero_S.add_empty(self.avNounAfterAdvRoot_ST)
        self.avNounAfterAdvRoot_ST.add_empty(self.avA3sg_S)
        self.avA3sg_S.add_empty(self.avPnon_S)
        self.avPnon_S.add(self.avDat_ST, "+yA")

        self.advForVerbDeriv_ST.add_empty(self.avZeroToVerb_S)
        self.avZeroToVerb_S.add_empty(self.nVerb_S)

    def connect_postpositives(self):
        self.postpRoot_ST.add_empty(self.postpZero_S)
        self.postpZero_S.add_empty(self.nVerb_S)

        # gibi is kind of special.
        gibiGen = self.lexicon.get_item_by_id("gibi_Postp_PCGen")
        gibiNom = self.lexicon.get_item_by_id("gibi_Postp_PCNom")
        sonraAbl = self.lexicon.get_item_by_id("sonra_Postp_PCAbl")
        self.postpZero_S.add_empty(
            self.po2nRoot_S, DictionaryItemIsAny(gibiGen, gibiNom, sonraAbl)
        )

        self.po2nRoot_S.add_empty(self.po2nA3sg_S)
        self.po2nRoot_S.add(self.po2nA3pl_S, "lAr")

        # gibisi, gibim-e, gibi-e, gibi-mize
        self.po2nA3sg_S.add(self.po2nP3sg_S, "+sI")
        self.po2nA3sg_S.add(self.po2nP1sg_S, "m", DictionaryItemIsAny(gibiGen, gibiNom))
        self.po2nA3sg_S.add(self.po2nP2sg_S, "n", DictionaryItemIsAny(gibiGen, gibiNom))
        self.po2nA3sg_S.add(
            self.po2nP1pl_S, "miz", DictionaryItemIsAny(gibiGen, gibiNom)
        )
        self.po2nA3sg_S.add(
            self.po2nP2pl_S, "niz", DictionaryItemIsAny(gibiGen, gibiNom)
        )

        # gibileri
        self.po2nA3pl_S.add(self.po2nP3sg_S, "+sI")
        self.po2nA3pl_S.add_empty(self.po2nPnon_S)

        self.po2nP3sg_S.add_all(
            [
                (self.po2nNom_ST, ""),
                (self.po2nDat_ST, "nA"),
                (self.po2nLoc_ST, "ndA"),
                (self.po2nAbl_ST, "ndAn"),
                (self.po2nIns_ST, "ylA"),
                (self.po2nGen_ST, "nIn"),
                (self.po2nAcc_ST, "nI"),
            ]
        )

        self.po2nPnon_S.add_all(
            [
                (self.po2nNom_ST, ""),
                (self.po2nDat_ST, "A"),
                (self.po2nLoc_ST, "dA"),
                (self.po2nAbl_ST, "dAn"),
                (self.po2nIns_ST, "lA"),
                (self.po2nGen_ST, "In"),
                (self.po2nEqu_ST, "cA"),
                (self.po2nAcc_ST, "I"),
            ]
        )

        self.po2nP1sg_S.add(self.po2nDat_ST, "e")
        self.po2nP2sg_S.add(self.po2nDat_ST, "e")
        self.po2nP1pl_S.add(self.po2nDat_ST, "e")
        self.po2nP2pl_S.add(self.po2nDat_ST, "e")

    def connect_verbs(self):
        # Imperative.
        self.verbRoot_S.add_empty(self.vImp_S)

        self.vImp_S.add_all(
            [
                (self.vA2sg_ST, ""),  # oku
                (self.vA2sg_ST, "sAnA"),  # oku
                (self.vA3sg_ST, "sIn"),  # okusun
                (self.vA2pl_ST, "+yIn"),  # okuyun
                (self.vA2pl_ST, "+yInIz"),  # okuyunuz
                (self.vA2pl_ST, "sAnIzA"),  # okuyunuz
                (self.vA3pl_ST, "sInlAr"),  # okusunlar
            ]
        )

        # Causative suffixes
        # Causes Verb-Verb derivation. There are three forms: "t", "tIr" and "Ir".
        # 1- "t" form is used if verb ends with a vowel, or immediately after "tIr" Causative.
        # 2- "tIr" form is used if verb ends with a consonant or immediately after "t" Causative.
        # 3- "Ir" form appears after some specific verbs but currently we treat them as separate verb.
        # such as "pişmek - pişirmek". Oflazer parses them as causative.

        self.verbRoot_S.add(
            self.vCausT_S,
            "t",
            HasRootAttribute(RootAttribute.Causative_t)
            .or_(LastDerivationIs(self.vCausTir_S))
            .and_not(LastDerivationIsAny(self.vCausT_S, self.vPass_S, self.vAble_S)),
        )

        self.verbRoot_S.add(
            self.vCausTir_S,
            ">dIr",
            HasPhoneticAttribute(PhoneticAttribute.LastLetterConsonant).and_not(
                LastDerivationIsAny(self.vCausTir_S, self.vPass_S, self.vAble_S)
            ),
        )

        self.vCausT_S.add_empty(self.verbRoot_S)
        self.vCausTir_S.add_empty(self.verbRoot_S)

        # Progressive1 suffix. "-Iyor"
        # if last letter is a vowel, this is handled with self.verbRoot_VowelDrop_S root.
        self.verbRoot_S.add(
            self.vProgYor_S, "Iyor", not_have(PhoneticAttribute.LastLetterVowel)
        )

        # For "aramak", the modified root "ar" connects to self.verbRoot_VowelDrop_S. Here it is connected to
        # progressive "Iyor" suffix. We use a separate root state for these for convenience.
        self.verbRoot_VowelDrop_S.add(self.vProgYor_S, "Iyor")
        self.vProgYor_S.add_all(
            [
                (self.vA1sg_ST, "um"),
                (self.vA2sg_ST, "sun"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "uz"),
                (self.vA2pl_ST, "sunuz"),
                (self.vA3pl_ST, "lar"),
                (self.vCond_S, "sa"),
                (self.vPastAfterTense_S, "du"),
                (self.vNarrAfterTense_S, "muş"),
                (self.vCopBeforeA3pl_S, "dur"),
                (self.vWhile_S, "ken"),
            ]
        )

        # Progressive - 2 "-mAktA"
        self.verbRoot_S.add(self.vProgMakta_S, "mAktA")
        self.vProgMakta_S.add_all(
            [
                (self.vA1sg_ST, "yIm"),
                (self.vA2sg_ST, "sIn"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "yIz"),
                (self.vA2pl_ST, "sInIz"),
                (self.vA3pl_ST, "lAr"),
                (self.vCond_S, "ysA"),
                (self.vPastAfterTense_S, "ydI"),
                (self.vNarrAfterTense_S, "ymIş"),
                (self.vCopBeforeA3pl_S, "dIr"),
                (self.vWhile_S, "yken"),
            ]
        )

        # Positive Aorist Tense.
        # For single syllable words, it forms as "ar-er". For others "ir-ır-ur-ür"
        # However there are exceptions to it as well. So dictionary items are marked as Aorist_I and
        # Aorist_A.
        self.verbRoot_S.add(
            self.vAor_S,
            "Ir",
            HasRootAttribute(RootAttribute.Aorist_I).or_(HasAnySuffixSurface()),
        )
        self.verbRoot_S.add(
            self.vAor_S,
            "Ar",
            HasRootAttribute(RootAttribute.Aorist_A).and_(HasAnySuffixSurface().not_()),
        )
        self.vAor_S.add_all(
            [
                (self.vA1sg_ST, "Im"),
                (self.vA2sg_ST, "sIn"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "Iz"),
                (self.vA2pl_ST, "sInIz"),
                (self.vA3pl_ST, "lAr"),
                (self.vPastAfterTense_S, "dI"),
                (self.vNarrAfterTense_S, "mIş"),
                (self.vCond_S, "sA"),
                (self.vCopBeforeA3pl_S, "dIr"),
                (self.vWhile_S, "ken"),
            ]
        )

        # Negative
        self.verbRoot_S.add(self.vNeg_S, "mA", PreviousMorphemeIs(able).not_())

        self.vNeg_S.add_all(
            [
                (self.vImp_S, ""),
                (self.vPast_S, "dI"),
                (self.vFut_S, "yAcA~k"),
                (self.vFut_S, "yAcA!ğ"),
                (self.vNarr_S, "mIş"),
                (self.vProgMakta_S, "mAktA"),
                (self.vOpt_S, "yA"),
                (self.vDesr_S, "sA"),
                (self.vNeces_S, "mAlI"),
                (self.vInf1_S, "mAk"),
                (self.vInf2_S, "mA"),
                (self.vInf3_S, "yIş"),
                (self.vActOf_S, "mAcA"),
                (self.vPastPart_S, "dI~k"),
                (self.vPastPart_S, "dI!ğ"),
                (self.vFutPart_S, "yAcA~k"),
                (self.vFutPart_S, "yAcA!ğ"),
                (self.vPresPart_S, "yAn"),
                (self.vNarrPart_S, "mIş"),
                (self.vSinceDoingSo_S, "yAlI"),
                (self.vByDoingSo_S, "yArAk"),
                (self.vHastily_S, "yIver"),
                (self.vEverSince_S, "yAgör"),
                (self.vAfterDoing_S, "yIp"),
                (self.vWhen_S, "yIncA"),
                (self.vAsLongAs_S, "dIkçA"),
                (self.vNotState_S, "mAzlI~k"),
                (self.vNotState_S, "mAzlI!ğ"),
                (self.vFeelLike_S, "yAsI"),
            ]
        )

        # Negative form is "m" before progressive "Iyor" because last vowel drops.
        # We use a separate negative state for this.
        self.verbRoot_S.add(self.vNegProg1_S, "m")
        self.vNegProg1_S.add(self.vProgYor_S, "Iyor")

        # Negative Aorist
        # Aorist tense forms differently after negative. It can be "z" or empty.
        self.vNeg_S.add(self.vAorNeg_S, "z")
        self.vNeg_S.add_empty(self.vAorNegEmpty_S)
        self.vAorNeg_S.add_all(
            [
                (self.vA2sg_ST, "sIn"),
                (self.vA3sg_ST, ""),
                (self.vA2pl_ST, "sInIz"),
                (self.vA3pl_ST, "lAr"),
                (self.vPastAfterTense_S, "dI"),
                (self.vNarrAfterTense_S, "mIş"),
                (self.vCond_S, "sA"),
                (self.vCopBeforeA3pl_S, "dIr"),
                (self.vWhile_S, "ken"),
            ]
        )

        self.vAorNegEmpty_S.add(self.vA1sg_ST, "m")
        self.vAorNegEmpty_S.add(self.vA1pl_ST, "yIz")
        # oku-maz-ım TODO: not sure here.
        self.vNeg_S.add(self.vAorPartNeg_S, "z")
        self.vAorPartNeg_S.add_empty(self.adjAfterVerb_ST)

        # Positive Ability.
        # This makes a Verb-Verb derivation.
        self.verbRoot_S.add(
            self.vAble_S, "+yAbil", LastDerivationIs(self.vAble_S).not_()
        )

        self.vAble_S.add_empty(self.verbRoot_S)

        # Also for ability that comes before negative, we add a new root state.
        # From there only negative connections is possible.
        self.vAbleNeg_S.add_empty(self.vAbleNegDerivRoot_S)
        self.vAbleNegDerivRoot_S.add(self.vNeg_S, "mA")
        self.vAbleNegDerivRoot_S.add(self.vNegProg1_S, "m")

        # it is possible to have abil derivation after negative.
        self.vNeg_S.add(self.vAble_S, "yAbil")

        # Unable.
        self.verbRoot_S.add(self.vUnable_S, "+yAmA", PreviousMorphemeIs(able).not_())
        # careful here. We copy all outgoing transitions to "unable"
        self.vUnable_S.copy_outgoing_transitions_from(self.vNeg_S)
        self.verbRoot_S.add(self.vUnableProg1_S, "+yAm")
        self.vUnableProg1_S.add(self.vProgYor_S, "Iyor")

        # Infinitive 1 "mAk"
        # Causes Verb to Noun derivation. It is connected to a special noun root state.
        self.verbRoot_S.add(self.vInf1_S, "mA~k")
        self.vInf1_S.add_empty(self.nounInf1Root_S)

        # Infinitive 2 "mA"
        # Causes Verb to Noun derivation.
        self.verbRoot_S.add(self.vInf2_S, "mA")
        self.vInf2_S.add_empty(self.noun_S)

        # Infinitive 3 "+yUş"
        # Causes Verb to Noun derivation.
        self.verbRoot_S.add(self.vInf3_S, "+yIş")
        self.vInf3_S.add_empty(self.noun_S)

        # Agt 3 "+yIcI"
        # Causes Verb to Noun and Adj derivation.
        self.verbRoot_S.add(self.vAgt_S, "+yIcI")
        self.vAgt_S.add_empty(self.noun_S)
        self.vAgt_S.add_empty(self.adjAfterVerb_ST)

        # ActOf "mAcA"
        # Causes Verb to Noun and Adj derivation.
        self.verbRoot_S.add(self.vActOf_S, "mAcA")
        self.vActOf_S.add_empty(self.nounActOfRoot_S)

        # PastPart "oku-duğ-um"
        self.verbRoot_S.add(self.vPastPart_S, ">dI~k")
        self.verbRoot_S.add(self.vPastPart_S, ">dI!ğ")
        self.vPastPart_S.add_empty(self.noun_S)
        self.vPastPart_S.add_empty(self.adjAfterVerb_S)

        # FutPart "oku-yacağ-ım kitap"
        self.verbRoot_S.add(self.vFutPart_S, "+yAcA~k")
        self.verbRoot_S.add(self.vFutPart_S, "+yAcA!ğ")
        self.vFutPart_S.add_empty(self.noun_S, HasTail())
        self.vFutPart_S.add_empty(self.adjAfterVerb_S)

        # FutPart "oku-yacağ-ım kitap"
        self.verbRoot_S.add(self.vNarrPart_S, "mIş")
        self.vNarrPart_S.add_empty(self.adjectiveRoot_ST)

        # AorPart "okunabilir-lik"
        self.verbRoot_S.add(
            self.vAorPart_S,
            "Ir",
            HasRootAttribute(RootAttribute.Aorist_I).or_(HasAnySuffixSurface()),
        )
        self.verbRoot_S.add(
            self.vAorPart_S,
            "Ar",
            HasRootAttribute(RootAttribute.Aorist_A).and_(HasAnySuffixSurface().not_()),
        )
        self.vAorPart_S.add_empty(self.adjAfterVerb_ST)

        # PresPart
        self.verbRoot_S.add(self.vPresPart_S, "+yAn")
        self.vPresPart_S.add_empty(self.noun_S, HasTail())
        self.vPresPart_S.add_empty(self.adjAfterVerb_ST)  # connect to terminal Adj

        # FeelLike
        self.verbRoot_S.add(self.vFeelLike_S, "+yAsI")
        self.vFeelLike_S.add_empty(self.noun_S, HasTail())
        self.vFeelLike_S.add_empty(self.adjAfterVerb_ST)  # connect to terminal Adj

        # NotState
        self.verbRoot_S.add(self.vNotState_S, "mAzlI~k")
        self.verbRoot_S.add(self.vNotState_S, "mAzlI!ğ")
        self.vNotState_S.add_empty(self.noun_S)

        # reciprocal
        # TODO: for reducing ambiguity for now remove reciprocal

        # self.verbRoot_S.add(self.vRecip_S, "Iş", not_haveAny(RootAttribute.Reciprocal, RootAttribute.NonReciprocal)
        #     .and_not(new ContainsMorpheme(recip)))

        self.vRecip_S.add_empty(self.verbRoot_S)
        self.vImplicitRecipRoot_S.add_empty(self.vRecip_S)

        # reflexive
        self.vImplicitReflexRoot_S.add_empty(self.vReflex_S)
        self.vReflex_S.add_empty(self.verbRoot_S)

        # Passive
        # Causes Verb-Verb derivation. Passive morpheme has three forms.
        # 1- If Verb ends with a vowel: "In"
        # 2- If Verb ends with letter 'l' : "InIl"
        # 3- If Verb ends with other consonants: "nIl"
        # When loading dictionary, first and second case items are marked with Passive_In

        self.verbRoot_S.add(
            self.vPass_S,
            "In",
            HasRootAttribute(RootAttribute.Passive_In).and_not(ContainsMorpheme(pass_)),
        )
        self.verbRoot_S.add(
            self.vPass_S,
            "InIl",
            HasRootAttribute(RootAttribute.Passive_In).and_not(ContainsMorpheme(pass_)),
        )
        self.verbRoot_S.add(
            self.vPass_S,
            "+nIl",
            PreviousStateIsAny(self.vCausT_S, self.vCausTir_S)
            .or_(not_have(RootAttribute.Passive_In))
            .and_not(ContainsMorpheme(pass_)),
        )
        self.vPass_S.add_empty(self.verbRoot_S)

        # Condition "oku-r-sa"
        self.vCond_S.add_all(
            [
                (self.vA1sg_ST, "m"),
                (self.vA2sg_ST, "n"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "k"),
                (self.vA2pl_ST, "nIz"),
                (self.vA3pl_ST, "lAr"),
            ]
        )

        # Past "oku-du"
        self.verbRoot_S.add(self.vPast_S, ">dI")
        self.vPast_S.add_all(
            [
                (self.vA1sg_ST, "m"),
                (self.vA2sg_ST, "n"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "k"),
                (self.vA2pl_ST, "nIz"),
                (self.vA3pl_ST, "lAr"),
            ]
        )

        self.vPast_S.add(self.vCond_S, "ysA")

        # Narrative "oku-muş"
        self.verbRoot_S.add(self.vNarr_S, "mIş")
        self.vNarr_S.add_all(
            [
                (self.vA1sg_ST, "Im"),
                (self.vA2sg_ST, "sIn"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "Iz"),
                (self.vA2pl_ST, "sInIz"),
                (self.vA3pl_ST, "lAr"),
            ]
        )

        self.vNarr_S.add(self.vCond_S, "sA")
        self.vNarr_S.add(self.vPastAfterTense_S, "tI")
        self.vNarr_S.add(self.vCopBeforeA3pl_S, "tIr")
        self.vNarr_S.add(self.vWhile_S, "ken")
        self.vNarr_S.add(self.vNarrAfterTense_S, "mIş")

        # Past after tense "oku-muş-tu"
        self.vPastAfterTense_S.add_all(
            [
                (self.vA1sg_ST, "m"),
                (self.vA2sg_ST, "n"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "k"),
                (self.vA2pl_ST, "nIz"),
                (self.vA3pl_ST, "lAr"),
            ]
        )

        # Narrative after tense "oku-r-muş"
        self.vNarrAfterTense_S.add_all(
            [
                (self.vA1sg_ST, "Im"),
                (self.vA2sg_ST, "sIn"),
                # for preventing yap+ar+lar(A3pl)+mış+A3sg
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "Iz"),
                (self.vA2pl_ST, "sInIz"),
                (self.vA3pl_ST, "lAr"),
            ]
        )

        self.vNarrAfterTense_S.add(self.vWhile_S, "ken")
        self.vNarrAfterTense_S.add(self.vCopBeforeA3pl_S, "tIr")

        # Future "oku-yacak"
        self.verbRoot_S.add(self.vFut_S, "+yAcA~k")
        self.verbRoot_S.add(self.vFut_S, "+yAcA!ğ")

        self.vFut_S.add_all(
            [
                (self.vA1sg_ST, "Im"),
                (self.vA2sg_ST, "sIn"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "Iz"),
                (self.vA2pl_ST, "sInIz"),
                (self.vA3pl_ST, "lAr"),
            ]
        )

        self.vFut_S.add(self.vCond_S, "sA")
        self.vFut_S.add(self.vPastAfterTense_S, "tI")
        self.vFut_S.add(self.vNarrAfterTense_S, "mIş")
        self.vFut_S.add(self.vCopBeforeA3pl_S, "tIr")
        self.vFut_S.add(self.vWhile_S, "ken")

        # `demek` and `yemek` are special because they are the only two verbs with two letters
        # and ends with a vowel.
        # Their root transform as:
        # No chabge: de-di, de-miş, de-dir
        # Change : di-yecek di-yor de-r
        # "ye" has similar behavior but not the same. Such as "yi-yin" but for "de", "de-yin"
        # TODO: this can be achieved with less repetition.

        diYiCondition = RootSurfaceIsAny("di", "yi")

        deYeCondition = RootSurfaceIsAny("de", "ye")

        cMultiVerb = PreviousMorphemeIsAny(
            everSince, repeat, almost, hastily, stay, start
        ).not_()

        self.vDeYeRoot_S.add_all(
            [
                (self.vFut_S, "yece~k", diYiCondition),
                (self.vFut_S, "yece!ğ", diYiCondition),
                (self.vProgYor_S, "yor", diYiCondition),
                (self.vAble_S, "yebil", diYiCondition),
                (self.vAbleNeg_S, "ye", diYiCondition),
                (self.vInf3_S, "yiş", RootSurfaceIsAny("yi")),
                (self.vFutPart_S, "yece~k", diYiCondition),
                (self.vFutPart_S, "yece!ğ", diYiCondition),
                (self.vPresPart_S, "yen", diYiCondition),
                (self.vEverSince_S, "yegel", diYiCondition.and_(cMultiVerb)),
                (self.vRepeat_S, "yedur", diYiCondition.and_(cMultiVerb)),
                (self.vRepeat_S, "yegör", diYiCondition.and_(cMultiVerb)),
                (self.vAlmost_S, "yeyaz", diYiCondition.and_(cMultiVerb)),
                (self.vStart_S, "yekoy", diYiCondition.and_(cMultiVerb)),
                (self.vSinceDoingSo_S, "yeli", diYiCondition),
                (self.vByDoingSo_S, "yerek", diYiCondition),
                (self.vFeelLike_S, "yesi", diYiCondition),
                (self.vAfterDoing_S, "yip", diYiCondition),
                (self.vWithoutBeingAbleToHaveDoneSo_S, "yemeden", diYiCondition),
                (self.vOpt_S, "ye", diYiCondition),
            ]
        )

        self.vDeYeRoot_S.add_all(
            [
                (self.vCausTir_S, "dir", deYeCondition),
                (self.vPass_S, "n", deYeCondition),
                (self.vPass_S, "nil", deYeCondition),
                (self.vPast_S, "di", deYeCondition),
                (self.vNarr_S, "miş", deYeCondition),
                (self.vAor_S, "r", deYeCondition),
                (self.vNeg_S, "me", deYeCondition),
                (self.vNegProg1_S, "m", deYeCondition),
                (self.vProgMakta_S, "mekte", deYeCondition),
                (self.vDesr_S, "se", deYeCondition),
                (self.vInf1_S, "mek", deYeCondition),
                (self.vInf2_S, "me", deYeCondition),
                (self.vInf3_S, "yiş", RootSurfaceIsAny("de")),
                (self.vPastPart_S, "di~k", deYeCondition),
                (self.vPastPart_S, "di!ğ", deYeCondition),
                (self.vNarrPart_S, "miş", deYeCondition),
                (self.vHastily_S, "yiver", diYiCondition.and_(cMultiVerb)),
                (self.vAsLongAs_S, "dikçe"),
                (self.vWithoutHavingDoneSo_S, "meden"),
                (self.vWithoutHavingDoneSo_S, "meksizin"),
                (self.vNeces_S, "meli"),
                (self.vNotState_S, "mezli~k"),
                (self.vNotState_S, "mezli!ğ"),
                (self.vImp_S, "", RootSurfaceIs("de")),
                (self.vImpYemekYe_S, "", RootSurfaceIs("ye")),
                (self.vImpYemekYi_S, "", RootSurfaceIs("yi")),
            ]
        )

        # verb `yemek` has an exception case for some imperatives.
        self.vImpYemekYi_S.add_all([(self.vA2pl_ST, "yin"), (self.vA2pl_ST, "yiniz")])

        self.vImpYemekYe_S.add_all(
            [
                (self.vA2sg_ST, ""),
                (self.vA2sg_ST, "sene"),
                (self.vA3sg_ST, "sin"),
                (self.vA2pl_ST, "senize"),
                (self.vA3pl_ST, "sinler"),
            ]
        )

        # Optative (gel-e, gel-eyim gel-me-ye-yim)
        self.verbRoot_S.add(self.vOpt_S, "+yA")
        self.vOpt_S.add_all(
            [
                (self.vA1sg_ST, "yIm"),
                (self.vA2sg_ST, "sIn"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "lIm"),
                (self.vA2pl_ST, "sInIz"),
                (self.vA3pl_ST, "lAr"),
                (self.vPastAfterTense_S, "ydI"),
                (self.vNarrAfterTense_S, "ymIş"),
            ]
        )

        # Desire (gel-se, gel-se-m gel-me-se-m)
        self.verbRoot_S.add(self.vDesr_S, "sA")
        self.vDesr_S.add_all(
            [
                (self.vA1sg_ST, "m"),
                (self.vA2sg_ST, "n"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "k"),
                (self.vA2pl_ST, "nIz"),
                (self.vA3pl_ST, "lAr"),
                (self.vPastAfterTense_S, "ydI"),
                (self.vNarrAfterTense_S, "ymIş"),
            ]
        )

        self.verbRoot_S.add(self.vNeces_S, "mAlI")
        self.vNeces_S.add_all(
            [
                (self.vA1sg_ST, "yIm"),
                (self.vA2sg_ST, "sIn"),
                (self.vA3sg_ST, ""),
                (self.vA1pl_ST, "yIz"),
                (self.vA2pl_ST, "sInIz"),
                (self.vA3pl_ST, "lAr"),
                (self.vPastAfterTense_S, "ydI"),
                (self.vCond_S, "ysA"),
                (self.vNarrAfterTense_S, "ymIş"),
                (self.vCopBeforeA3pl_S, "dIr"),
                (self.vWhile_S, "yken"),
            ]
        )

        # A3pl exception case.
        # A3pl can appear before or after some tense suffixes.
        # "yapar-lar-dı" - "yapar-dı-lar"
        # For preventing "yapar-dı-lar-dı", are added.

        previousNotPastNarrCond = PreviousStateIsAny(
            self.vPastAfterTense_S, self.vNarrAfterTense_S, self.vCond_S
        ).not_()
        self.vA3pl_ST.add(self.vPastAfterTense_ST, "dI", previousNotPastNarrCond)
        self.vA3pl_ST.add(self.vNarrAfterTense_ST, "mIş", previousNotPastNarrCond)
        self.vA3pl_ST.add(self.vCond_ST, "sA", previousNotPastNarrCond)

        a3plCopWhile = PreviousMorphemeIsAny(prog1, prog2, neces, fut, narr, aor)
        self.vA3pl_ST.add(self.vCop_ST, "dIr", a3plCopWhile)
        self.vA3pl_ST.add(self.vWhile_S, "ken", a3plCopWhile)

        a3sgCopWhile = PreviousMorphemeIsAny(prog1, prog2, neces, fut, narr, aor)
        self.vA1sg_ST.add(self.vCop_ST, "dIr", a3sgCopWhile)
        self.vA2sg_ST.add(self.vCop_ST, "dIr", a3sgCopWhile)
        self.vA3sg_ST.add(self.vCop_ST, ">dIr", a3sgCopWhile)
        self.vA1pl_ST.add(self.vCop_ST, "dIr", a3sgCopWhile)
        self.vA2pl_ST.add(self.vCop_ST, "dIr", a3sgCopWhile)

        self.vCopBeforeA3pl_S.add(self.vA3pl_ST, "lAr")

        # Allow Past+A2pl+Cond  Past+A2sg+Cond (geldinse, geldinizse)

        previousPast = PreviousMorphemeIs(past).and_not(ContainsMorpheme(cond, desr))
        self.vA2pl_ST.add(self.vCondAfterPerson_ST, "sA", previousPast)
        self.vA2sg_ST.add(self.vCondAfterPerson_ST, "sA", previousPast)
        self.vA1sg_ST.add(self.vCondAfterPerson_ST, "sA", previousPast)
        self.vA1pl_ST.add(self.vCondAfterPerson_ST, "sA", previousPast)

        self.verbRoot_S.add(self.vEverSince_S, "+yAgel", cMultiVerb)
        self.verbRoot_S.add(self.vRepeat_S, "+yAdur", cMultiVerb)
        self.verbRoot_S.add(self.vRepeat_S, "+yAgör", cMultiVerb)
        self.verbRoot_S.add(self.vAlmost_S, "+yAyaz", cMultiVerb)
        self.verbRoot_S.add(self.vHastily_S, "+yIver", cMultiVerb)
        self.verbRoot_S.add(self.vStay_S, "+yAkal", cMultiVerb)
        self.verbRoot_S.add(self.vStart_S, "+yAkoy", cMultiVerb)

        self.vEverSince_S.add_empty(self.verbRoot_S)
        self.vRepeat_S.add_empty(self.verbRoot_S)
        self.vAlmost_S.add_empty(self.verbRoot_S)
        self.vHastily_S.add_empty(self.verbRoot_S)
        self.vStay_S.add_empty(self.verbRoot_S)
        self.vStart_S.add_empty(self.verbRoot_S)

        self.vA3sg_ST.add(self.vAsIf_S, ">cAsInA", PreviousMorphemeIsAny(aor, narr))

        self.verbRoot_S.add(self.vWhen_S, "+yIncA")
        self.verbRoot_S.add(self.vSinceDoingSo_S, "+yAlI")
        self.verbRoot_S.add(self.vByDoingSo_S, "+yArAk")
        self.verbRoot_S.add(self.vAdamantly_S, "+yAsIyA")
        self.verbRoot_S.add(self.vAfterDoing_S, "+yIp")
        self.verbRoot_S.add(self.vWithoutBeingAbleToHaveDoneSo_S, "+yAmAdAn")
        self.verbRoot_S.add(self.vAsLongAs_S, ">dIkçA")
        self.verbRoot_S.add(self.vWithoutHavingDoneSo_S, "mAdAn")
        self.verbRoot_S.add(self.vWithoutHavingDoneSo_S, "mAksIzIn")

        self.vAsIf_S.add_empty(self.advRoot_ST)
        self.vSinceDoingSo_S.add_empty(self.advRoot_ST)
        self.vByDoingSo_S.add_empty(self.advRoot_ST)
        self.vAdamantly_S.add_empty(self.advRoot_ST)
        self.vAfterDoing_S.add_empty(self.advRoot_ST)
        self.vWithoutBeingAbleToHaveDoneSo_S.add_empty(self.advRoot_ST)
        self.vAsLongAs_S.add_empty(self.advRoot_ST)
        self.vWithoutHavingDoneSo_S.add_empty(self.advRoot_ST)
        self.vWhile_S.add_empty(self.advRoot_ST)
        self.vWhen_S.add_empty(self.advNounRoot_ST)

    def connect_question(self):
        # mı
        self.questionRoot_S.add_empty(self.qPresent_S)
        # mıydı
        self.questionRoot_S.add(self.qPast_S, "ydI")
        # mıymış
        self.questionRoot_S.add(self.qNarr_S, "ymIş")

        # mıyım
        self.qPresent_S.add(self.qA1sg_ST, "yIm")
        # mısın
        self.qPresent_S.add(self.qA2sg_ST, "sIn")
        # mı
        self.qPresent_S.add_empty(self.qA3sg_ST)

        # mıydım
        self.qPast_S.add(self.qA1sg_ST, "m")
        # mıymışım
        self.qNarr_S.add(self.qA1sg_ST, "Im")

        # mıydın
        self.qPast_S.add(self.qA2sg_ST, "n")
        # mıymışsın
        self.qNarr_S.add(self.qA2sg_ST, "sIn")

        # mıydık
        self.qPast_S.add(self.qA1pl_ST, "k")
        # mıymışız
        self.qNarr_S.add(self.qA1pl_ST, "Iz")
        # mıyız
        self.qPresent_S.add(self.qA1pl_ST, "+yIz")

        # mıydınız
        self.qPast_S.add(self.qA2pl_ST, "InIz")
        # mıymışsınız
        self.qNarr_S.add(self.qA2pl_ST, "sInIz")
        # mısınız
        self.qPresent_S.add(self.qA2pl_ST, "sInIz")

        # mıydılar
        self.qPast_S.add(self.qA3pl_ST, "lAr")
        # mıymışlar
        self.qNarr_S.add(self.qA3pl_ST, "lAr")

        # mıydı
        self.qPast_S.add_empty(self.qA3sg_ST)
        # mıymış
        self.qNarr_S.add_empty(self.qA3sg_ST)

        # for not allowing "mı-ydı-m-dır"

        rejectNoCopula = CurrentGroupContainsAny(self.qPast_S).not_()

        # mıyımdır
        self.qA1sg_ST.add(self.qCop_ST, "dIr", rejectNoCopula)
        # mısındır
        self.qA2sg_ST.add(self.qCop_ST, "dIr", rejectNoCopula)
        # mıdır
        self.qA3sg_ST.add(self.qCop_ST, ">dIr", rejectNoCopula)
        # mıyızdır
        self.qA1pl_ST.add(self.qCop_ST, "dIr", rejectNoCopula)
        # mısınızdır
        self.qA2pl_ST.add(self.qCop_ST, "dIr", rejectNoCopula)

        # Copula can come before A3pl.
        self.qPresent_S.add(self.pvCopBeforeA3pl_S, "dIr")
        self.qCopBeforeA3pl_S.add(self.qA3pl_ST, "lAr")

    def connect_imek(self):
        # idi
        self.imekRoot_S.add(self.imekPast_S, "di")
        # imiş
        self.imekRoot_S.add(self.imekNarr_S, "miş")
        # ise
        self.imekRoot_S.add(self.imekCond_S, "se")

        # idim, idin, idi, idik, idiniz, idiler
        self.imekPast_S.add(self.imekA1sg_ST, "m")
        self.imekPast_S.add(self.imekA2sg_ST, "n")
        self.imekPast_S.add_empty(self.imekA3sg_ST)
        self.imekPast_S.add(self.imekA1pl_ST, "k")
        self.imekPast_S.add(self.imekA2pl_ST, "niz")
        self.imekPast_S.add(self.imekA3pl_ST, "ler")

        # imişim, imişsin, imiş, imişiz, imişsiniz, imişler
        self.imekNarr_S.add(self.imekA1sg_ST, "im")
        self.imekNarr_S.add(self.imekA2sg_ST, "sin")
        self.imekNarr_S.add_empty(self.imekA3sg_ST)
        self.imekNarr_S.add(self.imekA1pl_ST, "iz")
        self.imekNarr_S.add(self.imekA2pl_ST, "siniz")
        self.imekNarr_S.add(self.imekA3pl_ST, "ler")

        self.imekPast_S.add(self.imekCond_S, "yse")
        self.imekNarr_S.add(self.imekCond_S, "se")

        self.imekCond_S.add(self.imekA1sg_ST, "m")
        self.imekCond_S.add(self.imekA2sg_ST, "n")
        self.imekCond_S.add_empty(self.imekA3sg_ST)
        self.imekCond_S.add(self.imekA1pl_ST, "k")
        self.imekCond_S.add(self.imekA2pl_ST, "niz")
        self.imekCond_S.add(self.imekA3pl_ST, "ler")

        # for not allowing "i-di-m-dir"

        rejectNoCopula = CurrentGroupContainsAny(self.imekPast_S).not_()

        # imişimdir, imişsindir etc.
        self.imekA1sg_ST.add(self.imekCop_ST, "dir", rejectNoCopula)
        self.imekA2sg_ST.add(self.imekCop_ST, "dir", rejectNoCopula)
        self.imekA3sg_ST.add(self.imekCop_ST, "tir", rejectNoCopula)
        self.imekA1pl_ST.add(self.imekCop_ST, "dir", rejectNoCopula)
        self.imekA2pl_ST.add(self.imekCop_ST, "dir", rejectNoCopula)
        self.imekA3pl_ST.add(self.imekCop_ST, "dir", rejectNoCopula)

    def handle_post_processing_connections(self):
        # Passive has an exception for some verbs like `kavurmak` or `savurmak`.
        # add passive state connection to modified root `kavr` etc.
        self.verbLastVowelDropModRoot_S.add(self.vPass_S, "Il")
        # for not allowing `kavur-ul` add all verb connections to
        # unmodified `kavur` root and remove only the passive.
        self.verbLastVowelDropUnmodRoot_S.copy_outgoing_transitions_from(
            self.verbRoot_S
        )
        self.verbLastVowelDropUnmodRoot_S.remove_transitions_to(pass_)

    def get_root_state(
        self, dict_item: DictionaryItem, attrs: "set[PhoneticAttribute] | None" = None
    ):
        root_ = self.item_root_states.get(dict_item.id_)
        attrs = (
            attrs.copy()
            if attrs is not None
            else calculate_phonetic_attributes(dict_item.pronunciation)
        )
        if root_ is not None:
            return root_
        # Verbs like "aramak" drops their last vowel when  connected to "Iyor" Progressive suffix.
        # those modified roots are connected to a separate root state called self.verbRoot_VowelDrop_S.
        if PhoneticAttribute.LastLetterDropped in attrs:
            return self.verbRoot_VowelDrop_S
        if dict_item.has_attribute(RootAttribute.Reciprocal):
            return self.vImplicitRecipRoot_S
        if dict_item.has_attribute(RootAttribute.Reflexive):
            return self.vImplicitReflexRoot_S
        if dict_item.primary_pos == PrimaryPos.Noun:
            if dict_item.secondary_pos == SecondaryPos.ProperNoun:
                return self.nounProper_S
            elif dict_item.secondary_pos == SecondaryPos.Abbreviation:
                return self.nounAbbrv_S
            elif dict_item.secondary_pos in [
                SecondaryPos.Email,
                SecondaryPos.Url,
                SecondaryPos.HashTag,
                SecondaryPos.Mention,
            ]:
                return self.nounProper_S
            elif dict_item.secondary_pos in [
                SecondaryPos.Emoticon,
                SecondaryPos.RomanNumeral,
            ]:
                return self.nounNoSuffix_S
            if dict_item.has_attribute(RootAttribute.CompoundP3sgRoot):
                return self.nounCompoundRoot_S
            else:
                return self.noun_S
        elif dict_item.primary_pos == PrimaryPos.Adjective:
            return self.adjectiveRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Pronoun:
            if dict_item.secondary_pos == SecondaryPos.PersonalPron:
                return self.pronPers_S
            if dict_item.secondary_pos == SecondaryPos.DemonstrativePron:
                return self.pronDemons_S
            elif dict_item.secondary_pos == SecondaryPos.QuantitivePron:
                return self.pronQuant_S
            elif dict_item.secondary_pos == SecondaryPos.QuestionPron:
                return self.pronQues_S
            elif dict_item.secondary_pos == SecondaryPos.ReflexivePron:
                return self.pronReflex_S
            else:
                return self.pronQuant_S
        elif dict_item.primary_pos == PrimaryPos.Adverb:
            return self.advRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Conjunction:
            return self.conjRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Question:
            return self.questionRoot_S
        elif dict_item.primary_pos == PrimaryPos.Interjection:
            return self.interjRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Verb:
            return self.verbRoot_S
        elif dict_item.primary_pos == PrimaryPos.Punctuation:
            return self.puncRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Determiner:
            return self.detRoot_ST
        elif dict_item.primary_pos == PrimaryPos.PostPositive:
            return self.postpRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Numeral:
            return self.numeralRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Duplicator:
            return self.dupRoot_ST
        else:
            return self.noun_S


class MorphemeTransition:
    """
    Represents a transition in morphotactics graph.
    :param condition: Defines the condition(s) to allow or block a graph visitor (SearchPath).
    A condition can be a single or a group of objects that has Condition interface.
    For example, if condition is HasPhoneticAttribute(LastLetterVowel), and SearchPath's last
    letter is a consonant, it cannot pass this transition.
    """

    def __init__(
        self,
        from_: MorphemeState,
        to_: MorphemeState,
        condition: "Condition | None" = None,
    ):
        self.from_ = from_
        self.to_ = to_
        self.condition = condition

    def __repr__(self):
        return f"MorphemeTransition ({self.from_.id_})-({self.to_.id_})({self.condition if self.condition else ''})"

    @property
    def condition_count(self):
        if self.condition is None:
            return 0
        else:
            return len(self.condition)


class StemTransition(MorphemeTransition):
    def __init__(
        self,
        dict_item: DictionaryItem,
        to_: MorphemeState,
        attrs: "set[PhoneticAttribute] | None" = None,
        surface: "str | None" = None,
    ):
        super().__init__(root_S, to_, None)
        if surface:
            if tr.is_upper(surface[0]):
                print(
                    f"Something wrong, generating StemTransition capitalized: {surface}"
                )
        else:
            if tr.is_upper(dict_item.root[0]):
                print(
                    f"Something ELSE is wrong: generating StemTransition capitalized from dictitem: {dict_item.root}"
                )
        self.surface = surface if surface is not None else dict_item.root
        self.dict_item = dict_item
        self.attrs = (
            calculate_phonetic_attributes(dict_item.pronunciation)
            if attrs is None
            else attrs.copy()
        )

    def __str__(self):
        return f"<(Dict: {self.dict_item}):{self.surface} → {self.to_}>"

    def __repr__(self):
        return f"StemTransition({self.dict_item.id_}): {self.surface}→{self.to_.id_}"

    def __eq__(self, other):
        return (
            self.surface == other.surface
            and self.attrs == other.attrs
            and self.dict_item == other.dict_item
        )

    def __hash__(self):
        return hash((self.surface, self.dict_item, frozenset(self.attrs)))


class SuffixTransition(MorphemeTransition):
    """
    :param surface_template: this string represents the possible surface forms for this transition.
    """

    def __init__(
        self,
        from_: MorphemeState,
        to_: MorphemeState,
        surface_template: str = "",
        condition: "Condition | None" = None,
    ):
        if from_ is None or to_ is None:
            raise ValueError("Suffix transition cannot have empty from and to points")
        super().__init__(from_, to_, condition)
        self.surface_template = surface_template
        self.condition = condition
        self.parse_conditions_from_template()
        self.token_list = list(SuffixTemplateTokenizer(self.surface_template))

    def __str__(self):
        template_str = f":{self.surface_template}" if self.surface_template else ""
        return f"<{self.from_.id_}→{self.to_.id_}{template_str}>"

    def __repr__(self):
        return f"SuffixTransition({self.from_.id_}, {self.to_.id_}, '{self.surface_template}', {self.condition})"

    def __eq__(self, other):
        return (
            self.to_.id_ == other.to_.id_
            and self.surface_template == other.surface_template
            and self.from_.id_ == other.from_.id_
        )

    def __hash__(self):
        return hash((self.from_.id_, self.to_.id_, self.surface_template))

    def can_pass(self, path: "SearchPath") -> bool:
        return self.condition is None or self.condition.accept(path)

    def connect(self):
        self.from_.add_outgoing([self])
        self.to_.add_incoming([self])

    # adds vowel-consonant expectation related automatically.
    # TODO: consider moving this to morphotactics somehow.
    def parse_conditions_from_template(self):
        if not self.surface_template:
            return
        lower = tr.lower(self.surface_template)
        c = None
        first_char_is_vowel = tr.is_vowel(lower[0])
        if lower.startswith(">") or not first_char_is_vowel:
            c = not_have(PhoneticAttribute.ExpectsVowel)

        if (
            lower.startswith("+") and len(lower) > 2 and tr.is_vowel(lower[2])
        ) or first_char_is_vowel:
            c = not_have(PhoneticAttribute.ExpectsConsonant)

        if c is not None:
            if self.condition is None:
                self.condition = c
            else:
                self.condition = c.and_(self.condition)

    def get_copy(self):
        return SuffixTransition(
            self.from_, self.to_, self.surface_template, self.condition
        )

    @property
    def has_surface_form(self):
        return len(self.token_list) > 0

    @property
    def last_template_token(self):
        if len(self.token_list) == 0:
            return None
        else:
            return self.token_list[-1]


class SurfaceTransition:
    def __init__(self, surface: str, lexical_transition):
        self.surface = surface
        self.lexical_transition = lexical_transition

    @property
    def is_derivative(self):
        return self.lexical_transition.to_.derivative

    @property
    def state(self):
        return self.lexical_transition.to_

    @property
    def morpheme(self):
        return self.lexical_transition.to_.morpheme

    @property
    def is_derivational_or_root(self):
        return self.state.derivative or self.state.pos_root

    def __str__(self):
        return f"{self.surface_string}{self.state.id_}"

    def to_morpheme_str(self):
        return f"{self.surface_string}{self.state.morpheme.id_}"

    @property
    def surface_string(self):
        return f"{self.surface}:" if self.surface else ""

    def __repr__(self):
        return str(self)


def generate_surface(
    transition: SuffixTransition, phonetic_attributes: set[PhoneticAttribute]
) -> str:
    root_attributes = phonetic_attributes
    root_attributes_key = None
    suffix_has_vowel = False
    index = 0
    result = []
    for token in transition.token_list:
        if suffix_has_vowel and token.type_ in ("A_VOWEL", "I_VOWEL"):
            root_attributes_key = root_attributes_key or frozenset(root_attributes)
            phonetic_attributes = _cached_phonetic_attributes(
                "".join(result), root_attributes_key
            )
        if token.type_ == "LETTER":
            result.append(token.letter)
        elif token.type_ == "A_VOWEL":
            if index == 0 and PhoneticAttribute.LastLetterVowel in phonetic_attributes:
                continue
            if PhoneticAttribute.LastVowelBack in phonetic_attributes:
                result.append("a")
            elif PhoneticAttribute.LastVowelFrontal in phonetic_attributes:
                result.append("e")
            else:
                raise ValueError(f"Cannot generate A form from {phonetic_attributes}")
        elif token.type_ == "I_VOWEL":
            if index == 0 and PhoneticAttribute.LastLetterVowel in phonetic_attributes:
                continue
            elif PhoneticAttribute.LastVowelFrontal in phonetic_attributes:
                if PhoneticAttribute.LastVowelUnrounded in phonetic_attributes:
                    result.append("i")
                else:
                    result.append("ü")
            elif PhoneticAttribute.LastVowelBack in phonetic_attributes:
                if PhoneticAttribute.LastVowelUnrounded in phonetic_attributes:
                    result.append("ı")
                else:
                    result.append("u")
            else:
                raise ValueError(f"Cannot generate I form from {phonetic_attributes}")
        elif token.type_ == "APPEND":
            if PhoneticAttribute.LastLetterVowel in phonetic_attributes:
                result.append(token.letter)
        elif token.type_ == "DEVOICE_FIRST":
            ld = token.letter
            if PhoneticAttribute.LastLetterVoiceless in phonetic_attributes:
                ld = tr.devoice(ld)
            result.append(ld)
        elif token.type_ in ["LAST_VOICED", "LAST_NOT_VOICED"]:
            ld = token.letter
            result.append(ld)
        suffix_has_vowel = suffix_has_vowel or (
            bool(result) and result[-1] in tr.vowels_lower_set
        )
        index += 1
    return "".join(result)


class SuffixTemplateToken:
    def __init__(self, type_: str, letter: str, append=False):
        self.type_ = type_
        self.letter = letter
        self.append = append

    def __str__(self):
        return f"({self.type_}:{self.letter})"

    def __repr__(self):
        return str(self)


class SuffixTemplateTokenizer:
    def __init__(self, word: str):
        self.word = word
        self.pointer = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.word is None or self.pointer >= len(self.word):
            raise StopIteration
        c = self.word[self.pointer]
        c_next = 0
        self.pointer += 1
        if self.pointer < len(self.word):
            c_next = self.word[self.pointer]
        undefined = chr(0)
        if c == "+":
            self.pointer += 1
            if c_next == "I":
                return SuffixTemplateToken("I_VOWEL", undefined, True)
            elif c_next == "A":
                return SuffixTemplateToken("A_VOWEL", undefined, True)
            else:
                return SuffixTemplateToken("APPEND", c_next)
        elif c == ">":
            self.pointer += 1
            return SuffixTemplateToken("DEVOICE_FIRST", c_next)
        elif c == "~":
            self.pointer += 1
            return SuffixTemplateToken("LAST_VOICED", c_next)
        elif c == "!":
            self.pointer += 1
            return SuffixTemplateToken("LAST_NOT_VOICED", c_next)
        elif c == "I":
            return SuffixTemplateToken("I_VOWEL", undefined)
        elif c == "A":
            return SuffixTemplateToken("A_VOWEL", undefined)
        else:
            return SuffixTemplateToken("LETTER", c)


class SearchPath:
    """
    This class represents a path in morphotactics graph. During analysis many SearchPaths are created
    and surviving paths are used for generating analysis results.
    :param tail: letters left to parse
    """

    def __init__(
        self,
        tail: str,
        current_state: MorphemeState,
        transitions: list[SurfaceTransition],
        phonetic_attributes: set[PhoneticAttribute],
        terminal: bool,
    ):
        self.tail = tail
        self.current_state = current_state
        self.transitions = transitions
        self.phonetic_attributes = phonetic_attributes
        self.terminal = terminal
        self.contains_derivation = False
        self.contains_suffix_with_surface = False

    @classmethod
    def initial(cls, stem_transition: StemTransition, tail: str) -> "SearchPath":
        morphemes_ = []
        root_ = SurfaceTransition(stem_transition.surface, stem_transition)
        morphemes_.append(root_)
        return cls(
            tail,
            stem_transition.to_,
            morphemes_,
            set(stem_transition.attrs),
            stem_transition.to_.terminal,
        )

    def __str__(self):
        st = self.stem_transition
        morpheme_str = " + ".join([str(tran) for tran in self.transitions])
        return f"<({st.dict_item.id_})(-{self.tail})({morpheme_str})>"

    def __repr__(self):
        return f"SearchPath({self.dict_item.id_}) (-{self.tail})({self.transitions})"

    def copy(
        self,
        surface_node: SurfaceTransition,
        pa: "set[PhoneticAttribute] | None" = None,
    ) -> "SearchPath":
        phonetic_attributes = (
            calculate_phonetic_attributes(
                surface_node.surface, tuple(self.phonetic_attributes)
            )
            if pa is None
            else pa
        )
        is_terminal = surface_node.state.terminal
        hist = self.transitions[:]
        hist.append(surface_node)
        new_tail = self.tail[len(surface_node.surface) :]
        path = SearchPath(
            new_tail, surface_node.state, hist, phonetic_attributes.copy(), is_terminal
        )
        path.contains_suffix_with_surface = (
            self.contains_suffix_with_surface or len(surface_node.surface) > 0
        )
        path.contains_derivation = (
            self.contains_derivation or surface_node.state.derivative
        )
        return path

    @property
    def stem_transition(self) -> StemTransition:
        return self.transitions[0].lexical_transition

    @property
    def previous_state(self) -> "MorphemeState | None":
        if len(self.transitions) < 2:
            return None
        return self.transitions[-2].state

    @property
    def is_terminal(self) -> bool:
        return self.terminal

    def has_dictionary_item(self, dict_item: DictionaryItem) -> bool:
        return self.stem_transition.dict_item == dict_item

    @property
    def last_transition(self) -> SurfaceTransition:
        return self.transitions[-1]

    @property
    def dict_item(self) -> DictionaryItem:
        return self.stem_transition.dict_item
