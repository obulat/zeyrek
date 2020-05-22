from typing import Union

from zeyrek.attributes import RootAttribute, PhoneticAttribute


class Condition:

    def accept(self, path):
        raise NotImplementedError

    def and_(self, other):
        if type(other) == CombinedCondition and other.operator == 'AND':
            return CombinedCondition('AND', [self, *other.conditions])
        else:
            return CombinedCondition('AND', [self, other])

    def or_(self, other):
        if type(other) == CombinedCondition and other.operator == 'OR':
            return CombinedCondition('OR', [self, *other.conditions])
        else:
            return CombinedCondition('OR', [self, other])

    def and_not(self, other):
        return self.and_(other.not_())

    def or_not(self, other):
        return self.or_(other.not_())

    def not_(self):
        return NotCondition(self)

    def __len__(self):
        return 1


class NotCondition(Condition):
    def __init__(self, condition):
        self.condition = condition

    def accept(self, path):
        return not self.condition.accept(path)

    def __repr__(self):
        return f"Not{self.condition}"


class CombinedCondition(Condition):

    def __init__(self, operator, conditions):
        self.operator = operator
        self.conditions = conditions

    def accept(self, path):
        if len(self.conditions) == 0:
            return True
        elif len(self.conditions) == 1:
            return self.conditions[0].accept(path)

        if self.operator == 'AND':
            for condition in self.conditions:
                if not condition.accept(path):
                    return False
            return True
        else:
            for condition in self.conditions:
                if condition.accept(path):
                    return True
            return False

    def __len__(self):
        if len(self.conditions) == 0:
            return 0
        result = 0
        for condition in self.conditions:
            if type(condition) == CombinedCondition:
                result += len(condition)
            else:
                result += 1
        return result


def has(attribute):
    if type(attribute) == RootAttribute:
        return HasRootAttribute(attribute)
    else:
        return HasPhoneticAttribute(attribute)


def not_have(attribute: Union[RootAttribute, PhoneticAttribute]):
    if type(attribute) == RootAttribute:
        return HasRootAttribute(attribute).not_()
    else:
        return HasPhoneticAttribute(attribute).not_()


class HasRootAttribute(Condition):
    def __init__(self, attribute):
        self.attribute = attribute

    def accept(self, path):
        return path.dict_item.has_attribute(self.attribute)  # TODO test

    def __repr__(self):
        return f"HasRootAttribute({self.attribute})"


class HasAnyRootAttribute(Condition):
    def __init__(self, attributes):
        self.attributes = attributes

    def accept(self, path):
        return path.dict_item.has_any_attribute(self.attributes)

    def __repr__(self):
        return f"HasAnyRootAttribute({self.attributes})"


class HasPhoneticAttribute(Condition):
    def __init__(self, attribute):
        self.attribute = attribute

    def accept(self, path):
        return self.attribute in path.phonetic_attributes

    def __repr__(self):
        return f"HasPhoneticAttribute({self.attribute})"


class DictionaryItemIs(Condition):
    def __init__(self, dict_item):
        self.dict_item = dict_item

    def accept(self, path):
        return self.dict_item is not None and path.dict_item == self.dict_item

    def __repr__(self):
        return f"DictionaryItemIs({self.dict_item})"


class SecondaryPosIs(Condition):
    def __init__(self, pos):
        self.pos = pos

    def accept(self, path):
        return path.dict_item.secondary_pos == self.pos

    def __repr__(self):
        return f"SecondaryPosIs[{self.pos}]"


class DictionaryItemIsAny(Condition):
    def __init__(self, *items):
        # Temporary:
        self.items = [item for item in items if item is not None]

    def accept(self, path):
        return path.dict_item in self.items

    def __repr__(self):
        return f"DictionaryItemIsAny({self.items})"


class HasAnySuffixSurface(Condition):

    def accept(self, path):
        return path.contains_suffix_with_surface

    def __repr__(self):
        return "HasAnySuffixSurface{}"


class HasTail(Condition):
    # accepts if path has letters to consume.

    def accept(self, path):
        return len(path.tail) != 0

    def __repr__(self):
        return "HasTail{}"


class HasTailSequence(Condition):
    def __init__(self, *morphemes):
        self.morphemes = morphemes

    def accept(self, path):
        forms = path.transitions
        if len(forms) < len(self.morphemes):
            return False
        for form, morph in zip(forms[-len(self.morphemes):], self.morphemes):
            if form.morpheme != morph:
                return False
        return True

    def __repr__(self):
        return f"HasTailSequence({self.morphemes})"


class ContainsMorphemeSequence(Condition):
    def __init__(self, *morphemes):
        self.morphemes = morphemes

    def accept(self, path):
        forms = path.transitions
        if len(forms) < len(self.morphemes):
            return False
        m = 0
        for form in forms:
            if form.morpheme == self.morphemes[m]:
                m += 1
                if m == len(self.morphemes):
                    return True
            else:
                m = 0
        return False

    def __repr__(self):
        return f"ContainsMorphemeSequence({self.morphemes})"


class PreviousMorphemeIs(Condition):
    def __init__(self, morpheme):
        self.morpheme = morpheme

    def accept(self, path):
        previous_state = path.previous_state
        return previous_state is not None and previous_state.morpheme == self.morpheme

    def __repr__(self):
        return f"PreviousMorphemeIs({self.morpheme.id_})"


class PreviousStateIs(Condition):
    def __init__(self, state):
        self.state = state

    def accept(self, path):
        previous_state = path.previous_state
        return previous_state is not None and previous_state == self.state

    def __repr__(self):
        return f"PreviousStateIs({self.state})"


class PreviousStateIsNot(Condition):
    def __init__(self, state):
        self.state = state

    def accept(self, path):
        previous_state = path.previous_state
        return previous_state is None or previous_state != self.state

    def __repr__(self):
        return f"PreviousStateIsNot({self.state})"


class RootSurfaceIs(Condition):
    def __init__(self, surface):
        self.surface = surface

    def accept(self, path):
        return path.stem_transition.surface == self.surface

    def __repr__(self):
        return f"RootSurfaceIs({self.surface})"


class RootSurfaceIsAny(Condition):
    def __init__(self, *surfaces):
        self.surfaces = surfaces

    def accept(self, path):
        for s in self.surfaces:
            if path.stem_transition.surface == s:
                return True

        return False

    def __repr__(self):
        return f"RootSurfaceIsAny({self.surfaces})"


class LastDerivationIs(Condition):

    def __init__(self, state):
        self.state = state

    def accept(self, path):
        suffixes = path.transitions
        for sf in reversed(suffixes):
            if sf.state.derivative:
                return sf.state == self.state
        return False

    def __repr__(self):
        return f"LastDerivationIs({self.state})"


class HasDerivation(Condition):

    def accept(self, path):
        suffixes = path.transitions
        for suffix in suffixes:
            if suffix.state.derivative:
                return True
        return False

    def __repr__(self):
        return "HasDerivation"


class LastDerivationIsAny(Condition):
    def __init__(self, *states):
        self.states = states

    def accept(self, path):
        suffixes = path.transitions
        for sf in reversed(suffixes):
            if sf.state.derivative:
                return sf.state in self.states
        return False

    def __repr__(self):
        return f"LastDerivationIsAny({self.states})"


class CurrentGroupContainsAny(Condition):
    """Checks if any of the "MorphemeState" in "states" exist in current Inflectional Group.
    If previous group starts after a derivation, derivation MorphemeState is also checked.
    """

    def __init__(self, *states):
        self.states = states

    def accept(self, path):
        suffixes = path.transitions
        for sf in reversed(suffixes):
            if sf.state in self.states:
                return True
            if sf.state.derivative:
                return False

        return False

    def __repr__(self):
        return f"CurrentGroupContainsAny({self.states})"


class PreviousGroupContains(Condition):
    """ Checks if any of the "MorphemeState" in "states" exist in previous Inflectional Group.
    # If previous group starts after a derivation, derivation MorphemeState is also checked.
    """

    def __init__(self, *states):
        self.states = states

    def accept(self, path):
        suffixes = path.transitions
        last_index = len(suffixes) - 1
        sf = suffixes[last_index]
        while not sf.state.derivative:
            if last_index == 0:
                return False
            last_index -= 1
            sf = suffixes[last_index]
        for sf in reversed(suffixes[:last_index]):
            if sf.state in self.states:
                return True
            if sf.state.derivative:
                return False
        return False

    def __repr__(self):
        return f"PreviousGroupContains({self.states})"


class PreviousGroupContainsMorpheme(Condition):
    """Checks if any of the "Morpheme" in "morphemes" exist in previous Inflectional Group.
    If previous group starts after a derivation, derivation Morpheme is also checked.
    """

    def __init__(self, *morphemes):
        self.morphemes = morphemes

    def accept(self, path):
        suffixes = path.transitions
        last_index = len(suffixes) - 1
        sf = suffixes[last_index]
        while not sf.state.derivative:
            if last_index == 0:
                return False
            last_index -= 1
            sf = suffixes[last_index]
        for sf in reversed(suffixes[:last_index]):
            if sf.state.morpheme in self.morphemes:
                return True
            if sf.state.derivative:
                return False
        return False

    def __repr__(self):
        morpheme_str = ', '.join([m.id_ for m in self.morphemes])
        return f"PreviousGroupContainsMorpheme({morpheme_str})"


class NoSurfaceAfterDerivation(Condition):
    """
    # No letters are consumed after derivation occurred. This does not include the transition
    that caused derivation.
    """

    def accept(self, path):
        suffixes = path.transitions
        for sf in reversed(suffixes):
            if sf.state.derivative or sf.is_derivational_or_root:  # TODO: check this
                return True
            if not len(sf.surface) == 0:
                return False
        return True

    def __repr__(self):
        return "NoSurfaceAfterDerivation{}"


class ContainsMorpheme(Condition):
    def __init__(self, *morphemes):
        self.morphemes = morphemes

    def accept(self, path):
        suffixes = path.transitions
        for suffix in suffixes:
            if suffix.state.morpheme in self.morphemes:
                return True
        return False

    def __repr__(self):
        morphemes_str = ', '.join([m.id_ for m in self.morphemes])
        return f"ContainsMorpheme({morphemes_str})"


class PreviousMorphemeIsAny(Condition):
    """Second before last morpheme"""
    def __init__(self, *morphemes):
        self.morphemes = morphemes

    def accept(self, path):
        previous_state = path.previous_state
        return previous_state is not None and previous_state.morpheme in self.morphemes

    def __repr__(self):
        return f"PreviousMorphemeIsAny({self.morphemes})"


class PreviousStateIsAny(Condition):

    def __init__(self, *states):
        self.states = states

    def accept(self, path):
        previous_state = path.previous_state
        return previous_state is not None and previous_state in self.states
