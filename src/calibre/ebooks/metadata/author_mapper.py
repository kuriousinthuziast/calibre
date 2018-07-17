#!/usr/bin/env python2
# vim:fileencoding=utf-8
# License: GPLv3 Copyright: 2015, Kovid Goyal <kovid at kovidgoyal.net>

from __future__ import (unicode_literals, division, absolute_import,
                        print_function)
from collections import deque


def compile_pat(pat):
    import regex
    REGEX_FLAGS = regex.VERSION1 | regex.WORD | regex.FULLCASE | regex.IGNORECASE | regex.UNICODE
    return regex.compile(pat, flags=REGEX_FLAGS)


def matcher(rule):
    mt = rule['match_type']
    if mt == 'one_of':
        authors = {icu_lower(x.strip()) for x in rule['query'].split('&')}
        return lambda x: x in authors

    if mt == 'not_one_of':
        authors = {icu_lower(x.strip()) for x in rule['query'].split('&')}
        return lambda x: x not in authors

    if mt == 'matches':
        pat = compile_pat(rule['query'])
        return lambda x: pat.match(x) is not None

    if mt == 'not_matches':
        pat = compile_pat(rule['query'])
        return lambda x: pat.match(x) is None

    if mt == 'has':
        s = icu_lower(rule['query'])
        return lambda x: s in x

    return lambda x: False


def apply_rules(author, rules):
    ans = []
    authors = deque()
    authors.append(author)
    maxiter = 20
    while authors and maxiter > 0:
        author = authors.popleft()
        lauthor = icu_lower(author)
        maxiter -= 1
        for rule, matches in rules:
            ac = rule['action']
            if matches(lauthor):
                if ac == 'replace':
                    if 'matches' in rule['match_type']:
                        author = compile_pat(rule['query']).sub(rule['replace'], author)
                    else:
                        author = rule['replace']
                    if '&' in author:
                        replacement_authors = []
                        self_added = False
                        for rauthor in (x.strip() for x in author.split('&')):
                            if icu_lower(rauthor) == lauthor:
                                if not self_added:
                                    ans.append(rauthor)
                                    self_added = True
                            else:
                                replacement_authors.append(rauthor)
                        authors.extendleft(reversed(replacement_authors))
                    else:
                        if icu_lower(author) == lauthor:
                            # Case change or self replacement
                            ans.append(author)
                            break
                        authors.appendleft(author)
                    break
                if ac == 'capitalize':
                    ans.append(author.capitalize())
                    break
                if ac == 'lower':
                    ans.append(icu_lower(author))
                    break
                if ac == 'upper':
                    ans.append(icu_upper(author))
                    break
        else:  # no rule matched, default keep
            ans.append(author)

    ans.extend(authors)
    return ans


def uniq(vals, kmap=icu_lower):
    ''' Remove all duplicates from vals, while preserving order. kmap must be a
    callable that returns a hashable value for every item in vals '''
    vals = vals or ()
    lvals = (kmap(x) for x in vals)
    seen = set()
    seen_add = seen.add
    return list(x for x, k in zip(vals, lvals) if k not in seen and not seen_add(k))


def map_authors(authors, rules=()):
    if not authors:
        return []
    if not rules:
        return list(authors)
    rules = [(r, matcher(r)) for r in rules]
    ans = []
    for a in authors:
        ans.extend(apply_rules(a, rules))
    return uniq(filter(None, ans))


def find_tests():
    import unittest

    class TestAuthorMapper(unittest.TestCase):

        def test_author_mapper(self):

            def rule(action, query, replace=None, match_type='one_of'):
                ans = {'action':action, 'query': query, 'match_type':match_type}
                if replace is not None:
                    ans['replace'] = replace
                return ans

            def run(rules, authors, expected):
                if isinstance(rules, dict):
                    rules = [rules]
                if isinstance(authors, type('')):
                    authors = [x.strip() for x in authors.split('&')]
                if isinstance(expected, type('')):
                    expected = [x.strip() for x in expected.split('&')]
                ans = map_authors(authors, rules)
                self.assertEqual(ans, expected)

            run(rule('capitalize', 't1&t2'), 't1&x1', 'T1&x1')
            run(rule('upper', 'ta&t2'), 'ta&x1', 'TA&x1')
            run(rule('lower', 'ta&x1'), 'TA&X1', 'ta&x1')
            run(rule('replace', 't1', 't2'), 't1&x1', 't2&x1')
            run(rule('replace', '(.)1', r'\g<1>2', 'matches'), 't1&x1', 't2&x2')
            run(rule('replace', '(.)1', r'\g<1>2&3', 'matches'), 't1&x1', 't2&3&x2')
            run(rule('replace', 't1', 't2 & t3'), 't1&x1', 't2&t3&x1')
            run(rule('replace', 't1', 't1'), 't1&x1', 't1&x1')
            run([rule('replace', 't1', 't2'), rule('replace', 't2', 't1')], 't1&t2', 't1&t2')
            run(rule('replace', 'a', 'A'), 'a&b', 'A&b')
            run(rule('replace', 'a&b', 'A&B'), 'a&b', 'A&B')
            run(rule('replace', 'L', 'T', 'has'), 'L', 'T')
    return unittest.defaultTestLoader.loadTestsFromTestCase(TestAuthorMapper)


if __name__ == '__main__':
    from calibre.utils.run_tests import run_cli
    run_cli(find_tests())
