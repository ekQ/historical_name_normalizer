# -*- coding: utf-8 -*-

import codecs
import re

NAME_TYPES = ['first', 'last', 'patronym', 'cause_of_death']


def is_vowel(c):
    return c in u'aeiouyäö'


def clean_name(token, clean_strong=1):
    if token is None:
        return ""
    token = token.lower().split('\k')[0].strip()
    if clean_strong >= 1:
        token = re.sub(u'[^a-zåäöé ]', '', token)
        token = token.strip()
        token = re.sub(u'c', u'k', token)
        token = re.sub(u'å', u'o', token)
        token = re.sub(u'w', u'v', token)
        token = re.sub(u'é', u'e', token)
    if clean_strong >= 2:
        token = re.sub(u'io', u'jo', token)
        token = re.sub(u'iö', u'jö', token)
        token = re.sub(u'ph', u'ff', token)
        if token.endswith(u'nen'):
            token = token[:-2]
        if token.endswith(u'in') and len(token) > 3 and is_vowel(token[-3]):
            token = token[:-2] + u'n'
    return token


class NameNormalizer:
    def __init__(self, name_type, do_clean_names=True):
        if name_type not in NAME_TYPES:
            raise Exception(
                    'Name type ({}) is not one of the following: {}'.format(
                        name_type, ', '.join(NAME_TYPES)))
        self.name_type = name_type
        self.do_clean_names = do_clean_names
        # The level of cleaning depends on name type.
        self.clean_level = 1
        if self.name_type == 'first':
            self.clean_level = 1
        elif self.name_type == 'last':
            self.clean_level = 2
        elif self.name_type == 'patronym':
            self.clean_level = 1
        elif self.name_type == 'cause_of_death':
            self.clean_level = 1
        # Mapped names.
        self.name_map = self.load_name_map()
        #self.name_trie = self.construct_trie()

    def load_name_map(self):
        if self.name_type == 'first':
            fname = 'data/normalized_first_names.tsv'
        elif self.name_type == 'last':
            fname = 'data/normalized_last_names.tsv'
        elif self.name_type == 'patronym':
            fname = 'data/normalized_patronyms.tsv'
        elif self.name_type == 'cause_of_death':
            fname = 'data/normalized_death_causes.tsv'
        else:
            raise Exception('Unsupported name type.')
        f = codecs.open(fname, 'r', 'utf8')
        name_map = {}
        for line in f:
            parts = line.rstrip('\n').split('\t')
            name = parts[0].lower()
            norm_name = parts[1].lower()
            if self.do_clean_names:
                name = clean_name(name, self.clean_level)
            name_popularity = int(parts[2])
            name_group_popularity = int(parts[3])
            others = parts[4:]
            if name in name_map:
                if name_map[name][0] != norm_name:
                    print u'Incompatible mappings for {}:'.format(name)
                    print name_map[name]
                    print norm_name
                    raise Exception('Incompatible mappings.')
                else:
                    if name_group_popularity != name_map[name][2]:
                        print(u"Same name group but different popularities:"
                              u" {} ({}), {} ({})".format(
                                  name, name_group_popularity,
                                  parts[0], name_map[name][2]))
                    name_popularity += name_map[name][1]
            name_map[name] = (norm_name, name_popularity, name_group_popularity,
                              others)
        return name_map


if __name__ == "__main__":
    first_normalizer = NameNormalizer('first')
    last_normalizer = NameNormalizer('last')
    patronym_normalizer = NameNormalizer('patronym')
    cod_normalizer = NameNormalizer('cause_of_death')
