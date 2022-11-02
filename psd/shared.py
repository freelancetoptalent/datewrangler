def strip_pairs(people, matchpairs):
    pdict = dict((x.name, x) for x in people)
    for pair in matchpairs:
        n1, n2 = pair
        if n2 in pdict[n1]:
            del pdict[n1][n2]
        if n1 in pdict[n2]:
            del pdict[n2][n1]
    return pdict.values()

def strip_matches(people, slate):
    pdict = dict((x.name, x) for x in people)
    for name in slate:
        n2, type = slate[name]
        if type not in ['recess', 'none']:
            if n2 in pdict[name]:
                del pdict[name][n2]
            if name in pdict[n2]:
                del pdict[n2][name]
    return pdict.values()

## Cribbed from elsewhere.
class counter(dict):
    def __init__(self, it={}):
        if isinstance(it, dict):
            dict.__init__(self, it)
        else:
            for item in it:
                if item in self:
                    self[item] += 1
                else:
                    self[item] = 1

    def __add__(self, other):
        new_copy = counter(self)
        for item in other:
            new_copy[item] = other[item] + self.get(item, 0)
        return new_copy

    def update(self, it):
        self += it

    def add(self, item):
        self.update([item])

    def remove(self, item):
        if item in self:
            self[item] -= 1
            if self[item] < 1:
                del self[item]
        else:
            raise KeyError

    def ordered_iter(self):
        return (y for (x,y) in sorted(((val, key) for (key, val) in self.iteritems()), reverse=True))
