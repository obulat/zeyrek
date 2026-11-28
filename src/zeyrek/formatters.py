from abc import ABC
from typing import ClassVar

from zeyrek.attributes import PrimaryPos, SecondaryPos
from zeyrek.morphotactics import Morpheme
from zeyrek.rulebasedanalyzer import SingleAnalysis

cases = ["Nom", "Dat", "Acc", "Abl", "Loc", "Ins", "Gen", "Equ"]


def format_dict_item(lemma, ppos, spos) -> str:
    """Formats information about analysis dictionary item."""
    spos_string = "" if spos is None else f",{spos}"
    return f"[{lemma}:{ppos}{spos_string}] "


def is_new_word(morpheme: Morpheme) -> bool:
    """
    A derivational suffix, such as "-ki" in "evdekiler", starts a new word, which
    has its own case and agreement. The copula "Zero" keeps them: "evdeyim" is still
    in the locative.
    """
    return morpheme.derivational and morpheme.id_ != "Zero"


class Formatter:
    """Abstract formatter class."""

    def format(self, analysis: SingleAnalysis) -> str:
        raise NotImplementedError

    def format_all(self, analyses: list[SingleAnalysis]) -> str:
        raise NotImplementedError


class UDFormatter(Formatter, ABC):
    possessives: ClassVar[dict[str, tuple[str, str]]] = {
        "P1sg": ("|Number[psor]=Sing", "|Person[psor]=1"),
        "P1pl": ("|Number[psor]=Plur", "|Person[psor]=1"),
        "P2sg": ("|Number[psor]=Sing", "|Person[psor]=2"),
        "P2pl": ("|Number[psor]=Plur", "|Person[psor]=2"),
        "P3sg": ("|Number[psor]=Sing", "|Person[psor]=3"),
        "P3pl": ("|Number[psor]=Plur", "|Person[psor]=3"),
    }

    agreement_values: ClassVar[dict[str, tuple[str, str]]] = {
        "A1sg": ("Sing", "1"),
        "A1pl": ("Plur", "1"),
        "A2sg": ("Sing", "2"),
        "A2pl": ("Plur", "2"),
        "A3sg": ("Sing", "3"),
        "A3pl": ("Plur", "3"),
    }

    def __init__(self, add_surface=True):
        self.add_surface = add_surface

    def format_nominal(self, analysis: SingleAnalysis) -> str:
        """UD features of a noun or an adjective, after its derivations.

        A noun or an adjective can become a verb, as ``güzeldi``
        (Adj+Zero+Verb+Past+A3sg) or ``evdeyim`` (Noun+A3sg+Loc+Zero+Verb+Pres+A1sg),
        and then gets the features of a verb. An adjective has no features in UD,
        and an adjective that becomes a noun, as ``kırmızıya``, gets the features of
        a noun.
        """
        if analysis.pos == PrimaryPos.Verb:
            return self.format_verb(analysis)
        if analysis.pos == PrimaryPos.Noun:
            return self.format_noun(analysis)
        return "_"

    @staticmethod
    def format_noun(analysis: SingleAnalysis) -> str:
        noun_str = "{}Case={}|Number={}{}|Person={}{}"
        case = ""
        number = ""
        person = ""
        number_psor = ""
        person_psor = ""
        for m in analysis.morphemes:
            morph = m[0]
            if is_new_word(morph):
                case = number = person = number_psor = person_psor = ""
            if morph.id_ in cases:
                case = morph.id_
            possessive_value = UDFormatter.possessives.get(morph.id_)
            agreement_value = UDFormatter.agreement_values.get(morph.id_)
            if possessive_value is not None:
                number_psor, person_psor = possessive_value
            if agreement_value is not None:
                number, person = agreement_value

        if case == "":
            case = "Nom"
        if analysis.dict_item.secondary_pos == SecondaryPos.Abbreviation:
            abbr = "Abbr=Yes|"
        else:
            abbr = ""
        return noun_str.format(abbr, case, number, number_psor, person, person_psor)

    @staticmethod
    def format_num(analysis: SingleAnalysis) -> str:
        return f"NumType={analysis.dict_item.secondary_pos.value}"

    @staticmethod
    def format_pron(analysis: SingleAnalysis) -> str:
        prontypestr = analysis.dict_item.secondary_pos.value

        if prontypestr == "Demons":
            prontype = "|PronType=Dem"
        elif prontypestr == "Pers":
            prontype = "|PronType=Prs"
        elif prontypestr == "Ques":
            prontype = ""
        elif prontypestr == "Reflex":
            prontype = "|Reflex=Yes"
        else:
            prontype = f"|PronType={prontypestr}"
        person = ""
        number = ""
        case = ""
        number_psor = ""
        person_psor = ""
        for m in analysis.morphemes:
            morph = m[0]
            agreement_value = UDFormatter.agreement_values.get(morph.id_)
            if agreement_value is not None:
                number, person = agreement_value
            if prontypestr in ["Reflex", "Quant"]:
                psor = UDFormatter.possessives.get(morph.id_)
                if psor is not None:
                    number_psor, person_psor = psor
            if morph.id_ in cases:
                case = morph.id_
        if case == "":
            case = "Nom"
        pron_str = "Case={case}|Number={number}{number_psor}|Person={person}{person_psor}{prontype}"

        return pron_str.format(
            case=case,
            number=number,
            number_psor=number_psor,
            person_psor=person_psor,
            person=person,
            prontype=prontype,
        )

    @staticmethod
    def format_verb(analysis: SingleAnalysis) -> str:
        aspect = ""
        mood = ""
        number = ""
        person = ""
        polarity = ""
        tense = ""
        case = ""
        verb_form = ""
        number_psor = ""
        person_psor = ""
        evident = ""
        voice = ""
        register = ""

        last_part = ""
        morph_ids = [_[0].id_ for _ in analysis.morphemes]

        for k, m in enumerate(analysis.morphemes):
            morph = m[0]
            if is_new_word(morph):
                case = ""
            if morph.id_ in cases:
                case = f"|Case={morph.id_}"

            agreement_value = UDFormatter.agreement_values.get(morph.id_)
            if agreement_value is not None and k == len(analysis.morphemes) - 1:
                number, person = agreement_value
            possessive_value = UDFormatter.possessives.get(morph.id_)
            if possessive_value is not None:
                number_psor, person_psor = possessive_value
            if morph.id_ == "Prog1":
                register = "|Polite=Infm"
            elif morph.id_ == "Prog2":
                register = "|Polite=Form"
            if morph.id_ in ["Past", "Pres", "Fut"]:
                if tense == "Past" and morph.id_ == "Past":
                    tense = "Pqp"

                elif tense == "":
                    tense = morph.id_
                # if verb_form == 'Part':
                #     tense = 'Pqp'
            if morph.id_ == "PastPart":
                tense = "Past"
            elif morph.id_ == "FutPart":
                tense = "Fut"
                verb_form = "Part"
            if morph.id_ == "Aor":
                aspect = "Hab"
            elif morph.id_ == "AorPart":
                aspect = "Hab"
                verb_form = "Part"
            elif morph.id_ == "NarrPart":
                tense = "Past"
                verb_form = "Part"
                evident = "|Evident=Nfh"
            if morph.id_ == "Caus":
                voice = "|Voice=Cau"
            elif morph.id_ == "Narr":
                if "Past" not in morph_ids:
                    evident = "|Evident=Nfh"
                # "okuyacakmış" stays in the future tense.
                if tense == "":
                    tense = "Past"
            elif morph.id_ == "Pass":
                voice = "|Voice=Pass"
            if morph.id_ in ["PresPart", "PastPart"]:
                verb_form = "Part"
            if morph.id_ == "Noun" and verb_form == "" and k > 0:
                verb_form = "Vnoun"
            if morph.id_ == "Opt":
                mood = "Opt"
            elif morph.id_ in ["Desr", "Cond"]:
                mood = "Cnd"
            elif morph.id_ in ["Unable", "Able"]:
                mood = "Pot"
            elif morph.id_ == "Imp":
                mood = "Imp"
            if morph.id_ in ["Neg", "Unable"]:
                polarity = "Neg"
            if morph.id_ in ["Prog1", "Prog2"]:
                aspect = "Prog"
            if morph.id_ == "Adv":
                verb_form = "Conv"
        if polarity.strip() == "":
            polarity = "Pos"
        if tense.strip() == "":
            tense = "Pres"
        if mood.strip() == "":
            mood = "Ind"
        if aspect.strip() == "":
            aspect = "Perf"

        if verb_form != "":
            last_part += f"|VerbForm={verb_form}"
            if verb_form == "Vnoun" and case == "":
                case = "|Case=Nom"
        if number != "":
            number = "|Number=" + number if verb_form == "" else ""
        if person != "":
            person = "|Person=" + person if verb_form == "" else ""
        # A noun root that becomes a verb, as "evdeyim", is not a verbal noun.
        if "Noun" in morph_ids[1:]:
            noun_deriv = morph_ids.index("Noun", 1)
            for id_ in morph_ids[noun_deriv:]:
                if id_ in cases:
                    case = f"|Case={id_}"
                if case == "":
                    case = "|Case=Nom"
        if "Fut" in morph_ids and "Past" in morph_ids:
            tense = "Fut,Past"
        return (
            f"Aspect={aspect}{evident}{case}|Mood={mood}"
            f"{number_psor}{number}{person_psor}{person}"
            f"|Polarity={polarity}{register}|Tense={tense}{last_part}{voice}"
        )

    def format(self, analysis: SingleAnalysis) -> str:
        pos = analysis.dict_item.primary_pos.value
        if pos in ("Noun", "Adj"):
            return self.format_nominal(analysis)
        elif pos == "Verb":
            return self.format_verb(analysis)
        elif pos == "Pron":
            return self.format_pron(analysis)
        elif pos == "Num":
            return self.format_num(analysis)

        # result = f"[{analysis.dict_item.lemma}:{analysis.dict_item.primary_pos.value}"
        # if analysis.dict_item.secondary_pos != SecondaryPos.NONE:
        #     result = (
        #         f"{result},{analysis.dict_item.secondary_pos.name}] "
        #     )  # TODO: check name works
        # else:
        #     result = f"{result}] "
        result = format_dict_item(
            analysis.dict_item.lemma,
            analysis.dict_item.primary_pos.value,
            analysis.dict_item.secondary_pos.value,
        )
        result += self.format_morphemes(stem=analysis.stem, surfaces=analysis.morphemes)
        return result

    def format_morphemes(self, stem: str, surfaces: list[tuple[Morpheme, str]]) -> str:
        result = []
        if self.add_surface:
            result.append(f"{stem}:")
        result.append(surfaces[0][0].id_)
        if len(surfaces) > 1 and not surfaces[1][0].derivational:
            result.append("+")
        for i, sf in enumerate(surfaces):
            if i == 0:
                continue
            m, surface = sf
            if m.derivational:
                result.append("|")
            if self.add_surface and len(surface) > 0:
                result.append(f"{surface}:")
            result.append(m.id_)
            if m.derivational:
                result.append("→")
            elif i < len(surfaces) - 1 and not surfaces[i + 1][0].derivational:
                result.append("+")
        return "".join(result)


class DefaultFormatter(Formatter, ABC):
    def __init__(self, add_surface=True):
        self.add_surface = add_surface

    def format(self, analysis: SingleAnalysis) -> str:
        result = f"[{analysis.dict_item.lemma}:{analysis.dict_item.primary_pos.value}"
        if analysis.dict_item.secondary_pos != SecondaryPos.NONE:
            result = f"{result},{analysis.dict_item.secondary_pos.value}] "  # TODO: check name works
        else:
            result = f"{result}] "
        result = format_dict_item(
            analysis.dict_item.lemma,
            analysis.dict_item.primary_pos.value,
            analysis.dict_item.secondary_pos.value,
        )
        result += self.format_morphemes(stem=analysis.stem, surfaces=analysis.morphemes)
        return result

    def format_morphemes(self, stem: str, surfaces: list[tuple[Morpheme, str]]) -> str:
        result = []
        if self.add_surface:
            result.append(f"{stem}:")
        result.append(surfaces[0][0].id_)
        if len(surfaces) > 1 and not surfaces[1][0].derivational:
            result.append("+")
        for i, sf in enumerate(surfaces):
            if i == 0:
                continue
            m, surface = sf
            if m.derivational:
                result.append("|")
            if self.add_surface and len(surface) > 0:
                result.append(f"{surface}:")
            result.append(m.id_)
            if m.derivational:
                result.append("→")
            elif i < len(surfaces) - 1 and not surfaces[i + 1][0].derivational:
                result.append("+")
        return "".join(result)
