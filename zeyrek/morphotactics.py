import sys, os
from typing import List, Set, NamedTuple, Optional

# sys.path.pop(0)
# print(sys.path)
# print(os.path.dirname(__file__))

from zeyrek import tr
from zeyrek.attributes import (
    PrimaryPos,
    PhoneticAttribute,
    RootAttribute,
    SecondaryPos,
    calculate_phonetic_attributes,
)
from zeyrek.conditions import (
    Condition,
    not_have,
    has,
    ContainsMorpheme,
    NotCondition,
    SecondaryPosIs,
    PreviousGroupContainsMorpheme,
    ContainsMorphemeSequence,
    NoSurfaceAfterDerivation,
    HasTailSequence,
    LastDerivationIs,
    PreviousMorphemeIs,
    DictionaryItemIs,
    PreviousMorphemeIsAny,
    CurrentGroupContainsAny,
    PreviousGroupContains,
    PreviousStateIsAny,
    RootSurfaceIsAny,
    RootSurfaceIs,
    LastDerivationIsAny,
    PreviousStateIs,
    HasRootAttribute,
    DictionaryItemIsAny,
    HasPhoneticAttribute,
    HasTail,
    HasAnySuffixSurface,
    PreviousStateIsNot,
)
from zeyrek.lexicon import DictionaryItem, RootLexicon


class Morpheme(NamedTuple):
    name: str
    id_: str
    pos: Optional[PrimaryPos]
    derivational: bool = False
    informal: bool = False

    def __eq__(self, other):
        return self.id_ == other.id_


class MorphemeState:
    def __init__(self, id_, morpheme, terminal=False, derivative=False, pos_root=False):
        self.id_ = id_
        self.morpheme = morpheme
        self.terminal = terminal
        self.derivative = derivative
        self.pos_root = pos_root
        self.outgoing = []
        self.incoming = []

    def __str__(self):
        return f"[{self.id_}:{self.morpheme.id_}]"

    def __repr__(self):
        return f"MorphemeState({self.id_}, {self.morpheme.id_})"

    def add_outgoing(self, *suffix_transitions):
        for transition in suffix_transitions:
            if transition in self.outgoing:
                # Outgoing transition {transition} already exists in {self}")
                continue

            self.outgoing.append(transition)
        return self

    def add_incoming(self, suffix_transitions):
        for transition in suffix_transitions:
            if transition in self.incoming:
                print(f"Incoming transition {transition} already exists in {self}")
                continue
            self.incoming.append(transition)
        return self

    def add(self, to_, template, condition=None):
        transition = SuffixTransition(self, to_, template, condition)
        self.add_outgoing(transition)  # type: SuffixTransition
        return self

    def add_all(self, transitions):
        for transition in transitions:
            self.add(*transition)

    def add_empty(self, to_, condition=None):
        transition = SuffixTransition(self, to_, "", condition)
        self.add_outgoing(transition)
        return self

    def copy_outgoing_transitions_from(self, state):
        for transition in state.outgoing:
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


morphemes = {}


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

# MorphemeState = namedtuple("MorphemeState", "id morpheme terminal derivative posRoot")

# -------------- States ----------------------------
# _ST = Terminal state _S = Non Terminal State.
# A terminal state means that a walk in the graph can end there.

# root of the graph.
root_S = MorphemeState("root_S", root, False, False, False)
puncRoot_ST = MorphemeState("puncRoot_ST", punc, True, False, True)

# -------------- Noun States ------------------------

noun_S = MorphemeState("noun_S", noun, False, False, True)
nounCompoundRoot_S = MorphemeState("nounCompoundRoot_S", noun, False, False, True)
nounSuRoot_S = MorphemeState("nounSuRoot_S", noun, False, False, True)
nounInf1Root_S = MorphemeState("nounInf1Root_S", noun, False, False, True)
nounActOfRoot_S = MorphemeState("nounActOfRoot_S", noun, False, False, True)

# Number-Person agreement

a3sg_S = MorphemeState("a3sg_S", a3sg, False, False, False)
a3sgSu_S = MorphemeState("a3sgSu_S", a3sg, False, False, False)
a3sgCompound_S = MorphemeState("a3sgCompound_S", a3sg, False, False, False)
a3sgInf1_S = MorphemeState("a3sgInf1_S", a3sg, False, False, False)
a3sgActOf_S = MorphemeState("a3sgActOf_S", a3sg, False, False, False)
a3pl_S = MorphemeState("a3pl_S", a3pl, False, False, False)
a3plActOf_S = MorphemeState("a3plActOf_S", a3pl, False, False, False)
a3plCompound_S = MorphemeState("a3plCompound_S", a3pl, False, False, False)
a3plCompound2_S = MorphemeState("a3plCompound2_S", a3pl, False, False, False)

# Possessive

pnon_S = MorphemeState("pnon_S", pnon, False, False, False)
pnonCompound_S = MorphemeState("pnonCompound_S", pnon, False, False, False)
pnonCompound2_S = MorphemeState("pnonCompound2_S", pnon, False, False, False)
pnonInf1_S = MorphemeState("pnonInf1_S", pnon, False, False, False)
pnonActOf = MorphemeState("pnonActOf", pnon, False, False, False)
p1sg_S = MorphemeState("p1sg_S", p1sg, False, False, False)
p2sg_S = MorphemeState("p2sg_S", p2sg, False, False, False)
p3sg_S = MorphemeState("p3sg_S", p3sg, False, False, False)
p1pl_S = MorphemeState("p1pl_S", p1pl, False, False, False)
p2pl_S = MorphemeState("p2pl_S", p2pl, False, False, False)
p3pl_S = MorphemeState("p3pl_S", p3pl, False, False, False)

# Case

nom_ST = MorphemeState("nom_ST", nom, True, False, False)
nom_S = MorphemeState("nom_S", nom, False, False, False)

dat_ST = MorphemeState("dat_ST", dat, True, False, False)
abl_ST = MorphemeState("abl_ST", abl, True, False, False)
loc_ST = MorphemeState("loc_ST", loc, True, False, False)
ins_ST = MorphemeState("ins_ST", ins, True, False, False)
acc_ST = MorphemeState("acc_ST", acc, True, False, False)
gen_ST = MorphemeState("gen_ST", gen, True, False, False)
equ_ST = MorphemeState("equ_ST", equ, True, False, False)

# MorphemeState = namedtuple("MorphemeState", "id morpheme terminal derivative posRoot")

# Derivation

dim_S = MorphemeState("dim_S", dim, False, True, False)
ness_S = MorphemeState("ness_S", ness, False, True, False)
agt_S = MorphemeState("agt_S", agt, False, True, False)
related_S = MorphemeState("related_S", related, False, True, False)
rel_S = MorphemeState("rel_S", rel, False, True, False)
relToPron_S = MorphemeState("relToPron_S", rel, False, True, False)
with_S = MorphemeState("with_S", with_, False, True, False)
without_S = MorphemeState("without_S", without, False, True, False)
justLike_S = MorphemeState("justLike_S", justLike, False, True, False)
nounZeroDeriv_S = MorphemeState("nounZeroDeriv_S", zero, False, True, False)
become_S = MorphemeState("become_S", become, False, True, False)
acquire_S = MorphemeState("acquire_S", acquire, False, True, False)

# MorphemeState = namedtuple("MorphemeState", "id morpheme terminal derivative posRoot")


# -------- Morphotactics for modified forms of words like "içeri->içerde"
nounLastVowelDropRoot_S = MorphemeState(
    "nounLastVowelDropRoot_S", noun, False, False, True
)
adjLastVowelDropRoot_S = MorphemeState(
    "adjLastVowelDropRoot_S", adj, False, False, True
)
postpLastVowelDropRoot_S = MorphemeState(
    "postpLastVowelDropRoot_S", postp, False, False, True
)
a3PlLastVowelDrop_S = MorphemeState("a3PlLastVowelDrop_S", a3pl, False, False, False)
a3sgLastVowelDrop_S = MorphemeState("a3sgLastVowelDrop_S", a3sg, False, False, False)
pNonLastVowelDrop_S = MorphemeState("pNonLastVowelDrop_S", pnon, False, False, False)
zeroLastVowelDrop_S = MorphemeState("zeroLastVowelDrop_S", zero, False, True, False)
# MorphemeState = namedtuple("MorphemeState", "id morpheme terminal derivative posRoot")

nounProper_S = MorphemeState("nounProper_S", noun, False, False, True)
nounAbbrv_S = MorphemeState("nounAbbrv_S", noun, False, False, True)
# this will be used for proper noun separation.
puncProperSeparator_S = MorphemeState(
    "puncProperSeparator_S", punc, False, False, False
)

nounNoSuffix_S = MorphemeState("nounNoSuffix_S", noun, False, False, True)
nounA3sgNoSuffix_S = MorphemeState("nounA3sgNoSuffix_S", a3sg, False, False, False)
nounPnonNoSuffix_S = MorphemeState("nounPnonNoSuffix_S", pnon, False, False, False)
nounNomNoSuffix_ST = MorphemeState("nounNomNoSuffix_S", nom, True, False, False)

# -------------- Adjective States ------------------------

adjectiveRoot_ST = MorphemeState("adjectiveRoot_ST", adj, True, False, True)
adjAfterVerb_S = MorphemeState("adjAfterVerb_S", adj, False, False, True)
adjAfterVerb_ST = MorphemeState("adjAfterVerb_ST", adj, True, False, True)

adjZeroDeriv_S = MorphemeState("adjZeroDeriv_S", zero, False, True, False)

# After verb->adj derivations Adj can get possesive suffixes.
# Such as "oku-duğ-um", "okuyacağı"
aPnon_ST = MorphemeState("aPnon_ST", pnon, True, False, False)
aP1sg_ST = MorphemeState("aP1sg_ST", p1sg, True, False, False)
aP2sg_ST = MorphemeState("aP2sg_ST", p2sg, True, False, False)
aP3sg_ST = MorphemeState("aP3sg_ST", p3sg, True, False, False)
aP1pl_ST = MorphemeState("aP3sg_ST", p1pl, True, False, False)
aP2pl_ST = MorphemeState("aP2pl_ST", p2pl, True, False, False)
aP3pl_ST = MorphemeState("aP3pl_ST", p3pl, True, False, False)

aLy_S = MorphemeState("aLy_S", ly, False, True, False)
aAsIf_S = MorphemeState("aAsIf_S", asIf, False, True, False)
aAgt_S = MorphemeState("aAgt_S", agt, False, True, False)

# --------------------- Numeral Root --------------------------------------------------
numeralRoot_ST = MorphemeState("numeralRoot_ST", num, True, False, True)
numZeroDeriv_S = MorphemeState("numZeroDeriv_S", zero, False, True, False)

# -------------- Adjective-Noun connected Verb States ------------------------

nVerb_S = MorphemeState("nVerb_S", verb, False, False, True)
nVerbDegil_S = MorphemeState("nVerbDegil_S", verb, False, False, True)

nPresent_S = MorphemeState("nPresent_S", pres, False, False, False)
nPast_S = MorphemeState("nPast_S", past, False, False, False)
nNarr_S = MorphemeState("nNarr_S", narr, False, False, False)
nCond_S = MorphemeState("nCond_S", cond, False, False, False)
nA1sg_ST = MorphemeState("nA1sg_ST", a1sg, True, False, False)
nA2sg_ST = MorphemeState("nA2sg_ST", a2sg, True, False, False)
nA1pl_ST = MorphemeState("nA1pl_ST", a1pl, True, False, False)
nA2pl_ST = MorphemeState("nA2pl_ST", a2pl, True, False, False)
nA3sg_ST = MorphemeState("nA3sg_ST", a3sg, True, False, False)
nA3sg_S = MorphemeState("nA3sg_S", a3sg, False, False, False)
nA3pl_ST = MorphemeState("nA3pl_ST", a3pl, True, False, False)

nCop_ST = MorphemeState("nCop_ST", cop, True, False, False)
nCopBeforeA3pl_S = MorphemeState("nCopBeforeA3pl_S", cop, False, False, False)

nNeg_S = MorphemeState("nNeg_S", neg, False, False, False)

# ----------- Pronoun states --------------------------

# Pronouns have states similar with Nouns.
pronPers_S = MorphemeState("pronPers_S", pron, False, False, True)

pronDemons_S = MorphemeState("pronDemons_S", pron, False, False, True)
pronQuant_S = MorphemeState("pronQuant_S", pron, False, False, True)
pronQuantModified_S = MorphemeState("pronQuantModified_S", pron, False, False, True)
pronQues_S = MorphemeState("pronQues_S", pron, False, False, True)
pronReflex_S = MorphemeState("pronReflex_S", pron, False, False, True)

# used for ben-sen modification
pronPers_Mod_S = MorphemeState("pronPers_Mod_S", pron, False, False, True)
# A root for noun->Rel->Pron derivation.
pronAfterRel_S = MorphemeState("pronAfterRel_S", pron, False, False, True)

pA1sg_S = MorphemeState("pA1sg_S", a1sg, False, False, False)
pA2sg_S = MorphemeState("pA2sg_S", a2sg, False, False, False)

pA1sgMod_S = MorphemeState("pA1sgMod_S", a1sg, False, False, False)  # for modified ben
pA2sgMod_S = MorphemeState("pA2sgMod_S", a2sg, False, False, False)  # for modified sen

pA3sg_S = MorphemeState("pA3sg_S", a3sg, False, False, False)
pA3sgRel_S = MorphemeState("pA3sgRel_S", a3sg, False, False, False)
pA1pl_S = MorphemeState("pA1pl_S", a1pl, False, False, False)
pA2pl_S = MorphemeState("pA2pl_S", a2pl, False, False, False)

pA3pl_S = MorphemeState("pA3pl_S", a3pl, False, False, False)
pA3plRel_S = MorphemeState("pA3plRel_S", a3pl, False, False, False)

pQuantA3sg_S = MorphemeState("pQuantA3sg_S", a3sg, False, False, False)
pQuantA3pl_S = MorphemeState("pQuantA3pl_S", a3pl, False, False, False)
pQuantModA3pl_S = MorphemeState(
    "pQuantModA3pl_S", a3pl, False, False, False
)  # for birbirleri etc.
pQuantA1pl_S = MorphemeState("pQuantA1pl_S", a1pl, False, False, False)
pQuantA2pl_S = MorphemeState("pQuantA2pl_S", a2pl, False, False, False)

pQuesA3sg_S = MorphemeState("pQuesA3sg_S", a3sg, False, False, False)
pQuesA3pl_S = MorphemeState("pQuesA3pl_S", a3pl, False, False, False)

pReflexA3sg_S = MorphemeState("pReflexA3sg_S", a3sg, False, False, False)
pReflexA3pl_S = MorphemeState("pReflexA3pl_S", a3pl, False, False, False)
pReflexA1sg_S = MorphemeState("pReflexA1sg_S", a1sg, False, False, False)
pReflexA2sg_S = MorphemeState("pReflexA2sg_S", a2sg, False, False, False)
pReflexA1pl_S = MorphemeState("pReflexA1pl_S", a1pl, False, False, False)
pReflexA2pl_S = MorphemeState("pReflexA2pl_S", a2pl, False, False, False)

# Possessive

pPnon_S = MorphemeState("pPnon_S", pnon, False, False, False)
pPnonRel_S = MorphemeState("pPnonRel_S", pnon, False, False, False)
pPnonMod_S = MorphemeState(
    "pPnonMod_S", pnon, False, False, False
)  # for modified ben-sen
pP1sg_S = MorphemeState("pP1sg_S", p1sg, False, False, False)  # kimim
pP2sg_S = MorphemeState("pP2sg_S", p2sg, False, False, False)
pP3sg_S = MorphemeState("pP3sg_S", p3sg, False, False, False)  # for `birisi` etc
pP1pl_S = MorphemeState("pP1pl_S", p1pl, False, False, False)  # for `birbirimiz` etc
pP2pl_S = MorphemeState("pP2pl_S", p2pl, False, False, False)  # for `birbiriniz` etc
pP3pl_S = MorphemeState("pP3pl_S", p3pl, False, False, False)  # for `birileri` etc

# Case

pNom_ST = MorphemeState("pNom_ST", nom, True, False, False)
pDat_ST = MorphemeState("pDat_ST", dat, True, False, False)
pAcc_ST = MorphemeState("pAcc_ST", acc, True, False, False)
pAbl_ST = MorphemeState("pAbl_ST", abl, True, False, False)
pLoc_ST = MorphemeState("pLoc_ST", loc, True, False, False)
pGen_ST = MorphemeState("pGen_ST", gen, True, False, False)
pIns_ST = MorphemeState("pIns_ST", ins, True, False, False)
pEqu_ST = MorphemeState("pEqu_ST", equ, True, False, False)

pronZeroDeriv_S = MorphemeState("pronZeroDeriv_S", zero, False, True, False)

pvPresent_S = MorphemeState("pvPresent_S", pres, False, False, False)
pvPast_S = MorphemeState("pvPast_S", past, False, False, False)
pvNarr_S = MorphemeState("pvNarr_S", narr, False, False, False)
pvCond_S = MorphemeState("pvCond_S", cond, False, False, False)
pvA1sg_ST = MorphemeState("pvA1sg_ST", a1sg, True, False, False)
pvA2sg_ST = MorphemeState("pvA2sg_ST", a2sg, True, False, False)
pvA3sg_ST = MorphemeState("pvA3sg_ST", a3sg, True, False, False)
pvA3sg_S = MorphemeState("pvA3sg_S", a3sg, False, False, False)
pvA1pl_ST = MorphemeState("pvA1pl_ST", a1pl, True, False, False)
pvA2pl_ST = MorphemeState("pvA2pl_ST", a2pl, True, False, False)
pvA3pl_ST = MorphemeState("pvA3pl_ST", a3pl, True, False, False)

pvCopBeforeA3pl_S = MorphemeState("pvCopBeforeA3pl_S", cop, False, False, False)
pvCop_ST = MorphemeState("pvCop_ST", cop, True, False, False)

pvVerbRoot_S = MorphemeState("pvVerbRoot_S", verb, False, False, True)
# ------------- Adverbs -----------------

advRoot_ST = MorphemeState("advRoot_ST", adv, True, False, True)
advNounRoot_ST = MorphemeState("advRoot_ST", adv, True, False, True)
advForVerbDeriv_ST = MorphemeState("advForVerbDeriv_ST", adv, True, False, True)

avNounAfterAdvRoot_ST = MorphemeState("advToNounRoot_ST", noun, False, False, True)
avA3sg_S = MorphemeState("avA3sg_S", a3sg, False, False, False)
avPnon_S = MorphemeState("avPnon_S", pnon, False, False, False)
avDat_ST = MorphemeState("avDat_ST", dat, True, False, False)

avZero_S = MorphemeState("avZero_S", zero, False, True, False)
avZeroToVerb_S = MorphemeState("avZeroToVerb_S", zero, False, True, False)
# ------------- Interjection, Conjunctions, Determiner and Duplicator  -----------------

conjRoot_ST = MorphemeState("conjRoot_ST", conj, True, False, True)
interjRoot_ST = MorphemeState("interjRoot_ST", interj, True, False, True)
detRoot_ST = MorphemeState("detRoot_ST", det, True, False, True)
dupRoot_ST = MorphemeState("dupRoot_ST", dup, True, False, True)

# ------------- Post Positive ------------------------------------------------

postpRoot_ST = MorphemeState("postpRoot_ST", postp, True, False, True)
postpZero_S = MorphemeState("postpZero_S", zero, False, True, False)

po2nRoot_S = MorphemeState("po2nRoot_S", noun, False, False, False)

po2nA3sg_S = MorphemeState("po2nA3sg_S", a3sg, False, False, False)
po2nA3pl_S = MorphemeState("po2nA3pl_S", a3pl, False, False, False)

po2nP3sg_S = MorphemeState("po2nP3sg_S", p3sg, False, False, False)
po2nP1sg_S = MorphemeState("po2nP1sg_S", p1sg, False, False, False)
po2nP2sg_S = MorphemeState("po2nP2sg_S", p2sg, False, False, False)
po2nP1pl_S = MorphemeState("po2nP1pl_S", p1pl, False, False, False)
po2nP2pl_S = MorphemeState("po2nP2pl_S", p2pl, False, False, False)
po2nPnon_S = MorphemeState("po2nPnon_S", pnon, False, False, False)

po2nNom_ST = MorphemeState("po2nNom_ST", nom, True, False, False)
po2nDat_ST = MorphemeState("po2nDat_ST", dat, True, False, False)
po2nAbl_ST = MorphemeState("po2nAbl_ST", abl, True, False, False)
po2nLoc_ST = MorphemeState("po2nLoc_ST", loc, True, False, False)
po2nIns_ST = MorphemeState("po2nIns_ST", ins, True, False, False)
po2nAcc_ST = MorphemeState("po2nAcc_ST", acc, True, False, False)
po2nGen_ST = MorphemeState("po2nGen_ST", gen, True, False, False)
po2nEqu_ST = MorphemeState("po2nEqu_ST", equ, True, False, False)

# ------------- Verbs -----------------------------------

verbRoot_S = MorphemeState("verbRoot_S", verb, False, False, True)
verbLastVowelDropModRoot_S = MorphemeState(
    "verbLastVowelDropModRoot_S", verb, False, False, True
)
verbLastVowelDropUnmodRoot_S = MorphemeState(
    "verbLastVowelDropUnmodRoot_S", verb, False, False, True
)

vA1sg_ST = MorphemeState("vA1sg_ST", a1sg, True, False, False)
vA2sg_ST = MorphemeState("vA2sg_ST", a2sg, True, False, False)
vA3sg_ST = MorphemeState("vA3sg_ST", a3sg, True, False, False)
vA1pl_ST = MorphemeState("vA1pl_ST", a1pl, True, False, False)
vA2pl_ST = MorphemeState("vA2pl_ST", a2pl, True, False, False)
vA3pl_ST = MorphemeState("vA3pl_ST", a3pl, True, False, False)

vPast_S = MorphemeState("vPast_S", past, False, False, False)
vNarr_S = MorphemeState("vNarr_S", narr, False, False, False)
vCond_S = MorphemeState("vCond_S", cond, False, False, False)
vCondAfterPerson_ST = MorphemeState("vCondAfterPerson_ST", cond, True, False, False)
vPastAfterTense_S = MorphemeState("vPastAfterTense_S", past, False, False, False)
vNarrAfterTense_S = MorphemeState("vNarrAfterTense_S", narr, False, False, False)

# terminal cases are used if A3pl comes before NarrAfterTense, PastAfterTense or vCond
vPastAfterTense_ST = MorphemeState("vPastAfterTense_ST", past, True, False, False)
vNarrAfterTense_ST = MorphemeState("vNarrAfterTense_ST", narr, True, False, False)
vCond_ST = MorphemeState("vCond_ST", cond, True, False, False)

vProgYor_S = MorphemeState("vProgYor_S", prog1, False, False, False)
vProgMakta_S = MorphemeState("vProgMakta_S", prog2, False, False, False)
vFut_S = MorphemeState("vFut_S", fut, False, False, False)

vCop_ST = MorphemeState("vCop_ST", cop, True, False, False)
vCopBeforeA3pl_S = MorphemeState("vCopBeforeA3pl_S", cop, False, False, False)

vNeg_S = MorphemeState("vNeg_S", neg, False, False, False)
vUnable_S = MorphemeState("vUnable_S", unable, False, False, False)
# for negative before progressive-1 "Iyor"
vNegProg1_S = MorphemeState("vNegProg1_S", neg, False, False, False)
vUnableProg1_S = MorphemeState("vUnableProg1_S", unable, False, False, False)

vImp_S = MorphemeState("vImp_S", imp, False, False, False)
vImpYemekYi_S = MorphemeState("vImpYemekYi_S", imp, False, False, False)
vImpYemekYe_S = MorphemeState("vImpYemekYe_S", imp, False, False, False)

vCausT_S = MorphemeState("vCaus_S", caus, False, True, False)
vCausTir_S = MorphemeState("vCausTır_S", caus, False, True, False)

vRecip_S = MorphemeState("vRecip_S", recip, False, True, False)
vImplicitRecipRoot_S = MorphemeState("vImplicitRecipRoot_S", verb, False, False, True)

vReflex_S = MorphemeState("vReflex_S", reflex, False, True, False)
vImplicitReflexRoot_S = MorphemeState("vImplicitReflexRoot_S", verb, False, False, True)

# for progressive vowel drop.
verbRoot_VowelDrop_S = MorphemeState("verbRoot_VowelDrop_S", verb, False, False, True)

vAor_S = MorphemeState("vAor_S", aor, False, False, False)
vAorNeg_S = MorphemeState("vAorNeg_S", aor, False, False, False)
vAorNegEmpty_S = MorphemeState("vAorNegEmpty_S", aor, False, False, False)
vAorPartNeg_S = MorphemeState("vAorPartNeg_S", aorPart, False, True, False)
vAorPart_S = MorphemeState("vAorPart_S", aorPart, False, True, False)

vAble_S = MorphemeState("vAble_S", able, False, True, False)
vAbleNeg_S = MorphemeState("vAbleNeg_S", able, False, True, False)
vAbleNegDerivRoot_S = MorphemeState("vAbleNegDerivRoot_S", verb, False, False, True)

vPass_S = MorphemeState("vPass_S", pass_, False, True, False)

vOpt_S = MorphemeState("vOpt_S", opt, False, False, False)
vDesr_S = MorphemeState("vDesr_S", desr, False, False, False)
vNeces_S = MorphemeState("vNeces_S", neces, False, False, False)

vInf1_S = MorphemeState("vInf1_S", inf1, False, True, False)
vInf2_S = MorphemeState("vInf2_S", inf2, False, True, False)
vInf3_S = MorphemeState("vInf3_S", inf3, False, True, False)

vAgt_S = MorphemeState("vAgt_S", agt, False, True, False)
vActOf_S = MorphemeState("vActOf_S", actOf, False, True, False)

vPastPart_S = MorphemeState("vPastPart_S", pastPart, False, True, False)
vFutPart_S = MorphemeState("vFutPart_S", futPart, False, True, False)
vPresPart_S = MorphemeState("vPresPart_S", presPart, False, True, False)
vNarrPart_S = MorphemeState("vNarrPart_S", narrPart, False, True, False)

vFeelLike_S = MorphemeState("vFeelLike_S", feelLike, False, True, False)

vNotState_S = MorphemeState("vNotState_S", notState, False, True, False)

vEverSince_S = MorphemeState("vEverSince_S", everSince, False, True, False)
vRepeat_S = MorphemeState("vRepeat_S", repeat, False, True, False)
vAlmost_S = MorphemeState("vAlmost_S", almost, False, True, False)
vHastily_S = MorphemeState("vHastily_S", hastily, False, True, False)
vStay_S = MorphemeState("vStay_S", stay, False, True, False)
vStart_S = MorphemeState("vStart_S", start, False, True, False)

vWhile_S = MorphemeState("vWhile_S", while_, False, True, False)
vWhen_S = MorphemeState("vWhen_S", when, False, True, False)
vAsIf_S = MorphemeState("vAsIf_S", asIf, False, True, False)
vSinceDoingSo_S = MorphemeState("vSinceDoingSo_S", sinceDoingSo, False, True, False)
vAsLongAs_S = MorphemeState("vAsLongAs_S", asLongAs, False, True, False)
vByDoingSo_S = MorphemeState("vByDoingSo_S", byDoingSo, False, True, False)
vAdamantly_S = MorphemeState("vAdamantly_S", adamantly, False, True, False)
vAfterDoing_S = MorphemeState("vAfterDoing_S", afterDoingSo, False, True, False)
vWithoutHavingDoneSo_S = MorphemeState(
    "vWithoutHavingDoneSo_S", withoutHavingDoneSo, False, True, False
)
vWithoutBeingAbleToHaveDoneSo_S = MorphemeState(
    "vWithoutBeingAbleToHaveDoneSo_S", withoutBeingAbleToHaveDoneSo, False, True, False
)

vDeYeRoot_S = MorphemeState("vDeYeRoot_S", verb, False, False, True)
# -------- Question (mi) -----------------------------------------------

qPresent_S = MorphemeState("qPresent_S", pres, False, False, False)
qPast_S = MorphemeState("qPast_S", past, False, False, False)
qNarr_S = MorphemeState("qNarr_S", narr, False, False, False)
qA1sg_ST = MorphemeState("qA1sg_ST", a1sg, True, False, False)
qA2sg_ST = MorphemeState("qA2sg_ST", a2sg, True, False, False)
qA3sg_ST = MorphemeState("qA3sg_ST", a3sg, True, False, False)
qA1pl_ST = MorphemeState("qA1pl_ST", a1pl, True, False, False)
qA2pl_ST = MorphemeState("qA2pl_ST", a2pl, True, False, False)
qA3pl_ST = MorphemeState("qA3pl_ST", a3pl, True, False, False)

qCopBeforeA3pl_S = MorphemeState("qCopBeforeA3pl_S", cop, False, False, False)
qCop_ST = MorphemeState("qCop_ST", cop, True, False, False)

questionRoot_S = MorphemeState("questionRoot_S", ques, False, False, True)
# -------- Verb `imek` -----------------------------------------------

imekRoot_S = MorphemeState("imekRoot_S", verb, False, False, True)

imekPast_S = MorphemeState("imekPast_S", past, False, False, False)
imekNarr_S = MorphemeState("imekNarr_S", narr, False, False, False)

imekCond_S = MorphemeState("imekCond_S", cond, False, False, False)

imekA1sg_ST = MorphemeState("imekA1sg_ST", a1sg, True, False, False)
imekA2sg_ST = MorphemeState("imekA2sg_ST", a2sg, True, False, False)
imekA3sg_ST = MorphemeState("imekA3sg_ST", a3sg, True, False, False)
imekA1pl_ST = MorphemeState("imekA1pl_ST", a1pl, True, False, False)
imekA2pl_ST = MorphemeState("imekA2pl_ST", a2pl, True, False, False)
imekA3pl_ST = MorphemeState("imekA3pl_ST", a3pl, True, False, False)

imekCop_ST = MorphemeState("qCop_ST", cop, True, False, False)


class StemTransitionsMapBased:
    """
    Generates StemTransition objects from the dictionary item.
    Most of the time a single StemNode is generated.

    @param item DictionaryItem
    @return one or more StemTransition objects.
    """

    modifiers = {
        RootAttribute.Doubling,
        RootAttribute.LastVowelDrop,
        RootAttribute.ProgressiveVowelDrop,
        RootAttribute.InverseHarmony,
        RootAttribute.Voicing,
        RootAttribute.CompoundP3sg,
        RootAttribute.CompoundP3sgRoot,
    }
    special_roots = {
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

    def __init__(self, morphotactics):
        self.lexicon: RootLexicon = morphotactics.lexicon
        self.morphotactics = morphotactics
        self.multi_stems = {}
        self.single_stems = {}
        self.different_stem_items = {}
        self.add_lexicon_items(self.lexicon.items)

    def add_lexicon_items(self, items: List[DictionaryItem]):
        for dict_item in items:
            if dict_item is None:
                print(dict_item)
            else:
                self.add_dict_item(dict_item)

    def generate_transitions(self, dict_item: DictionaryItem):

        def has_modifier_attribute(item):
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

    def generate_modified_root_nodes(self, dict_item: DictionaryItem):
        result = list(dict_item.pronunciation)
        original_attrs = calculate_phonetic_attributes(dict_item.pronunciation)
        modified_attrs = original_attrs.copy()
        modified_root_state = None
        unmodified_root_state = None
        for attr in dict_item.attributes:
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
                        unmodified_root_state = verbLastVowelDropUnmodRoot_S
                        modified_root_state = verbLastVowelDropModRoot_S
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
        if modified_root_state is None:
            modified_root_state = self.morphotactics.get_root_state(
                dict_item, modified_attrs
            )
        modified = StemTransition(
            dict_item, modified_root_state, modified_attrs, surface="".join(result)
        )

        if original == modified:
            return [original]
        else:
            return [original, modified]

    def handle_special_roots(self, dict_item: DictionaryItem):
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
            root_for_modified = None
            if dict_item.primary_pos == PrimaryPos.Noun:
                root_for_modified = nounLastVowelDropRoot_S
            elif dict_item.primary_pos == PrimaryPos.Adjective:
                root_for_modified = adjLastVowelDropRoot_S

            # TODO: check postpositive case. Maybe it is not required.
            elif dict_item.primary_pos == PrimaryPos.PostPositive:
                root_for_modified = adjLastVowelDropRoot_S
            else:
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
                    pronPers_Mod_S,
                    calculate_phonetic_attributes("ban"),
                    surface="ban",
                )
            else:
                modified = StemTransition(
                    dict_item,
                    pronPers_Mod_S,
                    calculate_phonetic_attributes("san"),
                    surface="san",
                )
            original.attrs.add(PhoneticAttribute.UnModifiedPronoun)
            modified.attrs.add(PhoneticAttribute.ModifiedPronoun)
            return [original, modified]
        elif item_id in ["demek_Verb", "yemek_Verb"]:
            original = StemTransition(dict_item, vDeYeRoot_S, original_attrs)
            if dict_item.lemma == "demek":
                modified = StemTransition(
                    dict_item,
                    vDeYeRoot_S,
                    calculate_phonetic_attributes("di"),
                    surface="di",
                )
            else:
                modified = StemTransition(
                    dict_item,
                    vDeYeRoot_S,
                    calculate_phonetic_attributes("yi"),
                    surface="yi",
                )
            return [original, modified]
        elif item_id == "imek_Verb":
            original = StemTransition(dict_item, imekRoot_S, original_attrs)
            return [original]
        elif item_id in special_item_dict:
            original = StemTransition(dict_item, pronQuant_S, original_attrs)
            modified_root = special_item_dict[item_id]
            modified = StemTransition(
                dict_item,
                pronQuantModified_S,
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

    def add_stem_transition(self, stem_transition: 'StemTransition'):
        surface_form = stem_transition.surface
        if surface_form in self.multi_stems:
            self.multi_stems[surface_form].append(stem_transition)
        elif surface_form in self.single_stems:
            existing_form = self.single_stems.get(surface_form)
            self.multi_stems[surface_form] = [existing_form, stem_transition]
            self.single_stems.pop(surface_form)
        else:
            self.single_stems[surface_form] = stem_transition

    def remove_stem_node(self, stem_transition: 'StemTransition'):
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

    def transitions_from_stem(self, stem):
        if stem in self.single_stems:
            return [self.single_stems.get(stem)]
        elif stem in self.multi_stems:
            return self.multi_stems.get(stem)
        else:
            return []

    def prefix_matches(self, prefix):
        matches = []
        current_string = ""
        for letter in prefix:
            current_string += letter
            matches.extend(self.transitions_from_stem(current_string))
        return matches

    def transitions_from_item(self, dict_item):
        if dict_item in self.different_stem_items:
            return self.different_stem_items.get(dict_item)
        transitions = self.transitions_from_stem(dict_item.root)
        return [
            transition
            for transition in transitions
            if transition.dict_item == dict_item
        ]

    def add_dict_item(self, dict_item):
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
        self.make_graph()
        self.item_root_states = {
            "değil_Verb": nVerbDegil_S,
            "imek_Verb": imekRoot_S,
            "su_Noun": nounSuRoot_S,
            "akarsu_Noun": nounSuRoot_S,
            "öyle_Adv": advForVerbDeriv_ST,
            "böyle_Adv": advForVerbDeriv_ST,
            "şöyle_Adv": advForVerbDeriv_ST,
        }
        self.stem_transitions = StemTransitionsMapBased(self)

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
        noun_S.add_empty(a3sg_S, not_have(RootAttribute.ImplicitPlural))

        # ev-ler-?-?.
        noun_S.add(
            a3pl_S,
            "lAr",
            not_have(RootAttribute.ImplicitPlural).and_(
                not_have(RootAttribute.CompoundP3sg)
            ),
        )

        # Allow only implicit plural `hayvanat`.
        noun_S.add_empty(a3pl_S, has(RootAttribute.ImplicitPlural))

        # --- Compound Handling ---------
        # for compound roots like "zeytinyağ-" generate two transitions
        # NounCompound--(ε)--> a3sgCompound --(ε)--> pNonCompound_S --> Nom_S
        nounCompoundRoot_S.add_empty(
            a3sgCompound_S, has(RootAttribute.CompoundP3sgRoot)
        )

        a3sgCompound_S.add_empty(pnonCompound_S)
        a3sgCompound_S.add(p3pl_S, "lArI")

        # ---- For compound derivations -----------------
        pnonCompound_S.add_empty(nom_S)
        nom_S.add(become_S, "lAş")
        nom_S.add(acquire_S, "lAn")
        # for "zeytinyağlı"
        nom_S.add(with_S, "lI", ContainsMorpheme(with_, without).not_())
        # for "zeytinyağsız"
        nom_S.add(without_S, "sIz", ContainsMorpheme(with_, without).not_())
        # for "zeytinyağlık"
        not_ = NotCondition
        containsNess = ContainsMorpheme(ness)
        nom_S.add(ness_S, "lI~k", not_(containsNess))
        nom_S.add(ness_S, "lI!ğ", not_(containsNess))
        # for "zeytinyağcı"
        nom_S.add(agt_S, ">cI", not_(ContainsMorpheme(agt)))
        # for "zeytinyağsı"
        nom_S.add(justLike_S, "+msI", not_(ContainsMorpheme(justLike)))
        # for "zeytinyağcık"
        nom_S.add(
            dim_S, ">cI~k", HasAnySuffixSurface().not_().and_not(ContainsMorpheme(dim))
        )
        nom_S.add(
            dim_S, ">cI!ğ", HasAnySuffixSurface().not_().and_not(ContainsMorpheme(dim))
        )
        # "zeytinyağcağız"
        nom_S.add(dim_S, "cAğIz", HasAnySuffixSurface().not_())

        # for compound roots like "zeytinyağ-lar-ı" generate two transition
        # NounCompound--(lAr)--> a3plCompound ---> p3sg_S, P1sg etc.
        nounCompoundRoot_S.add(
            a3plCompound_S, "lAr", has(RootAttribute.CompoundP3sgRoot)
        )

        # but for pnon connection, we use lArI
        nounCompoundRoot_S.add(
            a3plCompound2_S, "lArI", has(RootAttribute.CompoundP3sgRoot)
        )

        a3plCompound_S.add_all(
            [
                (p3sg_S, "I"),
                (p2sg_S, "In"),
                (p1sg_S, "Im"),
                (p1pl_S, "ImIz"),
                (p2pl_S, "InIz"),
                (p3pl_S, "I"),
            ]
        )

        # this path is used for plural analysis (A3pl+Pnon+Nom) of compound words.
        a3plCompound2_S.add_empty(pnonCompound2_S)
        pnonCompound2_S.add_empty(nom_ST)

        # ------

        # do not allow possessive suffixes for abbreviations or words like "annemler"

        abbreviation = SecondaryPosIs(SecondaryPos.Abbreviation)
        possessionCond = not_have(RootAttribute.FamilyMember).and_not(abbreviation)

        a3sg_S.add_all(
            [
                (pnon_S, "", not_have(RootAttribute.FamilyMember)),  # ev
                (p1sg_S, "Im", possessionCond),  # evim
                (
                    p2sg_S,
                    "In",
                    possessionCond.and_not(PreviousGroupContainsMorpheme(justLike)),
                ),  # evin
                (p3sg_S, "+sI", possessionCond),  # evi, odası
                (
                    p3sg_S,
                    "",
                    has(RootAttribute.CompoundP3sg),
                ),  # "zeytinyağı" has two analyses. Pnon and P3sg.
                (p1pl_S, "ImIz", possessionCond),  # evimiz
                (
                    p2pl_S,
                    "InIz",
                    possessionCond.and_not(PreviousGroupContainsMorpheme(justLike)),
                ),  # eviniz
                (p3pl_S, "lArI", possessionCond),
            ]
        )  # evleri

        # ev-ler-ε-?
        a3pl_S.add_empty(pnon_S, not_have(RootAttribute.FamilyMember))

        # ev-ler-im-?
        a3pl_S.add_all(
            [
                (p1sg_S, "Im", possessionCond),
                (p2sg_S, "In", possessionCond),
                (
                    p1sg_S,
                    "",
                    has(RootAttribute.ImplicitP1sg),
                ),  # for words like "annemler"
                (
                    p2sg_S,
                    "",
                    has(RootAttribute.ImplicitP2sg),
                ),  # for words like "annenler"
                (p3sg_S, "I", possessionCond),
                (p1pl_S, "ImIz", possessionCond),
                (p2pl_S, "InIz", possessionCond),
                (p3pl_S, "I", possessionCond),
            ]
        )

        # --- handle su - akarsu roots. ----
        nounSuRoot_S.add_empty(a3sgSu_S)
        nounSuRoot_S.add(a3pl_S, "lar")
        a3sgSu_S.add_all(
            [
                (pnon_S, ""),
                (p1sg_S, "yum"),
                (p2sg_S, "yun"),
                (p3sg_S, "yu"),
                (p1pl_S, "yumuz"),
                (p2pl_S, "yunuz"),
                (p3pl_S, "lArI"),
            ]
        )

        # ev-?-ε-ε (ev, evler).
        pnon_S.add_empty(nom_ST, not_have(RootAttribute.FamilyMember))

        equCond1 = (
            ContainsMorpheme(adj, futPart, presPart, narrPart, pastPart)
                .not_()
                .or_(ContainsMorphemeSequence(able, verb, pastPart))
        )

        equCond = PreviousMorphemeIs(a3pl).or_(equCond1)  # allow `yapabildiğince`

        # Not allow "zetinyağı-ya" etc.
        pnon_S.add_all(
            [
                (dat_ST, "+yA", not_have(RootAttribute.CompoundP3sg)),  # ev-e
                (abl_ST, ">dAn", not_have(RootAttribute.CompoundP3sg)),  # ev-den
                (loc_ST, ">dA", not_have(RootAttribute.CompoundP3sg)),  # evde
                (acc_ST, "+yI", not_have(RootAttribute.CompoundP3sg)),  # evi
                (gen_ST, "+nIn", PreviousStateIsNot(a3sgSu_S)),  # evin, zeytinyağının
                (gen_ST, "yIn", PreviousStateIs(a3sgSu_S)),  # suyun
                (
                    equ_ST,
                    ">cA",
                    not_have(RootAttribute.CompoundP3sg).and_(equCond),
                ),  # evce
                (ins_ST, "+ylA"),  # evle, zeytinyağıyla
            ]
        )
        pnon_S.add_all(
            [
                (
                    dat_ST,
                    "+nA",
                    HasRootAttribute(RootAttribute.CompoundP3sg),
                ),  # zeytinyağı-na
                (
                    abl_ST,
                    "+ndAn",
                    HasRootAttribute(RootAttribute.CompoundP3sg),
                ),  # zeytinyağı-ndan
                (
                    loc_ST,
                    "+ndA",
                    HasRootAttribute(RootAttribute.CompoundP3sg),
                ),  # zeytinyağı-nda
                (
                    equ_ST,
                    "+ncA",
                    HasRootAttribute(RootAttribute.CompoundP3sg).and_(equCond),
                ),  # zeytinyağı-nca
                (
                    acc_ST,
                    "+nI",
                    HasRootAttribute(RootAttribute.CompoundP3sg),
                ),  # zeytinyağı-nı
            ]
        )
        # This transition is for words like "içeri" or "dışarı".
        # Those words implicitly contains Dative suffix.
        # But It is also possible to add dative suffix +yA to those words such as "içeri-ye".
        pnon_S.add_empty(dat_ST, HasRootAttribute(RootAttribute.ImplicitDative))

        p1sg_S.add_all(
            [
                (nom_ST, ""),  # evim
                (dat_ST, "A"),  # evime
                (loc_ST, "dA"),  # evimde
                (abl_ST, "dAn"),  # evimden
                (ins_ST, "lA"),  # evimle
                (gen_ST, "In"),  # evimin
                (equ_ST, "cA", equCond.or_(ContainsMorpheme(pastPart))),  # evimce
                (acc_ST, "I"),  # evimi
            ]
        )

        p2sg_S.add_all(
            [
                (nom_ST, ""),  # evin
                (dat_ST, "A"),  # evine
                (loc_ST, "dA"),  # evinde
                (abl_ST, "dAn"),  # evinden
                (ins_ST, "lA"),  # evinle
                (gen_ST, "In"),  # evinin
                (equ_ST, "cA", equCond.or_(ContainsMorpheme(pastPart))),  # evince
                (acc_ST, "I"),  # evini
            ]
        )

        p3sg_S.add_all(
            [
                (nom_ST, ""),  # evi
                (dat_ST, "nA"),  # evine
                (loc_ST, "ndA"),  # evinde
                (abl_ST, "ndAn"),  # evinden
                (ins_ST, "ylA"),  # eviyle
                (gen_ST, "nIn"),  # evinin
                (equ_ST, "ncA", equCond.or_(ContainsMorpheme(pastPart))),  # evince
                (acc_ST, "nI"),  # evini
            ]
        )

        p1pl_S.add_all(
            [
                (nom_ST, ""),  # evimiz
                (dat_ST, "A"),  # evimize
                (loc_ST, "dA"),  # evimizde
                (abl_ST, "dAn"),  # evimizden
                (ins_ST, "lA"),  # evimizden
                (gen_ST, "In"),  # evimizin
                (equ_ST, "cA", equCond.or_(ContainsMorpheme(pastPart))),  # evimizce
                (acc_ST, "I"),  # evimizi
            ]
        )
        p2pl_S.add_all(
            [
                (nom_ST, ""),  # eviniz
                (dat_ST, "A"),  # evinize
                (loc_ST, "dA"),  # evinizde
                (abl_ST, "dAn"),  # evinizden
                (ins_ST, "lA"),  # evinizle
                (gen_ST, "In"),  # evinizin
                (equ_ST, "cA", equCond.or_(ContainsMorpheme(pastPart))),  # evinizce
                (acc_ST, "I"),  # evinizi
            ]
        )

        p3pl_S.add_all(
            [
                (nom_ST, ""),  # evleri
                (dat_ST, "nA"),  # evlerine
                (loc_ST, "ndA"),  # evlerinde
                (abl_ST, "ndAn"),  # evlerinden
                (ins_ST, "ylA"),  # evleriyle
                (gen_ST, "nIn"),  # evlerinin
                # For now we omit equCond check because adj+..+A3pl+..+Equ fails.
                (equ_ST, "+ncA"),  # evlerince.
                (acc_ST, "nI"),  # evlerini
            ]
        )

        # ev-ε-ε-ε-cik (evcik). Disallow this path if visitor contains any non empty surface suffix.
        # There are two almost identical suffix transitions with templates ">cI~k" and ">cI!ğ"
        # This was necessary for some simplification during analysis. This way there will be only one
        # surface form generated for each transition.
        nom_ST.add(dim_S, ">cI~k", HasAnySuffixSurface().not_().and_not(abbreviation))
        nom_ST.add(dim_S, ">cI!ğ", HasAnySuffixSurface().not_().and_not(abbreviation))

        # ev-ε-ε-ε-ceğiz (evceğiz)
        nom_ST.add(dim_S, "cAğIz", HasAnySuffixSurface().not_().and_not(abbreviation))

        # connect dim to the noun root.
        dim_S.add_empty(noun_S)

        emptyAdjNounSeq = ContainsMorphemeSequence(adj, zero, noun, a3sg, pnon, nom)

        nom_ST.add(
            ness_S,
            "lI~k",
            NoSurfaceAfterDerivation()
                .and_not(containsNess)
                .and_not(emptyAdjNounSeq)
                .and_not(abbreviation),
        )
        nom_ST.add(
            ness_S,
            "lI!ğ",
            NoSurfaceAfterDerivation()
                .and_not(containsNess)
                .and_not(emptyAdjNounSeq)
                .and_not(abbreviation),
        )

        # connect `ness` to the noun root.
        ness_S.add_empty(noun_S)

        nom_ST.add(
            agt_S, ">cI", NoSurfaceAfterDerivation().and_not(ContainsMorpheme(adj, agt))
        )

        # connect `ness` to the noun root.
        agt_S.add_empty(noun_S)

        # here we do not allow an adjective to pass here.
        # such as, adj->zero->noun->ε-ε-ε->zero->Verb is not acceptable because there is already a
        # adj->zero->Verb path.

        noun2VerbZeroDerivationCondition = HasTail().and_not(
            NoSurfaceAfterDerivation().and_(LastDerivationIs(adjZeroDeriv_S))
        )
        nom_ST.add_empty(nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-ya-yım elma-ya-ydı
        dat_ST.add_empty(nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-dan-ım elma-dan-dı
        abl_ST.add_empty(nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-da-yım elma-da-ydı
        loc_ST.add_empty(nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-yla-yım elma-yla-ydı
        ins_ST.add_empty(nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        # elma-nın-ım elma-nın-dı
        gen_ST.add_empty(nounZeroDeriv_S, noun2VerbZeroDerivationCondition)

        nounZeroDeriv_S.add_empty(nVerb_S)

        # meyve-li

        noSurfaceAfterDerivation = NoSurfaceAfterDerivation()
        nom_ST.add(
            with_S,
            "lI",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(with_, without)),
        )

        nom_ST.add(
            without_S,
            "sIz",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(with_, without, inf1)),
        )

        nom_ST.add(
            justLike_S,
            "+msI",
            noSurfaceAfterDerivation.and_not(
                ContainsMorpheme(justLike, futPart, pastPart, presPart, adj)
            ),
        )

        # TODO: test order
        nom_ST.add(
            justLike_S,
            "ImsI",
            not_have(PhoneticAttribute.LastLetterVowel)
                .and_(noSurfaceAfterDerivation)
                .and_not(ContainsMorpheme(justLike, futPart, pastPart, presPart, adj)),
        )

        nom_ST.add(
            related_S,
            "sAl",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(with_, without, related)),
        )

        # connect With to Adjective root.
        with_S.add_empty(adjectiveRoot_ST)
        without_S.add_empty(adjectiveRoot_ST)
        related_S.add_empty(adjectiveRoot_ST)

        justLike_S.add_empty(adjectiveRoot_ST)

        # meyve-de-ki
        notRelRepetition = HasTailSequence(rel, adj, zero, noun, a3sg, pnon, loc).not_()
        loc_ST.add(rel_S, "ki", notRelRepetition)
        rel_S.add_empty(adjectiveRoot_ST)

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
        nom_ST.add(rel_S, "ki", time.and_not(time2))
        nom_ST.add(rel_S, "ki", DictionaryItemIsAny(ileri, geri, ote, beri))
        nom_ST.add(rel_S, "kü", time2.and_(time))

        # After Genitive suffix, Rel suffix makes a Pronoun derivation.
        gen_ST.add(relToPron_S, "ki")
        relToPron_S.add_empty(pronAfterRel_S)

        verbDeriv = ContainsMorpheme(inf1, inf2, inf3, pastPart, futPart)

        nom_ST.add(
            become_S,
            "lAş",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(adj)).and_not(verbDeriv),
        )
        become_S.add_empty(verbRoot_S)

        nom_ST.add(
            acquire_S,
            "lAn",
            noSurfaceAfterDerivation.and_not(ContainsMorpheme(adj)).and_not(verbDeriv),
        )

        acquire_S.add_empty(verbRoot_S)

        # Inf1 mak makes noun derivation. However, it cannot get any possessive or plural suffix.
        # Also cannot be followed by Dat, Gen, Acc case suffixes.
        # So we create a path only for it.
        nounInf1Root_S.add_empty(a3sgInf1_S)
        a3sgInf1_S.add_empty(pnonInf1_S)
        pnonInf1_S.add_empty(nom_ST)
        pnonInf1_S.add(abl_ST, "tAn")

        pnonInf1_S.add(loc_ST, "tA")
        pnonInf1_S.add(ins_ST, "lA")

        nounActOfRoot_S.add_empty(a3sgActOf_S)
        nounActOfRoot_S.add(a3plActOf_S, "lar")
        a3sgActOf_S.add_empty(pnonActOf)
        a3plActOf_S.add_empty(pnonActOf)
        pnonActOf.add_empty(nom_ST)

    def connect_last_vowel_drop_words(self):
        nounLastVowelDropRoot_S.add_empty(a3sgLastVowelDrop_S)
        nounLastVowelDropRoot_S.add(a3PlLastVowelDrop_S, "lAr")
        a3sgLastVowelDrop_S.add_empty(pNonLastVowelDrop_S)
        a3PlLastVowelDrop_S.add_empty(pNonLastVowelDrop_S)
        pNonLastVowelDrop_S.add(loc_ST, ">dA")
        pNonLastVowelDrop_S.add(abl_ST, ">dAn")

        adjLastVowelDropRoot_S.add_empty(zeroLastVowelDrop_S)
        postpLastVowelDropRoot_S.add_empty(zeroLastVowelDrop_S)
        zeroLastVowelDrop_S.add_empty(nounLastVowelDropRoot_S)

    def connect_proper_nouns_and_abbreviations(self):
        # ---- Proper noun handling -------
        # TODO: consider adding single quote after an overhaul.
        # nounProper_S.add(puncProperSeparator_S, "'")
        nounProper_S.add_empty(a3sg_S)
        nounProper_S.add(a3pl_S, "lAr")
        puncProperSeparator_S.add_empty(a3sg_S)
        puncProperSeparator_S.add(a3pl_S, "lAr")

        # ---- Abbreviation Handling -------
        # TODO: consider restricting possessive, most derivation and plural suffixes.
        nounAbbrv_S.add_empty(a3sg_S)
        nounAbbrv_S.add(a3pl_S, "lAr")

        # ----- This is for catching words that cannot have a suffix.
        nounNoSuffix_S.add_empty(nounA3sgNoSuffix_S)
        nounA3sgNoSuffix_S.add_empty(nounPnonNoSuffix_S)
        nounPnonNoSuffix_S.add_empty(nounNomNoSuffix_ST)

    def connect_adjective_states(self):
        # zero morpheme derivation. Words like "yeşil-i" requires Adj to Noun conversion.
        # Since noun suffixes are not derivational a "Zero" morpheme is used for this.
        # Transition has a HasTail() condition because Adj->Zero->Noun+A3sg+Pnon+Nom) is not allowed.
        adjectiveRoot_ST.add_empty(adjZeroDeriv_S, HasTail())

        adjZeroDeriv_S.add_empty(noun_S)

        adjZeroDeriv_S.add_empty(nVerb_S)

        adjectiveRoot_ST.add(aLy_S, ">cA")
        aLy_S.add_empty(advRoot_ST)

        adjectiveRoot_ST.add(
            aAsIf_S, ">cA", ContainsMorpheme(asIf, ly, agt, with_, justLike).not_()
        )

        aAsIf_S.add_empty(adjectiveRoot_ST)

        adjectiveRoot_ST.add(
            aAgt_S, ">cI", ContainsMorpheme(asIf, ly, agt, with_, justLike).not_()
        )
        aAgt_S.add_empty(noun_S)

        adjectiveRoot_ST.add(
            justLike_S,
            "+msI",
            NoSurfaceAfterDerivation().and_(ContainsMorpheme(justLike).not_()),
        )

        adjectiveRoot_ST.add(
            justLike_S,
            "ImsI",
            not_have(PhoneticAttribute.LastLetterVowel)
                .and_(NoSurfaceAfterDerivation())
                .and_(ContainsMorpheme(justLike).not_()),
        )

        adjectiveRoot_ST.add(become_S, "lAş", NoSurfaceAfterDerivation())
        adjectiveRoot_ST.add(acquire_S, "lAn", NoSurfaceAfterDerivation())

        c1 = PreviousMorphemeIsAny(futPart, pastPart)

        adjAfterVerb_S.add_empty(aPnon_ST, c1)
        adjAfterVerb_S.add(aP1sg_ST, "Im", c1)
        adjAfterVerb_S.add(aP2sg_ST, "In", c1)
        adjAfterVerb_S.add(aP3sg_ST, "I", c1)
        adjAfterVerb_S.add(aP1pl_ST, "ImIz", c1)
        adjAfterVerb_S.add(aP2pl_ST, "InIz", c1)
        adjAfterVerb_S.add(aP3pl_ST, "lArI", c1)

        adjectiveRoot_ST.add(ness_S, "lI~k")
        adjectiveRoot_ST.add(ness_S, "lI!ğ")

        adjAfterVerb_ST.add(ness_S, "lI~k", PreviousMorphemeIs(aorPart))
        adjAfterVerb_ST.add(ness_S, "lI!ğ", PreviousMorphemeIs(aorPart))

    def connect_numeral_states(self):
        numeralRoot_ST.add(ness_S, "lI~k")
        numeralRoot_ST.add(ness_S, "lI!ğ")
        numeralRoot_ST.add_empty(numZeroDeriv_S, HasTail())
        numZeroDeriv_S.add_empty(noun_S)
        numZeroDeriv_S.add_empty(nVerb_S)

        numeralRoot_ST.add(
            justLike_S,
            "+msI",
            NoSurfaceAfterDerivation().and_(ContainsMorpheme(justLike).not_()),
        )

        numeralRoot_ST.add(
            justLike_S,
            "ImsI",
            not_have(PhoneticAttribute.LastLetterVowel)
                .and_(NoSurfaceAfterDerivation())
                .and_(ContainsMorpheme(justLike).not_()),
        )

    def connect_verb_after_noun_adj_states(self):
        # elma-..-ε-yım
        nVerb_S.add_empty(nPresent_S)

        # elma-ydı, çorap-tı
        nVerb_S.add(nPast_S, "+y>dI")
        # elma-ymış
        nVerb_S.add(nNarr_S, "+ymIş")

        nVerb_S.add(nCond_S, "+ysA")

        nVerb_S.add(vWhile_S, "+yken")

        # word "değil" is special. It contains negative suffix implicitly. Also it behaves like
        # noun->Verb Zero morpheme derivation. because it cannot have most Verb suffixes.
        # So we connect it to a separate root state "nVerbDegil" instead of Verb
        degilRoot = self.lexicon.get_item_by_id("değil_Verb")
        nVerbDegil_S.add_empty(nNeg_S, DictionaryItemIs(degilRoot))
        # copy transitions from nVerb_S
        nNeg_S.copy_outgoing_transitions_from(nVerb_S)

        noFamily = not_have(RootAttribute.FamilyMember)
        # for preventing elmamım, elmamdım
        # pP1sg_S, pDat_ST, pA1sg_S, pA1pl_S, pA3pl_S, pP2sg_S, pP1pl_S, pP3sg_S, pP1sg_S
        # TODO: below causes "beklemedeyiz" to fail.

        verbDeriv = ContainsMorpheme(inf1, inf2, inf3, pastPart, futPart)

        allowA1sgTrans = noFamily.and_not(ContainsMorphemeSequence(p1sg, nom)).and_not(
            verbDeriv
        )

        allowA2sgTrans = noFamily.and_not(ContainsMorphemeSequence(p2sg, nom)).and_not(
            verbDeriv
        )

        allowA3plTrans = (
            noFamily.and_not(PreviousGroupContains(a3pl_S))
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
        nPresent_S.add(nA1sg_ST, "+yIm", allowA1sgTrans)
        nPresent_S.add(nA2sg_ST, "sIn", allowA2sgTrans)

        # elma-ε-ε-dır to non terminal A3sg. We do not allow ending with A3sg from empty Present tense.
        nPresent_S.add_empty(nA3sg_S)

        # we allow `değil` to end with terminal A3sg from Present tense.
        nPresent_S.add_empty(nA3sg_ST, DictionaryItemIs(degilRoot))

        # elma-lar, elma-da-lar as Verb.
        # TODO: consider disallowing this for "elmalar" case.
        nPresent_S.add(
            nA3pl_ST,
            "lAr",
            not_have(RootAttribute.CompoundP3sg)
                # do not allow "okumak-lar"
                .and_not(PreviousGroupContainsMorpheme(inf1)).and_(allowA3plTrans),
        )

        # elma-ydı-m. Do not allow "elmaya-yım" (Oflazer accepts this)
        nPast_S.add(nA1sg_ST, "m", allowA1sgTrans)
        nNarr_S.add(nA1sg_ST, "Im", allowA1sgTrans)

        nPast_S.add(nA2sg_ST, "n", allowA2sgTrans)
        nNarr_S.add(nA2sg_ST, "sIn", allowA2sgTrans)

        nPast_S.add(nA1pl_ST, "k", allowA1plTrans)
        nNarr_S.add(nA1pl_ST, "Iz", allowA1plTrans)
        nPresent_S.add(nA1pl_ST, "+yIz", allowA1plTrans)

        nPast_S.add(nA2pl_ST, "InIz", allowA2plTrans)
        nNarr_S.add(nA2pl_ST, "sInIz", allowA2plTrans)
        nPresent_S.add(nA2pl_ST, "sInIz", allowA2plTrans)

        # elma-ydı-lar.
        nPast_S.add(
            nA3pl_ST, "lAr", not_have(RootAttribute.CompoundP3sg).and_(allowA3plTrans)
        )
        # elma-ymış-lar.
        nNarr_S.add(
            nA3pl_ST, "lAr", not_have(RootAttribute.CompoundP3sg).and_(allowA3plTrans)
        )

        # elma-ydı-ε
        nPast_S.add_empty(nA3sg_ST)
        # elma-ymış-ε
        nNarr_S.add_empty(nA3sg_ST)

        # narr+cons is allowed but not past+cond
        nNarr_S.add(nCond_S, "sA")

        nCond_S.add(nA1sg_ST, "m", allowA1sgTrans)
        nCond_S.add(nA2sg_ST, "n", allowA2sgTrans)
        nCond_S.add(nA1pl_ST, "k", allowA1plTrans)
        nCond_S.add(nA2pl_ST, "nIz", allowA2plTrans)
        nCond_S.add_empty(nA3sg_ST)
        nCond_S.add(nA3pl_ST, "lAr")

        # for not allowing "elma-ydı-m-dır"

        rejectNoCopula = CurrentGroupContainsAny(
            nPast_S, nCond_S, nCopBeforeA3pl_S
        ).not_()

        # elma-yım-dır
        nA1sg_ST.add(nCop_ST, "dIr", rejectNoCopula)
        # elmasındır
        nA2sg_ST.add(nCop_ST, "dIr", rejectNoCopula)
        # elmayızdır
        nA1pl_ST.add(nCop_ST, "dIr", rejectNoCopula)
        # elmasınızdır
        nA2pl_ST.add(nCop_ST, "dIr", rejectNoCopula)

        nA3sg_S.add(nCop_ST, ">dIr", rejectNoCopula)

        nA3pl_ST.add(nCop_ST, "dIr", rejectNoCopula)

        asIfCond = PreviousMorphemeIsAny(narr)
        nA3sg_ST.add(vAsIf_S, ">cAsInA", asIfCond)
        nA1sg_ST.add(vAsIf_S, ">cAsInA", asIfCond)
        nA2sg_ST.add(vAsIf_S, ">cAsInA", asIfCond)
        nA1pl_ST.add(vAsIf_S, ">cAsInA", asIfCond)
        nA2pl_ST.add(vAsIf_S, ">cAsInA", asIfCond)
        nA3pl_ST.add(vAsIf_S, ">cAsInA", asIfCond)

        # Copula can come before A3pl.
        nPresent_S.add(nCopBeforeA3pl_S, ">dIr")
        nCopBeforeA3pl_S.add(nA3pl_ST, "lAr")

    def connect_pronoun_states(self):
        # ----------- Personal Pronouns ----------------------------

        ben = self.lexicon.get_item_by_id("ben_Pron_Pers")
        sen = self.lexicon.get_item_by_id("sen_Pron_Pers")
        o = self.lexicon.get_item_by_id("o_Pron_Pers")
        biz = self.lexicon.get_item_by_id("biz_Pron_Pers")
        siz = self.lexicon.get_item_by_id("siz_Pron_Pers")
        falan = self.lexicon.get_item_by_id("falan_Pron_Pers")
        falanca = self.lexicon.get_item_by_id("falanca_Pron_Pers")

        pronPers_S.add_empty(pA1sg_S, DictionaryItemIs(ben))
        pronPers_S.add_empty(pA2sg_S, DictionaryItemIs(sen))
        pronPers_S.add_empty(pA3sg_S, DictionaryItemIsAny(o, falan, falanca))
        pronPers_S.add(
            pA3pl_S, "nlAr", DictionaryItemIs(o)
        )  # Oflazer does not have "onlar" as Pronoun root.

        pronPers_S.add(pA3pl_S, "lAr", DictionaryItemIsAny(falan, falanca))
        pronPers_S.add_empty(pA1pl_S, DictionaryItemIs(biz))
        pronPers_S.add(pA1pl_S, "lAr", DictionaryItemIs(biz))
        pronPers_S.add_empty(pA2pl_S, DictionaryItemIs(siz))
        pronPers_S.add(pA2pl_S, "lAr", DictionaryItemIs(siz))

        # --- modified `ben-sen` special state and transitions
        pronPers_Mod_S.add_empty(pA1sgMod_S, DictionaryItemIs(ben))
        pronPers_Mod_S.add_empty(pA2sgMod_S, DictionaryItemIs(sen))
        pA1sgMod_S.add_empty(pPnonMod_S)
        pA2sgMod_S.add_empty(pPnonMod_S)
        pPnonMod_S.add(pDat_ST, "A")
        # ----

        # Possesive connecitons are not used.
        pA1sg_S.add_empty(pPnon_S)
        pA2sg_S.add_empty(pPnon_S)
        pA3sg_S.add_empty(pPnon_S)
        pA1pl_S.add_empty(pPnon_S)
        pA2pl_S.add_empty(pPnon_S)
        pA3pl_S.add_empty(pPnon_S)

        # ------------ Noun -> Rel -> Pron ---------------------------
        # masanınki
        pronAfterRel_S.add_empty(pA3sgRel_S)
        pronAfterRel_S.add(pA3plRel_S, "lAr")
        pA3sgRel_S.add_empty(pPnonRel_S)
        pA3plRel_S.add_empty(pPnonRel_S)
        pPnonRel_S.add_empty(pNom_ST)
        pPnonRel_S.add(pDat_ST, "+nA")
        pPnonRel_S.add(pAcc_ST, "+nI")
        pPnonRel_S.add(pAbl_ST, "+ndAn")
        pPnonRel_S.add(pLoc_ST, "+ndA")
        pPnonRel_S.add(pIns_ST, "+ylA")
        pPnonRel_S.add(pGen_ST, "+nIn")

        # ------------ Demonstrative pronouns. ------------------------

        bu = self.lexicon.get_item_by_id("bu_Pron_Demons")

        su = self.lexicon.get_item_by_id("şu_Pron_Demons")

        o_demons = self.lexicon.get_item_by_id("o_Pron_Demons")

        pronDemons_S.add_empty(pA3sg_S)
        pronDemons_S.add(pA3pl_S, "nlAr")

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
        pronQuant_S.add_empty(
            pQuantA3sg_S,
            DictionaryItemIsAny(
                herkes, umum, hepsi, cumlesi, hep, tumu, birkaci, topu
            ).not_(),
        )

        pronQuant_S.add(
            pQuantA3pl_S,
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
        pronQuant_S.add(pQuantA1pl_S, "lAr", DictionaryItemIsAny(bazi))
        pronQuant_S.add(pQuantA2pl_S, "lAr", DictionaryItemIsAny(bazi))

        # Herkes is implicitly plural.
        pronQuant_S.add_empty(
            pQuantA3pl_S,
            DictionaryItemIsAny(
                herkes, umum, birkaci, hepsi, cumlesi, cogu, bircogu, tumu, topu
            ),
        )

        # connect "kimse" to Noun-A3sg and Noun-A3pl. It behaves like a noun.
        pronQuant_S.add_empty(a3sg_S, DictionaryItemIs(kimse))
        pronQuant_S.add(a3pl_S, "lAr", DictionaryItemIsAny(kimse))

        # for `birbiri-miz` `hep-imiz`
        pronQuant_S.add_empty(
            pQuantA1pl_S,
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
        pronQuant_S.add_empty(
            pQuantA2pl_S,
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
        pronQuantModified_S.add_empty(pQuantModA3pl_S)
        pQuantModA3pl_S.add(pP3pl_S, "lArI")

        # both `biri-ne` and `birisi-ne` or `birbirine` and `birbirisine` are accepted.
        pQuantA3sg_S.add_empty(
            pP3sg_S,
            DictionaryItemIsAny(
                biri, birbiri, kimi, herbiri, hicbiri, oburu, oburku, beriki
            ).and_(not_have(PhoneticAttribute.ModifiedPronoun)),
        )

        pQuantA3sg_S.add(
            pP3sg_S,
            "sI",
            DictionaryItemIsAny(
                biri, bazi, kimi, birbiri, herbiri, hicbiri, oburku
            ).and_(not_have(PhoneticAttribute.ModifiedPronoun)),
        )

        # there is no connection from pQuantA3pl to Pnon for preventing `biriler` (except herkes)
        pQuantA3pl_S.add(
            pP3pl_S, "I", DictionaryItemIsAny(biri, bazi, birbiri, kimi, oburku, beriki)
        )
        pQuantA3pl_S.add_empty(
            pP3pl_S,
            DictionaryItemIsAny(hepsi, birkaci, cumlesi, cogu, tumu, topu, bircogu),
        )
        pQuantA3pl_S.add_empty(
            pPnon_S, DictionaryItemIsAny(herkes, umum, oburku, beriki)
        )

        pQuantA1pl_S.add(pP1pl_S, "ImIz")
        pQuantA2pl_S.add(pP2pl_S, "InIz")

        # ------------ Question Pronouns ----------------------------
        # `kim` (kim_Pron_Ques), `ne` and `nere`

        ne = self.lexicon.get_item_by_id("ne_Pron_Ques")
        nere = self.lexicon.get_item_by_id("nere_Pron_Ques")
        kim = self.lexicon.get_item_by_id("kim_Pron_Ques")
        pronQues_S.add_empty(pQuesA3sg_S)
        pronQues_S.add(pQuesA3pl_S, "lAr")

        pQuesA3sg_S.add_all(
            [
                (pPnon_S, ""),
                (pP3sg_S, "+sI"),
                (pP1sg_S, "Im", DictionaryItemIs(ne).not_()),
                (pP1sg_S, "yIm", DictionaryItemIs(ne)),
                (pP2sg_S, "In", DictionaryItemIs(ne).not_()),
                (pP2sg_S, "yIn", DictionaryItemIs(ne)),
                (pP1pl_S, "ImIz", DictionaryItemIs(ne).not_()),
                (pP1pl_S, "yImIz", DictionaryItemIs(ne)),
            ]
        )

        pQuesA3pl_S.add_all(
            [(pPnon_S, ""), (pP3sg_S, "I"), (pP1sg_S, "Im"), (pP1pl_S, "ImIz")]
        )

        # ------------ Reflexive Pronouns ----------------------------
        # `kendi`

        kendi = self.lexicon.get_item_by_id("kendi_Pron_Reflex")
        pronReflex_S.add_all(
            [
                (pReflexA1sg_S, ""),
                (pReflexA2sg_S, ""),
                (pReflexA3sg_S, ""),
                (pReflexA1pl_S, ""),
                (pReflexA2pl_S, ""),
                (pReflexA3pl_S, ""),
            ]
        )

        pReflexA1sg_S.add(pP1sg_S, "Im")
        pReflexA2sg_S.add(pP2sg_S, "In")
        pReflexA3sg_S.add(pP3sg_S, "+sI")
        pReflexA2sg_S.add_empty(pP3sg_S)
        pReflexA1pl_S.add(pP1pl_S, "ImIz")
        pReflexA2pl_S.add(pP2pl_S, "InIz")
        pReflexA3pl_S.add(pP3pl_S, "lArI")

        # ------------------------
        # Case connections for all

        nGroup = DictionaryItemIsAny(ne, nere, falan, falanca, hep, herkes).not_()

        yGroup = DictionaryItemIsAny(ne, nere, falan, falanca, hep, herkes)

        pPnon_S.add_all(
            [
                (pNom_ST, ""),
                # not allowing `ben-e` and `sen-e`. `ban-a` and `san-a` are using different states
                (
                    pDat_ST,
                    "+nA",
                    DictionaryItemIsAny(
                        ben, sen, ne, nere, falan, falanca, herkes
                    ).not_(),
                ),
                (pDat_ST, "+yA", yGroup),
                (pAcc_ST, "+nI", nGroup),
                (pAcc_ST, "+yI", yGroup),
                (pLoc_ST, "+ndA", nGroup),
                (pLoc_ST, ">dA", yGroup),
                (pAbl_ST, "+ndAn", nGroup),
                (pAbl_ST, ">dAn", yGroup),
                (
                    pGen_ST,
                    "+nIn",
                    nGroup.and_(DictionaryItemIsAny(biz, ben, sen).not_()),
                ),
                (
                    pGen_ST,
                    "im",
                    DictionaryItemIsAny(ben, biz),
                ),  # benim, senin, bizim are genitive.
                (pGen_ST, "in", DictionaryItemIs(sen)),
                (pGen_ST, "+yIn", yGroup.and_(DictionaryItemIsAny(biz).not_())),
                (pEqu_ST, ">cA", yGroup),
                (pEqu_ST, ">cA", nGroup),
                (pIns_ST, "+ylA", yGroup),
                (pIns_ST, "+nlA", nGroup),
                (pIns_ST, "+nInlA", nGroup.and_(DictionaryItemIsAny(bu, su, o, sen))),
                (pIns_ST, "inle", DictionaryItemIs(siz)),
                (pIns_ST, "imle", DictionaryItemIsAny(biz, ben)),
            ]
        )

        conditionpP1sg_S = DictionaryItemIsAny(kim, ben, ne, nere, kendi)

        pP1sg_S.add_all(
            [
                (pNom_ST, ""),
                (pDat_ST, "+nA", nGroup),
                (pAcc_ST, "+nI", nGroup),
                (pDat_ST, "+yA", yGroup),
                (pAcc_ST, "+yI", yGroup),
                (pLoc_ST, "+ndA", DictionaryItemIsAny(kendi)),
                (pAbl_ST, "+ndAn", DictionaryItemIsAny(kendi)),
                (pEqu_ST, "+ncA", DictionaryItemIsAny(kendi)),
                (pIns_ST, "+nlA", conditionpP1sg_S),
                (pGen_ST, "+nIn", conditionpP1sg_S),
            ]
        )

        conditionP2sg = DictionaryItemIsAny(kim, sen, ne, nere, kendi)
        pP2sg_S.add_all(
            [
                (pNom_ST, ""),
                (pDat_ST, "+nA", nGroup),
                (pAcc_ST, "+nI", nGroup),
                (pDat_ST, "+yA", yGroup),
                (pAcc_ST, "+yI", yGroup),
                (pLoc_ST, "+ndA", DictionaryItemIsAny(kendi)),
                (pAbl_ST, "+ndAn", DictionaryItemIsAny(kendi)),
                (pEqu_ST, "+ncA", DictionaryItemIsAny(kendi)),
                (pIns_ST, "+nlA", conditionP2sg),
                (pGen_ST, "+nIn", conditionP2sg),
            ]
        )

        p3sgCond = DictionaryItemIsAny(
            kendi, kim, ne, nere, o, bazi, biri, birbiri, herbiri, hep, kimi, hicbiri
        )

        pP3sg_S.add_all(
            [
                (pNom_ST, ""),
                (pDat_ST, "+nA", nGroup),
                (pAcc_ST, "+nI", nGroup),
                (pDat_ST, "+yA", yGroup),
                (pAcc_ST, "+yI", yGroup),
                (pLoc_ST, "+ndA", p3sgCond),
                (pAbl_ST, "+ndAn", p3sgCond),
                (pGen_ST, "+nIn", p3sgCond),
                (pEqu_ST, "ncA", p3sgCond),
                (pIns_ST, "+ylA", p3sgCond),
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
        pP1pl_S.add_all(
            [
                (pNom_ST, ""),
                (pDat_ST, "+nA", nGroup),
                (pAcc_ST, "+nI", nGroup),
                (pDat_ST, "+yA", yGroup),
                (pAcc_ST, "+yI", yGroup),
                (pLoc_ST, "+ndA", hepCnd),
                (pAbl_ST, "+ndAn", hepCnd),
                (pGen_ST, "+nIn", hepCnd),
                (pEqu_ST, "+ncA", hepCnd),
                (pIns_ST, "+nlA", hepCnd),
            ]
        )

        pP2pl_S.add_all(
            [
                (pNom_ST, ""),
                (pDat_ST, "+nA", nGroup),
                (pAcc_ST, "+nI", nGroup),
                (pDat_ST, "+yA", yGroup),
                (pAcc_ST, "+yI", yGroup),
                (pLoc_ST, "+ndA", hepCnd),
                (pAbl_ST, "+ndAn", hepCnd),
                (pGen_ST, "+nIn", hepCnd),
                (pEqu_ST, "+ncA", hepCnd),
                (pIns_ST, "+nlA", hepCnd),
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

        pP3pl_S.add_all(
            [
                (pNom_ST, ""),
                (pDat_ST, "+nA", nGroup),
                (pAcc_ST, "+nI", nGroup),
                (pDat_ST, "+yA", yGroup),
                (pAcc_ST, "+yI", yGroup),
                (pLoc_ST, "+ndA", hepsi_cnd),
                (pAbl_ST, "+ndAn", hepsi_cnd),
                (pGen_ST, "+nIn", hepsi_cnd.or_(DictionaryItemIsAny(sen, siz))),
                (pEqu_ST, "+ncA", hepsi_cnd),
                (pIns_ST, "+ylA", hepsi_cnd),
            ]
        )

        pNom_ST.add(
            with_S, "+nlI", DictionaryItemIsAny(bu, su, o_demons, ben, sen, o, biz, siz)
        )
        pNom_ST.add(with_S, "lI", DictionaryItemIsAny(nere))
        pNom_ST.add(with_S, "+ylI", DictionaryItemIsAny(ne))
        pNom_ST.add(
            without_S,
            "+nsIz",
            DictionaryItemIsAny(nere, bu, su, o_demons, ben, sen, o, biz, siz),
        )
        pNom_ST.add(without_S, "+ysIz", DictionaryItemIsAny(ne))
        pGen_ST.add(
            rel_S,
            "ki",
            DictionaryItemIsAny(nere, bu, su, o_demons, ne, sen, o, biz, siz),
        )

        notRelRepetition = HasTailSequence(rel, adj, zero, noun, a3sg, pnon, loc).not_()
        pLoc_ST.add(rel_S, "ki", notRelRepetition)

        pIns_ST.add(vWhile_S, "+yken")

        # ------------- Derivation connections ---------

        pNom_ST.add_empty(pronZeroDeriv_S, HasTail())
        pDat_ST.add_empty(pronZeroDeriv_S, HasTail())
        pLoc_ST.add_empty(pronZeroDeriv_S, HasTail())
        pAbl_ST.add_empty(pronZeroDeriv_S, HasTail())
        pGen_ST.add_empty(pronZeroDeriv_S, HasTail())
        pIns_ST.add_empty(pronZeroDeriv_S, HasTail())

        pronZeroDeriv_S.add_empty(pvVerbRoot_S)

    def connect_verb_after_pronoun(self):
        pvVerbRoot_S.add_empty(pvPresent_S)

        pvVerbRoot_S.add(vWhile_S, "+yken")

        pvVerbRoot_S.add(pvPast_S, "+ydI")

        pvVerbRoot_S.add(pvNarr_S, "+ymIş")

        pvVerbRoot_S.add(pvCond_S, "+ysA")

        # disallow `benin, bizim with A1sg analysis etc.`

        allowA1sgTrans = PreviousGroupContains(pA1pl_S, pP1sg_S).not_()

        allowA1plTrans = PreviousGroupContains(
            pA1sg_S, pA2sg_S, pP1sg_S, pP2sg_S
        ).not_()

        allowA2sgTrans = PreviousGroupContains(pA2pl_S, pP2sg_S).not_()

        allowA2plTrans = PreviousGroupContains(pA2sg_S, pP2pl_S).not_()

        pvPresent_S.add(pvA1sg_ST, "+yIm", allowA1sgTrans)
        pvPresent_S.add(pvA2sg_ST, "sIn", allowA2sgTrans)
        # We do not allow ending with A3sg from empty Present tense.
        pvPresent_S.add_empty(nA3sg_S)
        pvPresent_S.add(pvA1pl_ST, "+yIz", allowA1plTrans)
        pvPresent_S.add(pvA2pl_ST, "sInIz")
        pvPresent_S.add(pvA3pl_ST, "lAr", PreviousGroupContains(pLoc_ST))

        pvPast_S.add(pvA1sg_ST, "m", allowA1sgTrans)
        pvPast_S.add(pvA2sg_ST, "n", allowA2sgTrans)
        pvPast_S.add(pvA1pl_ST, "k", allowA1plTrans)
        pvPast_S.add(pvA2pl_ST, "InIz")
        pvPast_S.add(pvA3pl_ST, "lAr")
        pvPast_S.add_empty(pvA3sg_ST)

        pvNarr_S.add(pvA1sg_ST, "Im", allowA1sgTrans)
        pvNarr_S.add(pvA2sg_ST, "sIn", allowA2sgTrans)
        pvNarr_S.add(pvA1pl_ST, "Iz", allowA1plTrans)
        pvNarr_S.add(pvA2pl_ST, "sInIz")
        pvNarr_S.add(pvA3pl_ST, "lAr")
        pvNarr_S.add_empty(pvA3sg_ST)
        # narr+cons is allowed but not past+cond
        pvNarr_S.add(pvCond_S, "sA")

        pvCond_S.add(pvA1sg_ST, "m", allowA1sgTrans)
        pvCond_S.add(pvA2sg_ST, "n", allowA2sgTrans)
        pvCond_S.add(pvA1pl_ST, "k", allowA1plTrans)
        pvCond_S.add(pvA2pl_ST, "nIz", allowA2plTrans)
        pvCond_S.add_empty(pvA3sg_ST)
        pvCond_S.add(pvA3pl_ST, "lAr")

        rejectNoCopula = CurrentGroupContainsAny(
            pvPast_S, pvCond_S, pvCopBeforeA3pl_S
        ).not_()

        pvA1sg_ST.add(pvCop_ST, "dIr", rejectNoCopula)
        pvA2sg_ST.add(pvCop_ST, "dIr", rejectNoCopula)
        pvA1pl_ST.add(pvCop_ST, "dIr", rejectNoCopula)
        pvA2pl_ST.add(pvCop_ST, "dIr", rejectNoCopula)

        pvA3sg_S.add(pvCop_ST, ">dIr", rejectNoCopula)

        pvA3pl_ST.add(pvCop_ST, "dIr", rejectNoCopula)

        # Copula can come before A3pl.
        pvPresent_S.add(pvCopBeforeA3pl_S, ">dIr")
        pvCopBeforeA3pl_S.add(pvA3pl_ST, "lAr")

    def connect_adverbs(self):
        advNounRoot_ST.add_empty(avZero_S)
        avZero_S.add_empty(avNounAfterAdvRoot_ST)
        avNounAfterAdvRoot_ST.add_empty(avA3sg_S)
        avA3sg_S.add_empty(avPnon_S)
        avPnon_S.add(avDat_ST, "+yA")

        advForVerbDeriv_ST.add_empty(avZeroToVerb_S)
        avZeroToVerb_S.add_empty(nVerb_S)

    def connect_postpositives(self):
        postpRoot_ST.add_empty(postpZero_S)
        postpZero_S.add_empty(nVerb_S)

        # gibi is kind of special.
        gibiGen = self.lexicon.get_item_by_id("gibi_Postp_PCGen")
        gibiNom = self.lexicon.get_item_by_id("gibi_Postp_PCNom")
        sonraAbl = self.lexicon.get_item_by_id("sonra_Postp_PCAbl")
        postpZero_S.add_empty(
            po2nRoot_S, DictionaryItemIsAny(gibiGen, gibiNom, sonraAbl)
        )

        po2nRoot_S.add_empty(po2nA3sg_S)
        po2nRoot_S.add(po2nA3pl_S, "lAr")

        # gibisi, gibim-e, gibi-e, gibi-mize
        po2nA3sg_S.add(po2nP3sg_S, "+sI")
        po2nA3sg_S.add(po2nP1sg_S, "m", DictionaryItemIsAny(gibiGen, gibiNom))
        po2nA3sg_S.add(po2nP2sg_S, "n", DictionaryItemIsAny(gibiGen, gibiNom))
        po2nA3sg_S.add(po2nP1pl_S, "miz", DictionaryItemIsAny(gibiGen, gibiNom))
        po2nA3sg_S.add(po2nP2pl_S, "niz", DictionaryItemIsAny(gibiGen, gibiNom))

        # gibileri
        po2nA3pl_S.add(po2nP3sg_S, "+sI")
        po2nA3pl_S.add_empty(po2nPnon_S)

        po2nP3sg_S.add_all(
            [
                (po2nNom_ST, ""),
                (po2nDat_ST, "nA"),
                (po2nLoc_ST, "ndA"),
                (po2nAbl_ST, "ndAn"),
                (po2nIns_ST, "ylA"),
                (po2nGen_ST, "nIn"),
                (po2nAcc_ST, "nI"),
            ]
        )

        po2nPnon_S.add_all(
            [
                (po2nNom_ST, ""),
                (po2nDat_ST, "A"),
                (po2nLoc_ST, "dA"),
                (po2nAbl_ST, "dAn"),
                (po2nIns_ST, "lA"),
                (po2nGen_ST, "In"),
                (po2nEqu_ST, "cA"),
                (po2nAcc_ST, "I"),
            ]
        )

        po2nP1sg_S.add(po2nDat_ST, "e")
        po2nP2sg_S.add(po2nDat_ST, "e")
        po2nP1pl_S.add(po2nDat_ST, "e")
        po2nP2pl_S.add(po2nDat_ST, "e")

    def connect_verbs(self):
        # Imperative.
        verbRoot_S.add_empty(vImp_S)

        vImp_S.add_all(
            [
                (vA2sg_ST, ""),  # oku
                (vA2sg_ST, "sAnA"),  # oku
                (vA3sg_ST, "sIn"),  # okusun
                (vA2pl_ST, "+yIn"),  # okuyun
                (vA2pl_ST, "+yInIz"),  # okuyunuz
                (vA2pl_ST, "sAnIzA"),  # okuyunuz
                (vA3pl_ST, "sInlAr"),  # okusunlar
            ]
        )

        # Causative suffixes
        # Causes Verb-Verb derivation. There are three forms: "t", "tIr" and "Ir".
        # 1- "t" form is used if verb ends with a vowel, or immediately after "tIr" Causative.
        # 2- "tIr" form is used if verb ends with a consonant or immediately after "t" Causative.
        # 3- "Ir" form appears after some specific verbs but currently we treat them as separate verb.
        # such as "pişmek - pişirmek". Oflazer parses them as causative.

        verbRoot_S.add(
            vCausT_S,
            "t",
            HasRootAttribute(RootAttribute.Causative_t)
                .or_(LastDerivationIs(vCausTir_S))
                .and_not(LastDerivationIsAny(vCausT_S, vPass_S, vAble_S)),
        )

        verbRoot_S.add(
            vCausTir_S,
            ">dIr",
            HasPhoneticAttribute(PhoneticAttribute.LastLetterConsonant).and_not(
                LastDerivationIsAny(vCausTir_S, vPass_S, vAble_S)
            ),
        )

        vCausT_S.add_empty(verbRoot_S)
        vCausTir_S.add_empty(verbRoot_S)

        # Progressive1 suffix. "-Iyor"
        # if last letter is a vowel, this is handled with verbRoot_VowelDrop_S root.
        verbRoot_S.add(vProgYor_S, "Iyor", not_have(PhoneticAttribute.LastLetterVowel))

        # For "aramak", the modified root "ar" connects to verbRoot_VowelDrop_S. Here it is connected to
        # progressive "Iyor" suffix. We use a separate root state for these for convenience.
        verbRoot_VowelDrop_S.add(vProgYor_S, "Iyor")
        vProgYor_S.add_all(
            [
                (vA1sg_ST, "um"),
                (vA2sg_ST, "sun"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "uz"),
                (vA2pl_ST, "sunuz"),
                (vA3pl_ST, "lar"),
                (vCond_S, "sa"),
                (vPastAfterTense_S, "du"),
                (vNarrAfterTense_S, "muş"),
                (vCopBeforeA3pl_S, "dur"),
                (vWhile_S, "ken"),
            ]
        )

        # Progressive - 2 "-mAktA"
        verbRoot_S.add(vProgMakta_S, "mAktA")
        vProgMakta_S.add_all(
            [
                (vA1sg_ST, "yIm"),
                (vA2sg_ST, "sIn"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "yIz"),
                (vA2pl_ST, "sInIz"),
                (vA3pl_ST, "lAr"),
                (vCond_S, "ysA"),
                (vPastAfterTense_S, "ydI"),
                (vNarrAfterTense_S, "ymIş"),
                (vCopBeforeA3pl_S, "dIr"),
                (vWhile_S, "yken"),
            ]
        )

        # Positive Aorist Tense.
        # For single syllable words, it forms as "ar-er". For others "ir-ır-ur-ür"
        # However there are exceptions to it as well. So dictionary items are marked as Aorist_I and
        # Aorist_A.
        verbRoot_S.add(
            vAor_S,
            "Ir",
            HasRootAttribute(RootAttribute.Aorist_I).or_(HasAnySuffixSurface()),
        )
        verbRoot_S.add(
            vAor_S,
            "Ar",
            HasRootAttribute(RootAttribute.Aorist_A).and_(HasAnySuffixSurface().not_()),
        )
        vAor_S.add_all(
            [
                (vA1sg_ST, "Im"),
                (vA2sg_ST, "sIn"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "Iz"),
                (vA2pl_ST, "sInIz"),
                (vA3pl_ST, "lAr"),
                (vPastAfterTense_S, "dI"),
                (vNarrAfterTense_S, "mIş"),
                (vCond_S, "sA"),
                (vCopBeforeA3pl_S, "dIr"),
                (vWhile_S, "ken"),
            ]
        )

        # Negative
        verbRoot_S.add(vNeg_S, "mA", PreviousMorphemeIs(able).not_())

        vNeg_S.add_all(
            [
                (vImp_S, ""),
                (vPast_S, "dI"),
                (vFut_S, "yAcA~k"),
                (vFut_S, "yAcA!ğ"),
                (vNarr_S, "mIş"),
                (vProgMakta_S, "mAktA"),
                (vOpt_S, "yA"),
                (vDesr_S, "sA"),
                (vNeces_S, "mAlI"),
                (vInf1_S, "mAk"),
                (vInf2_S, "mA"),
                (vInf3_S, "yIş"),
                (vActOf_S, "mAcA"),
                (vPastPart_S, "dI~k"),
                (vPastPart_S, "dI!ğ"),
                (vFutPart_S, "yAcA~k"),
                (vFutPart_S, "yAcA!ğ"),
                (vPresPart_S, "yAn"),
                (vNarrPart_S, "mIş"),
                (vSinceDoingSo_S, "yAlI"),
                (vByDoingSo_S, "yArAk"),
                (vHastily_S, "yIver"),
                (vEverSince_S, "yAgör"),
                (vAfterDoing_S, "yIp"),
                (vWhen_S, "yIncA"),
                (vAsLongAs_S, "dIkçA"),
                (vNotState_S, "mAzlI~k"),
                (vNotState_S, "mAzlI!ğ"),
                (vFeelLike_S, "yAsI"),
            ]
        )

        # Negative form is "m" before progressive "Iyor" because last vowel drops.
        # We use a separate negative state for this.
        verbRoot_S.add(vNegProg1_S, "m")
        vNegProg1_S.add(vProgYor_S, "Iyor")

        # Negative Aorist
        # Aorist tense forms differently after negative. It can be "z" or empty.
        vNeg_S.add(vAorNeg_S, "z")
        vNeg_S.add_empty(vAorNegEmpty_S)
        vAorNeg_S.add_all(
            [
                (vA2sg_ST, "sIn"),
                (vA3sg_ST, ""),
                (vA2pl_ST, "sInIz"),
                (vA3pl_ST, "lAr"),
                (vPastAfterTense_S, "dI"),
                (vNarrAfterTense_S, "mIş"),
                (vCond_S, "sA"),
                (vCopBeforeA3pl_S, "dIr"),
                (vWhile_S, "ken"),
            ]
        )

        vAorNegEmpty_S.add(vA1sg_ST, "m")
        vAorNegEmpty_S.add(vA1pl_ST, "yIz")
        # oku-maz-ım TODO: not sure here.
        vNeg_S.add(vAorPartNeg_S, "z")
        vAorPartNeg_S.add_empty(adjAfterVerb_ST)

        # Positive Ability.
        # This makes a Verb-Verb derivation.
        verbRoot_S.add(vAble_S, "+yAbil", LastDerivationIs(vAble_S).not_())

        vAble_S.add_empty(verbRoot_S)

        # Also for ability that comes before negative, we add a new root state.
        # From there only negative connections is possible.
        vAbleNeg_S.add_empty(vAbleNegDerivRoot_S)
        vAbleNegDerivRoot_S.add(vNeg_S, "mA")
        vAbleNegDerivRoot_S.add(vNegProg1_S, "m")

        # it is possible to have abil derivation after negative.
        vNeg_S.add(vAble_S, "yAbil")

        # Unable.
        verbRoot_S.add(vUnable_S, "+yAmA", PreviousMorphemeIs(able).not_())
        # careful here. We copy all outgoing transitions to "unable"
        vUnable_S.copy_outgoing_transitions_from(vNeg_S)
        verbRoot_S.add(vUnableProg1_S, "+yAm")
        vUnableProg1_S.add(vProgYor_S, "Iyor")

        # Infinitive 1 "mAk"
        # Causes Verb to Noun derivation. It is connected to a special noun root state.
        verbRoot_S.add(vInf1_S, "mA~k")
        vInf1_S.add_empty(nounInf1Root_S)

        # Infinitive 2 "mA"
        # Causes Verb to Noun derivation.
        verbRoot_S.add(vInf2_S, "mA")
        vInf2_S.add_empty(noun_S)

        # Infinitive 3 "+yUş"
        # Causes Verb to Noun derivation.
        verbRoot_S.add(vInf3_S, "+yIş")
        vInf3_S.add_empty(noun_S)

        # Agt 3 "+yIcI"
        # Causes Verb to Noun and Adj derivation.
        verbRoot_S.add(vAgt_S, "+yIcI")
        vAgt_S.add_empty(noun_S)
        vAgt_S.add_empty(adjAfterVerb_ST)

        # ActOf "mAcA"
        # Causes Verb to Noun and Adj derivation.
        verbRoot_S.add(vActOf_S, "mAcA")
        vActOf_S.add_empty(nounActOfRoot_S)

        # PastPart "oku-duğ-um"
        verbRoot_S.add(vPastPart_S, ">dI~k")
        verbRoot_S.add(vPastPart_S, ">dI!ğ")
        vPastPart_S.add_empty(noun_S)
        vPastPart_S.add_empty(adjAfterVerb_S)

        # FutPart "oku-yacağ-ım kitap"
        verbRoot_S.add(vFutPart_S, "+yAcA~k")
        verbRoot_S.add(vFutPart_S, "+yAcA!ğ")
        vFutPart_S.add_empty(noun_S, HasTail())
        vFutPart_S.add_empty(adjAfterVerb_S)

        # FutPart "oku-yacağ-ım kitap"
        verbRoot_S.add(vNarrPart_S, "mIş")
        vNarrPart_S.add_empty(adjectiveRoot_ST)

        # AorPart "okunabilir-lik"
        verbRoot_S.add(
            vAorPart_S,
            "Ir",
            HasRootAttribute(RootAttribute.Aorist_I).or_(HasAnySuffixSurface()),
        )
        verbRoot_S.add(
            vAorPart_S,
            "Ar",
            HasRootAttribute(RootAttribute.Aorist_A).and_(HasAnySuffixSurface().not_()),
        )
        vAorPart_S.add_empty(adjAfterVerb_ST)

        # PresPart
        verbRoot_S.add(vPresPart_S, "+yAn")
        vPresPart_S.add_empty(noun_S, HasTail())
        vPresPart_S.add_empty(adjAfterVerb_ST)  # connect to terminal Adj

        # FeelLike
        verbRoot_S.add(vFeelLike_S, "+yAsI")
        vFeelLike_S.add_empty(noun_S, HasTail())
        vFeelLike_S.add_empty(adjAfterVerb_ST)  # connect to terminal Adj

        # NotState
        verbRoot_S.add(vNotState_S, "mAzlI~k")
        verbRoot_S.add(vNotState_S, "mAzlI!ğ")
        vNotState_S.add_empty(noun_S)

        # reciprocal
        # TODO: for reducing ambiguity for now remove reciprocal

        # verbRoot_S.add(vRecip_S, "Iş", not_haveAny(RootAttribute.Reciprocal, RootAttribute.NonReciprocal)
        #     .and_not(new ContainsMorpheme(recip)))

        vRecip_S.add_empty(verbRoot_S)
        vImplicitRecipRoot_S.add_empty(vRecip_S)

        # reflexive
        vImplicitReflexRoot_S.add_empty(vReflex_S)
        vReflex_S.add_empty(verbRoot_S)

        # Passive
        # Causes Verb-Verb derivation. Passive morpheme has three forms.
        # 1- If Verb ends with a vowel: "In"
        # 2- If Verb ends with letter 'l' : "InIl"
        # 3- If Verb ends with other consonants: "nIl"
        # When loading dictionary, first and second case items are marked with Passive_In

        verbRoot_S.add(
            vPass_S,
            "In",
            HasRootAttribute(RootAttribute.Passive_In).and_not(ContainsMorpheme(pass_)),
        )
        verbRoot_S.add(
            vPass_S,
            "InIl",
            HasRootAttribute(RootAttribute.Passive_In).and_not(ContainsMorpheme(pass_)),
        )
        verbRoot_S.add(
            vPass_S,
            "+nIl",
            PreviousStateIsAny(vCausT_S, vCausTir_S)
                .or_(not_have(RootAttribute.Passive_In))
                .and_not(ContainsMorpheme(pass_)),
        )
        vPass_S.add_empty(verbRoot_S)

        # Condition "oku-r-sa"
        vCond_S.add_all(
            [
                (vA1sg_ST, "m"),
                (vA2sg_ST, "n"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "k"),
                (vA2pl_ST, "nIz"),
                (vA3pl_ST, "lAr"),
            ]
        )

        # Past "oku-du"
        verbRoot_S.add(vPast_S, ">dI")
        vPast_S.add_all(
            [
                (vA1sg_ST, "m"),
                (vA2sg_ST, "n"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "k"),
                (vA2pl_ST, "nIz"),
                (vA3pl_ST, "lAr"),
            ]
        )

        vPast_S.add(vCond_S, "ysA")

        # Narrative "oku-muş"
        verbRoot_S.add(vNarr_S, "mIş")
        vNarr_S.add_all(
            [
                (vA1sg_ST, "Im"),
                (vA2sg_ST, "sIn"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "Iz"),
                (vA2pl_ST, "sInIz"),
                (vA3pl_ST, "lAr"),
            ]
        )

        vNarr_S.add(vCond_S, "sA")
        vNarr_S.add(vPastAfterTense_S, "tI")
        vNarr_S.add(vCopBeforeA3pl_S, "tIr")
        vNarr_S.add(vWhile_S, "ken")
        vNarr_S.add(vNarrAfterTense_S, "mIş")

        # Past after tense "oku-muş-tu"
        vPastAfterTense_S.add_all(
            [
                (vA1sg_ST, "m"),
                (vA2sg_ST, "n"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "k"),
                (vA2pl_ST, "nIz"),
                (vA3pl_ST, "lAr"),
            ]
        )

        # Narrative after tense "oku-r-muş"
        vNarrAfterTense_S.add_all(
            [
                (vA1sg_ST, "Im"),
                (vA2sg_ST, "sIn"),
                # for preventing yap+ar+lar(A3pl)+mış+A3sg
                (vA3sg_ST, ""),
                (vA1pl_ST, "Iz"),
                (vA2pl_ST, "sInIz"),
                (vA3pl_ST, "lAr"),
            ]
        )

        vNarrAfterTense_S.add(vWhile_S, "ken")
        vNarrAfterTense_S.add(vCopBeforeA3pl_S, "tIr")

        # Future "oku-yacak"
        verbRoot_S.add(vFut_S, "+yAcA~k")
        verbRoot_S.add(vFut_S, "+yAcA!ğ")

        vFut_S.add_all(
            [
                (vA1sg_ST, "Im"),
                (vA2sg_ST, "sIn"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "Iz"),
                (vA2pl_ST, "sInIz"),
                (vA3pl_ST, "lAr"),
            ]
        )

        vFut_S.add(vCond_S, "sA")
        vFut_S.add(vPastAfterTense_S, "tI")
        vFut_S.add(vNarrAfterTense_S, "mIş")
        vFut_S.add(vCopBeforeA3pl_S, "tIr")
        vFut_S.add(vWhile_S, "ken")

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

        vDeYeRoot_S.add_all(
            [
                (vFut_S, "yece~k", diYiCondition),
                (vFut_S, "yece!ğ", diYiCondition),
                (vProgYor_S, "yor", diYiCondition),
                (vAble_S, "yebil", diYiCondition),
                (vAbleNeg_S, "ye", diYiCondition),
                (vInf3_S, "yiş", RootSurfaceIsAny("yi")),
                (vFutPart_S, "yece~k", diYiCondition),
                (vFutPart_S, "yece!ğ", diYiCondition),
                (vPresPart_S, "yen", diYiCondition),
                (vEverSince_S, "yegel", diYiCondition.and_(cMultiVerb)),
                (vRepeat_S, "yedur", diYiCondition.and_(cMultiVerb)),
                (vRepeat_S, "yegör", diYiCondition.and_(cMultiVerb)),
                (vAlmost_S, "yeyaz", diYiCondition.and_(cMultiVerb)),
                (vStart_S, "yekoy", diYiCondition.and_(cMultiVerb)),
                (vSinceDoingSo_S, "yeli", diYiCondition),
                (vByDoingSo_S, "yerek", diYiCondition),
                (vFeelLike_S, "yesi", diYiCondition),
                (vAfterDoing_S, "yip", diYiCondition),
                (vWithoutBeingAbleToHaveDoneSo_S, "yemeden", diYiCondition),
                (vOpt_S, "ye", diYiCondition),
            ]
        )

        vDeYeRoot_S.add_all(
            [
                (vCausTir_S, "dir", deYeCondition),
                (vPass_S, "n", deYeCondition),
                (vPass_S, "nil", deYeCondition),
                (vPast_S, "di", deYeCondition),
                (vNarr_S, "miş", deYeCondition),
                (vAor_S, "r", deYeCondition),
                (vNeg_S, "me", deYeCondition),
                (vNegProg1_S, "m", deYeCondition),
                (vProgMakta_S, "mekte", deYeCondition),
                (vDesr_S, "se", deYeCondition),
                (vInf1_S, "mek", deYeCondition),
                (vInf2_S, "me", deYeCondition),
                (vInf3_S, "yiş", RootSurfaceIsAny("de")),
                (vPastPart_S, "di~k", deYeCondition),
                (vPastPart_S, "di!ğ", deYeCondition),
                (vNarrPart_S, "miş", deYeCondition),
                (vHastily_S, "yiver", diYiCondition.and_(cMultiVerb)),
                (vAsLongAs_S, "dikçe"),
                (vWithoutHavingDoneSo_S, "meden"),
                (vWithoutHavingDoneSo_S, "meksizin"),
                (vNeces_S, "meli"),
                (vNotState_S, "mezli~k"),
                (vNotState_S, "mezli!ğ"),
                (vImp_S, "", RootSurfaceIs("de")),
                (vImpYemekYe_S, "", RootSurfaceIs("ye")),
                (vImpYemekYi_S, "", RootSurfaceIs("yi")),
            ]
        )

        # verb `yemek` has an exception case for some imperatives.
        vImpYemekYi_S.add_all([(vA2pl_ST, "yin"), (vA2pl_ST, "yiniz")])

        vImpYemekYe_S.add_all(
            [
                (vA2sg_ST, ""),
                (vA2sg_ST, "sene"),
                (vA3sg_ST, "sin"),
                (vA2pl_ST, "senize"),
                (vA3pl_ST, "sinler"),
            ]
        )

        # Optative (gel-e, gel-eyim gel-me-ye-yim)
        verbRoot_S.add(vOpt_S, "+yA")
        vOpt_S.add_all(
            [
                (vA1sg_ST, "yIm"),
                (vA2sg_ST, "sIn"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "lIm"),
                (vA2pl_ST, "sInIz"),
                (vA3pl_ST, "lAr"),
                (vPastAfterTense_S, "ydI"),
                (vNarrAfterTense_S, "ymIş"),
            ]
        )

        # Desire (gel-se, gel-se-m gel-me-se-m)
        verbRoot_S.add(vDesr_S, "sA")
        vDesr_S.add_all(
            [
                (vA1sg_ST, "m"),
                (vA2sg_ST, "n"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "k"),
                (vA2pl_ST, "nIz"),
                (vA3pl_ST, "lAr"),
                (vPastAfterTense_S, "ydI"),
                (vNarrAfterTense_S, "ymIş"),
            ]
        )

        verbRoot_S.add(vNeces_S, "mAlI")
        vNeces_S.add_all(
            [
                (vA1sg_ST, "yIm"),
                (vA2sg_ST, "sIn"),
                (vA3sg_ST, ""),
                (vA1pl_ST, "yIz"),
                (vA2pl_ST, "sInIz"),
                (vA3pl_ST, "lAr"),
                (vPastAfterTense_S, "ydI"),
                (vCond_S, "ysA"),
                (vNarrAfterTense_S, "ymIş"),
                (vCopBeforeA3pl_S, "dIr"),
                (vWhile_S, "yken"),
            ]
        )

        # A3pl exception case.
        # A3pl can appear before or after some tense suffixes.
        # "yapar-lar-dı" - "yapar-dı-lar"
        # For preventing "yapar-dı-lar-dı", are added.

        previousNotPastNarrCond = PreviousStateIsAny(
            vPastAfterTense_S, vNarrAfterTense_S, vCond_S
        ).not_()
        vA3pl_ST.add(vPastAfterTense_ST, "dI", previousNotPastNarrCond)
        vA3pl_ST.add(vNarrAfterTense_ST, "mIş", previousNotPastNarrCond)
        vA3pl_ST.add(vCond_ST, "sA", previousNotPastNarrCond)

        a3plCopWhile = PreviousMorphemeIsAny(prog1, prog2, neces, fut, narr, aor)
        vA3pl_ST.add(vCop_ST, "dIr", a3plCopWhile)
        vA3pl_ST.add(vWhile_S, "ken", a3plCopWhile)

        a3sgCopWhile = PreviousMorphemeIsAny(prog1, prog2, neces, fut, narr, aor)
        vA1sg_ST.add(vCop_ST, "dIr", a3sgCopWhile)
        vA2sg_ST.add(vCop_ST, "dIr", a3sgCopWhile)
        vA3sg_ST.add(vCop_ST, ">dIr", a3sgCopWhile)
        vA1pl_ST.add(vCop_ST, "dIr", a3sgCopWhile)
        vA2pl_ST.add(vCop_ST, "dIr", a3sgCopWhile)

        vCopBeforeA3pl_S.add(vA3pl_ST, "lAr")

        # Allow Past+A2pl+Cond  Past+A2sg+Cond (geldinse, geldinizse)

        previousPast = PreviousMorphemeIs(past).and_not(ContainsMorpheme(cond, desr))
        vA2pl_ST.add(vCondAfterPerson_ST, "sA", previousPast)
        vA2sg_ST.add(vCondAfterPerson_ST, "sA", previousPast)
        vA1sg_ST.add(vCondAfterPerson_ST, "sA", previousPast)
        vA1pl_ST.add(vCondAfterPerson_ST, "sA", previousPast)

        verbRoot_S.add(vEverSince_S, "+yAgel", cMultiVerb)
        verbRoot_S.add(vRepeat_S, "+yAdur", cMultiVerb)
        verbRoot_S.add(vRepeat_S, "+yAgör", cMultiVerb)
        verbRoot_S.add(vAlmost_S, "+yAyaz", cMultiVerb)
        verbRoot_S.add(vHastily_S, "+yIver", cMultiVerb)
        verbRoot_S.add(vStay_S, "+yAkal", cMultiVerb)
        verbRoot_S.add(vStart_S, "+yAkoy", cMultiVerb)

        vEverSince_S.add_empty(verbRoot_S)
        vRepeat_S.add_empty(verbRoot_S)
        vAlmost_S.add_empty(verbRoot_S)
        vHastily_S.add_empty(verbRoot_S)
        vStay_S.add_empty(verbRoot_S)
        vStart_S.add_empty(verbRoot_S)

        vA3sg_ST.add(vAsIf_S, ">cAsInA", PreviousMorphemeIsAny(aor, narr))

        verbRoot_S.add(vWhen_S, "+yIncA")
        verbRoot_S.add(vSinceDoingSo_S, "+yAlI")
        verbRoot_S.add(vByDoingSo_S, "+yArAk")
        verbRoot_S.add(vAdamantly_S, "+yAsIyA")
        verbRoot_S.add(vAfterDoing_S, "+yIp")
        verbRoot_S.add(vWithoutBeingAbleToHaveDoneSo_S, "+yAmAdAn")
        verbRoot_S.add(vAsLongAs_S, ">dIkçA")
        verbRoot_S.add(vWithoutHavingDoneSo_S, "mAdAn")
        verbRoot_S.add(vWithoutHavingDoneSo_S, "mAksIzIn")

        vAsIf_S.add_empty(advRoot_ST)
        vSinceDoingSo_S.add_empty(advRoot_ST)
        vByDoingSo_S.add_empty(advRoot_ST)
        vAdamantly_S.add_empty(advRoot_ST)
        vAfterDoing_S.add_empty(advRoot_ST)
        vWithoutBeingAbleToHaveDoneSo_S.add_empty(advRoot_ST)
        vAsLongAs_S.add_empty(advRoot_ST)
        vWithoutHavingDoneSo_S.add_empty(advRoot_ST)
        vWhile_S.add_empty(advRoot_ST)
        vWhen_S.add_empty(advNounRoot_ST)

    def connect_question(self):
        # mı
        questionRoot_S.add_empty(qPresent_S)
        # mıydı
        questionRoot_S.add(qPast_S, "ydI")
        # mıymış
        questionRoot_S.add(qNarr_S, "ymIş")

        # mıyım
        qPresent_S.add(qA1sg_ST, "yIm")
        # mısın
        qPresent_S.add(qA2sg_ST, "sIn")
        # mı
        qPresent_S.add_empty(qA3sg_ST)

        # mıydım
        qPast_S.add(qA1sg_ST, "m")
        # mıymışım
        qNarr_S.add(qA1sg_ST, "Im")

        # mıydın
        qPast_S.add(qA2sg_ST, "n")
        # mıymışsın
        qNarr_S.add(qA2sg_ST, "sIn")

        # mıydık
        qPast_S.add(qA1pl_ST, "k")
        # mıymışız
        qNarr_S.add(qA1pl_ST, "Iz")
        # mıyız
        qPresent_S.add(qA1pl_ST, "+yIz")

        # mıydınız
        qPast_S.add(qA2pl_ST, "InIz")
        # mıymışsınız
        qNarr_S.add(qA2pl_ST, "sInIz")
        # mısınız
        qPresent_S.add(qA2pl_ST, "sInIz")

        # mıydılar
        qPast_S.add(qA3pl_ST, "lAr")
        # mıymışlar
        qNarr_S.add(qA3pl_ST, "lAr")

        # mıydı
        qPast_S.add_empty(qA3sg_ST)
        # mıymış
        qNarr_S.add_empty(qA3sg_ST)

        # for not allowing "mı-ydı-m-dır"

        rejectNoCopula = CurrentGroupContainsAny(qPast_S).not_()

        # mıyımdır
        qA1sg_ST.add(qCop_ST, "dIr", rejectNoCopula)
        # mısındır
        qA2sg_ST.add(qCop_ST, "dIr", rejectNoCopula)
        # mıdır
        qA3sg_ST.add(qCop_ST, ">dIr", rejectNoCopula)
        # mıyızdır
        qA1pl_ST.add(qCop_ST, "dIr", rejectNoCopula)
        # mısınızdır
        qA2pl_ST.add(qCop_ST, "dIr", rejectNoCopula)

        # Copula can come before A3pl.
        qPresent_S.add(pvCopBeforeA3pl_S, "dIr")
        qCopBeforeA3pl_S.add(qA3pl_ST, "lAr")

    def connect_imek(self):
        # idi
        imekRoot_S.add(imekPast_S, "di")
        # imiş
        imekRoot_S.add(imekNarr_S, "miş")
        # ise
        imekRoot_S.add(imekCond_S, "se")

        # idim, idin, idi, idik, idiniz, idiler
        imekPast_S.add(imekA1sg_ST, "m")
        imekPast_S.add(imekA2sg_ST, "n")
        imekPast_S.add_empty(imekA3sg_ST)
        imekPast_S.add(imekA1pl_ST, "k")
        imekPast_S.add(imekA2pl_ST, "niz")
        imekPast_S.add(imekA3pl_ST, "ler")

        # imişim, imişsin, imiş, imişiz, imişsiniz, imişler
        imekNarr_S.add(imekA1sg_ST, "im")
        imekNarr_S.add(imekA2sg_ST, "sin")
        imekNarr_S.add_empty(imekA3sg_ST)
        imekNarr_S.add(imekA1pl_ST, "iz")
        imekNarr_S.add(imekA2pl_ST, "siniz")
        imekNarr_S.add(imekA3pl_ST, "ler")

        imekPast_S.add(imekCond_S, "yse")
        imekNarr_S.add(imekCond_S, "se")

        imekCond_S.add(imekA1sg_ST, "m")
        imekCond_S.add(imekA2sg_ST, "n")
        imekCond_S.add_empty(imekA3sg_ST)
        imekCond_S.add(imekA1pl_ST, "k")
        imekCond_S.add(imekA2pl_ST, "niz")
        imekCond_S.add(imekA3pl_ST, "ler")

        # for not allowing "i-di-m-dir"

        rejectNoCopula = CurrentGroupContainsAny(imekPast_S).not_()

        # imişimdir, imişsindir etc.
        imekA1sg_ST.add(imekCop_ST, "dir", rejectNoCopula)
        imekA2sg_ST.add(imekCop_ST, "dir", rejectNoCopula)
        imekA3sg_ST.add(imekCop_ST, "tir", rejectNoCopula)
        imekA1pl_ST.add(imekCop_ST, "dir", rejectNoCopula)
        imekA2pl_ST.add(imekCop_ST, "dir", rejectNoCopula)
        imekA3pl_ST.add(imekCop_ST, "dir", rejectNoCopula)

    def handle_post_processing_connections(self):
        # Passive has an exception for some verbs like `kavurmak` or `savurmak`.
        # add passive state connection to modified root `kavr` etc.
        verbLastVowelDropModRoot_S.add(vPass_S, "Il")
        # for not allowing `kavur-ul` add all verb connections to
        # unmodified `kavur` root and remove only the passive.
        verbLastVowelDropUnmodRoot_S.copy_outgoing_transitions_from(verbRoot_S)
        verbLastVowelDropUnmodRoot_S.remove_transitions_to(pass_)

    def get_root_state(self, dict_item, attrs=None):
        root = self.item_root_states.get(dict_item.id_)
        attrs = (
            attrs.copy()
            if attrs is not None
            else calculate_phonetic_attributes(dict_item.pronunciation)
        )
        if root is not None:
            return root
        # Verbs like "aramak" drops their last vowel when  connected to "Iyor" Progressive suffix.
        # those modified roots are connected to a separate root state called verbRoot_VowelDrop_S.
        if PhoneticAttribute.LastLetterDropped in attrs:
            return verbRoot_VowelDrop_S
        if dict_item.has_attribute(RootAttribute.Reciprocal):
            return vImplicitRecipRoot_S
        if dict_item.has_attribute(RootAttribute.Reflexive):
            return vImplicitReflexRoot_S
        if dict_item.primary_pos == PrimaryPos.Noun:
            if dict_item.secondary_pos == SecondaryPos.ProperNoun:
                return nounProper_S
            elif dict_item.secondary_pos == SecondaryPos.Abbreviation:
                return nounAbbrv_S
            elif dict_item.secondary_pos in [
                SecondaryPos.Email,
                SecondaryPos.Url,
                SecondaryPos.HashTag,
                SecondaryPos.Mention,
            ]:
                return nounProper_S
            elif dict_item.secondary_pos in [
                SecondaryPos.Emoticon,
                SecondaryPos.RomanNumeral,
            ]:
                return nounNoSuffix_S
            if dict_item.has_attribute(RootAttribute.CompoundP3sgRoot):
                return nounCompoundRoot_S
            else:
                return noun_S
        elif dict_item.primary_pos == PrimaryPos.Adjective:
            return adjectiveRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Pronoun:
            if dict_item.secondary_pos == SecondaryPos.PersonalPron:
                return pronPers_S
            if dict_item.secondary_pos == SecondaryPos.DemonstrativePron:
                return pronDemons_S
            elif dict_item.secondary_pos == SecondaryPos.QuantitivePron:
                return pronQuant_S
            elif dict_item.secondary_pos == SecondaryPos.QuestionPron:
                return pronQues_S
            elif dict_item.secondary_pos == SecondaryPos.ReflexivePron:
                return pronReflex_S
            else:
                return pronQuant_S
        elif dict_item.primary_pos == PrimaryPos.Adverb:
            return advRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Conjunction:
            return conjRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Question:
            return questionRoot_S
        elif dict_item.primary_pos == PrimaryPos.Interjection:
            return interjRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Verb:
            return verbRoot_S
        elif dict_item.primary_pos == PrimaryPos.Punctuation:
            return puncRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Determiner:
            return detRoot_ST
        elif dict_item.primary_pos == PrimaryPos.PostPositive:
            return postpRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Numeral:
            return numeralRoot_ST
        elif dict_item.primary_pos == PrimaryPos.Duplicator:
            return dupRoot_ST
        else:
            return noun_S


class MorphemeTransition:
    """
    Represents a transition in morphotactics graph.
    :param condition: Defines the condition(s) to allow or block a graph visitor (SearchPath).
    A condition can be a single or a group of objects that has Condition interface.
    For example, if condition is HasPhoneticAttribute(LastLetterVowel), and SearchPath's last
    letter is a consonant, it cannot pass this transition.
    """

    def __init__(
        self, from_: MorphemeState, to_: MorphemeState, condition: Condition = None
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
        attrs: Set = None,
        surface: str = None,
    ):
        super().__init__(root_S, to_, None)
        if surface:
            if tr.is_upper(surface[0]):
                print(f"Something wrong, generating StemTransition capitalized: {surface}")
        else:
            if tr.is_upper(dict_item.root[0]):
                print(f"Something ELSE is wrong: generating StemTransition capitalized from dictitem: {dict_item.root}")
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

    def __init__(self, from_, to_, surface_template=None, condition=None):
        if from_ is None or to_ is None:
            raise ValueError(f"Suffix transition cannot have empty from and to points")
        super().__init__(from_, to_, condition)
        self.surface_template = "" if surface_template is None else surface_template
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

    def can_pass(self, path):
        return self.condition is None or self.condition.accept(path)

    def connect(self):
        self.from_.add_outgoing([self])
        self.to_.add_incoming([self])

    # adds vowel-consonant expectation related automatically.
    # TODO: consider moving this to morphotactics somehow.
    def parse_conditions_from_template(self):
        if self.surface_template is None or len(self.surface_template) == 0:
            return
        lower = tr.lower(self.surface_template)
        c = None
        first_char_is_vowel = tr.is_vowel(lower[0])
        if lower.startswith(">") or not first_char_is_vowel:
            c = not_have(PhoneticAttribute.ExpectsVowel)

        if (lower.startswith("+") and tr.is_lower(lower[1])) or first_char_is_vowel:
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
    def __init__(self, surface, lexical_transition):
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
    transition: SurfaceTransition, phonetic_attributes: Set[PhoneticAttribute]
) -> str:
    index = 0
    result = []
    for token in transition.token_list:
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
        index += 1
    return "".join(result)


class SuffixTemplateToken:
    def __init__(self, type_, letter, append=False):
        self.type_ = type_
        self.letter = letter
        self.append = append

    def __str__(self):
        return f"({self.type_}:{self.letter})"

    def __repr__(self):
        return str(self)


class SuffixTemplateTokenizer:
    def __init__(self, word):
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
        transitions: List[SurfaceTransition],
        phonetic_attributes: Set[PhoneticAttribute],
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
    def initial(cls, stem_transition: StemTransition, tail: str):
        morphemes = []
        root = SurfaceTransition(stem_transition.surface, stem_transition)
        morphemes.append(root)
        return cls(
            tail,
            stem_transition.to_,
            morphemes,
            stem_transition.attrs,
            stem_transition.to_.terminal,
        )

    def __str__(self):
        st = self.stem_transition
        morpheme_str = " + ".join([str(tran) for tran in self.transitions])
        return f"<({st.dict_item.id_})(-{self.tail})({morpheme_str})>"

    def __repr__(self):
        return f"SearchPath({self.dict_item.id_}) (-{self.tail})({self.transitions})"

    def copy(self, surface_node: SurfaceTransition, pa: set[PhoneticAttribute] | None = None):
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
        new_tail = self.tail[len(surface_node.surface):]
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
    def stem_transition(self):
        return self.transitions[0].lexical_transition

    @property
    def previous_state(self):
        if len(self.transitions) < 2:
            return None
        return self.transitions[-2].state

    @property
    def is_terminal(self):
        return self.terminal

    def has_dictionary_item(self, dict_item):
        return self.stem_transition.item == dict_item

    @property
    def last_transition(self):
        return self.transitions[-1]

    @property
    def dict_item(self):
        return self.stem_transition.dict_item
