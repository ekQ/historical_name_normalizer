# -*- coding: utf-8 -*-

import codecs
import re
import time
import jellyfish as jf

# If a name is not found among the predefined mappings, it's mapped to the
# nearest predefined name if the Jaro-Winkler similarity (0,1] is above this
# threshold.
SIMILARITY_THRESHOLD = 0.9
# The list of available mappings.
NAME_TYPES = ['first', 'last', 'patronym', 'cause_of_death']
DEBUG = True


def ensure_unicode(s):
    if isinstance(s, unicode):
        return s
    if isinstance(s, str):
        return s.decode("utf8")
    return unicode(s)
u = ensure_unicode


def is_vowel(c):
    return c in u'aeiouyäö'


def clean_name(token, clean_strong=1):
    if token is None:
        return u""
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
                    u'Name type ({}) is not one of the following: {}'.format(
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
        self.name_map = self._load_name_map()
        self.name_trie = self._construct_trie()

    def normalize(self, name, find_nearest=True):
        '''
        Returns a normalized form of the name.

        If find_nearest is True, goes through all predefined names and find the
        most similar one (if performance is an issue, set it to false).
        '''
        t0 = time.time()
        name = u(name)
        if self.do_clean_names:
            name = clean_name(name, self.clean_level)
        if name in self.name_map:
            if DEBUG:
                print u"Found exact match: {} -> {}".format(name, self.name_map[name][0])
                print "Search took {:.4f} seconds.".format(time.time() - t0)
            return self.name_map[name][0]
        else:
            if not find_nearest:
                match_node = self.name_trie.longest_common_prefix(name)
                sim = jf.jaro_winkler(u(match_node.top_name), u(name))
                if sim >= SIMILARITY_THRESHOLD:
                    if DEBUG:
                        print u"Found approximate match: {} -> {} (sim={:.3f}) -> {}".format(
                                name, match_node.top_name, sim, match_node.top_norm_name)
                        print "Search took {:.4f} seconds.".format(time.time() - t0)
                    return match_node.top_norm_name
                else:
                    if DEBUG:
                        print u"Only bad match found: {} -> {} (sim={:.3f}) -> {}".format(
                                name, match_node.top_name, sim, match_node.top_norm_name)
                        print "Search took {:.4f} seconds.".format(time.time() - t0)
                    return name
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
                        print "Search took {:.4f} seconds.".format(time.time() - t0)
                    return self.name_map[nearest][0]
                else:
                    if DEBUG:
                        print u"Only bad search match found: {} -> {} (sim={:.3f}) -> {}".format(
                                name, nearest, nearest_sim, self.name_map[nearest][0])
                        print "Search took {:.4f} seconds.".format(time.time() - t0)
                    return name

    def normalize_all(self, name):
        '''
        Split the name string, normalize the tokens, concatenate and return.
        Useful for normalizing strings of multiple first names.
        '''
        parts = map(self.normalize, name.split())
        return ' '.join(parts)

    def _load_name_map(self):
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
            name = u(parts[0].lower())
            norm_name = u(parts[1].lower())
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
    last_normalizer = NameNormalizer('last')
    patronym_normalizer = NameNormalizer('patronym')
    cod_normalizer = NameNormalizer('cause_of_death')

    name = 'Hindrich'
    print u"\nExample first name to normalize: {}\n".format(name)
    normalized = first_normalizer.normalize(name)
    print u"Normalized: {}\n".format(normalized)


    name = u'Malmkvist'
    print u"\nExample last name to normalize: {}\n".format(name)
    normalized = last_normalizer.normalize(name, find_nearest=False)
    print u"Normalized based on prefix: {}\n".format(normalized)
    normalized = last_normalizer.normalize(name, find_nearest=True)
    print u"Normalized based on search: {}".format(normalized)
