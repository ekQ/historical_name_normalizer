# -*- coding: utf-8 -*-

import codecs
import re
import time
import jellyfish as jf
import os

# If a name is not found among the predefined mappings, it's mapped to the
# nearest predefined name if the Jaro-Winkler similarity (0,1] is above this
# threshold.
SIMILARITY_THRESHOLD = 0.9
# The list of available mappings. The ones with suffix "_extended" include
# automatically inferred mapping between name variations which help to improve
# recall.
NAME_TYPES = ['first', 'last', 'patronym', 'cause_of_death', 'last_extended',
              'cause_of_death_extended']
DEBUG = True
WARNINGS = False


def ensure_unicode(s):
    if s is None:
        return u''
    if isinstance(s, unicode):
        return s
    if isinstance(s, str):
        return s.decode("utf8")
    return unicode(s)
u = ensure_unicode


def is_vowel(c):
    return c in u'aeiouyäö'


def clean_name(name, name_type='first'):
    '''
    Cleans a name string by making some common substitutions, such as
        c -> k
    For certain name types ('last' and 'cause_of_death') additional custom
    substitution rules are applied.

    Return:
        The cleaned name string.
    '''
    if name is None or len(name) == 0:
        return u""
    name = name.lower().split('\k')[0].strip()
    if name_type != 'dont_substitute':
        name = re.sub(u'[^a-zåäöé ]', '', name)
        name = name.strip()
        name = re.sub(u'c', u'k', name)
        name = re.sub(u'å', u'o', name)
        name = re.sub(u'w', u'v', name)
        name = re.sub(u'é', u'e', name)
    if name_type.startswith('last'):
        name = re.sub(u'io', u'jo', name)
        name = re.sub(u'iö', u'jö', name)
        name = re.sub(u'ph', u'ff', name)
        if name.endswith(u'nen'):
            name = name[:-2]
        if name.endswith(u'in') and len(name) > 3 and is_vowel(name[-3]):
            name = name[:-2] + u'n'
    elif name_type.startswith('cause_of_death'):
        name = re.sub(u'^af ', u'', name)
        name = re.sub(u'^i ', u'', name)
        name = re.sub(u'^död af ', u'', name)
        name = re.sub(u'^död i ', u'', name)
    return name


class NameNormalizer:
    def __init__(self, name_type, do_clean_names=True):
        if name_type not in NAME_TYPES:
            raise Exception(
                    u'Name type ({}) is not one of the following: {}'.format(
                        name_type, ', '.join(NAME_TYPES)))
        self.name_type = name_type
        self.do_clean_names = do_clean_names
        # Mapped names.
        self.name_map = self._load_name_map()
        self.name_trie = self._construct_trie()

    def normalize(self, name, find_nearest=True, info=None,
                  only_first_token=False):
        '''
        Returns a normalized form of the name.

        If find_nearest is True, goes through all predefined names and find the
        most similar one (if performance is an issue, set it to false).

        If info dictionary is provided, some extra data about the call will be
        stored there.

        only_first_token indicates whether to split the name string into tokens
        and only keep the first token.
        '''
        t0 = time.time()
        name = u(name)
        normalized = None
        if info is None:
            info = {}
        success = False
        if self.do_clean_names:
            name = clean_name(name, self.name_type)
        if only_first_token and len(name.strip()) > 0:
            name = name.split()[0]
        if len(name) == 0:
            normalized = u''
            success = True
            info['nearest'] = name
            info['sim'] = 1
        elif name in self.name_map:
            if DEBUG:
                print u"Found exact match: {} -> {}".format(name, self.name_map[name][0])
            normalized = self.name_map[name][0]
            success = True
            info['nearest'] = name
            info['sim'] = 1
            info['norm_popularity'] = self.name_map[name][2]
        else:
            if not find_nearest:
                match_node = self.name_trie.longest_common_prefix(name)
                sim = jf.jaro_winkler(u(match_node.top_name), u(name))
                if sim >= SIMILARITY_THRESHOLD:
                    if DEBUG:
                        print u"Found approximate match: {} -> {} (sim={:.3f}) -> {}".format(
                                name, match_node.top_name, sim, match_node.top_norm_name)
                    normalized = match_node.top_norm_name
                    success = True
                    info['norm_popularity'] = match_node.top_name_popularity
                else:
                    if DEBUG:
                        print u"Only bad match found: {} -> {} (sim={:.3f}) -> {}".format(
                                name, match_node.top_name, sim, match_node.top_norm_name)
                    normalized = name
                    info['norm_popularity'] = None
                info['nearest'] = match_node.top_name
                info['sim'] = sim
            else:
                nearest = None
                nearest_sim = -1
                for name2 in self.name_map.iterkeys():
                    sim = jf.jaro_winkler(u(name), u(name2))
                    if sim > nearest_sim:
                        nearest_sim = sim
                        nearest = name2
                if nearest_sim >= SIMILARITY_THRESHOLD:
                    if DEBUG:
                        print u"Found approximate search match: {} -> {} (sim={:.3f}) -> {}".format(
                                name, nearest, nearest_sim, self.name_map[nearest][0])
                    normalized = self.name_map[nearest][0]
                    success = True
                    info['norm_popularity'] = self.name_map[nearest][2]
                else:
                    if DEBUG:
                        print u"Only bad search match found: {} -> {} (sim={:.3f}) -> {}".format(
                                name, nearest, nearest_sim, self.name_map[nearest][0])
                    normalized = name
                    info['norm_popularity'] = None
                info['nearest'] = nearest
                info['sim'] = nearest_sim
        if DEBUG:
            print "Normalization took {:.3f} ms.".format(1000 * (time.time() - t0))
        info['success'] = success
        return normalized

    def normalize_all(self, name):
        '''
        Split the name string, normalize the tokens, concatenate and return.
        Useful for normalizing strings of multiple first names.
        '''
        parts = map(self.normalize, name.split())
        return ' '.join(parts)

    def _load_name_map(self):
        pd = os.path.dirname(os.path.abspath(__file__))  # Package directory.
        if self.name_type == 'first':
            fname = os.path.join(pd, 'data', 'normalized_first_names.tsv')
        elif self.name_type == 'last':
            fname = os.path.join(pd, 'data', 'normalized_last_names.tsv')
        elif self.name_type == 'last_extended':
            fname = os.path.join(pd, 'data', 'normalized_last_names_th0.90.tsv')
        elif self.name_type == 'patronym':
            fname = os.path.join(pd, 'data', 'normalized_patronyms.tsv')
        elif self.name_type == 'cause_of_death':
            fname = os.path.join(pd, 'data', 'normalized_death_causes.tsv')
        elif self.name_type == 'cause_of_death_extended':
            fname = os.path.join(pd, 'data', 'normalized_death_causes_th0.95.tsv')
        else:
            raise Exception('Unsupported name type.')
        f = codecs.open(fname, 'r', 'utf8')
        name_map = {}
        for line in f:
            parts = line.rstrip('\n').split('\t')
            name = u(parts[0].lower())
            norm_name = u(parts[1].lower())
            if self.do_clean_names:
                name = clean_name(name, self.name_type)
            name_popularity = int(parts[2])
            name_group_popularity = int(parts[3])
            others = parts[4:]
            if name in name_map:
                if name_map[name][0] != norm_name:
                    if WARNINGS:
                        print u'  Ignoring mapping:\t{} -> {}'.format(name, norm_name)
                        print u'  which contradicts a previous mapping:\t{} -> {}\n'.format(name, name_map[name][0])
                    continue
                else:
                    if name_group_popularity != name_map[name][2] and WARNINGS:
                        print(u"Same name group but different popularities:"
                              u" {} ({}), {} ({})".format(
                                  name, name_group_popularity,
                                  parts[0], name_map[name][2]))
                    name_popularity += name_map[name][1]
            name_map[name] = (norm_name, name_popularity, name_group_popularity,
                              others)
        return name_map

    def _construct_trie(self):
        t0 = time.time()
        node0 = TrieNode()
        n_nodes = 1
        for name, (norm_name, name_popularity, _, _) in \
                self.name_map.iteritems():
            cur = node0  # Current node.
            for c in name:
                if c not in cur.children:
                    new_node = TrieNode(c, name, norm_name, name_popularity)
                    cur.children[c] = new_node
                    n_nodes += 1
                else:
                    if name_popularity > cur.children[c].top_name_popularity:
                        cur.children[c].top_name = name
                        cur.children[c].top_norm_name = norm_name
                        cur.children[c].top_name_popularity = name_popularity
                cur = cur.children[c]
        if DEBUG:
            print "Constructed a '{}' trie with {} nodes in {:.4f} seconds.".format(
                    self.name_type, n_nodes, time.time()-t0)
        return node0


class TrieNode:

    def __init__(self, char=u'', top_name=u'', top_norm_name=u'',
                 top_name_popularity=-1):
        self.char = char
        self.children = {}
        self.top_name = top_name
        self.top_norm_name = top_norm_name
        self.top_name_popularity = top_name_popularity

    def longest_common_prefix(self, name):
        '''
        Follow the children nodes until the name has been exhausted or cannot
        be followed any further, and return the last matching node.
        '''
        if len(name) == 0 or name[0] not in self.children:
            return self
        else:
            return self.children[name[0]].longest_common_prefix(name[1:])


if __name__ == "__main__":
    first_normalizer = NameNormalizer('first')
    last_normalizer = NameNormalizer('last_extended')
    patronym_normalizer = NameNormalizer('patronym')
    cod_normalizer = NameNormalizer('cause_of_death')

    name = 'Hindrich'
    print u"\nExample #1: first name to normalize: {}\n".format(name)
    normalized = first_normalizer.normalize(name)
    print u"Normalized: {}\n".format(normalized)


    name = u'Malmkvist'
    print u"\nExample #2: last name to normalize: {}\n".format(name)
    normalized = last_normalizer.normalize(name, find_nearest=False)
    print u"Normalized based on prefix: {}\n".format(normalized)
    normalized = last_normalizer.normalize(name, find_nearest=True)
    print u"Normalized based on search: {}".format(normalized)
