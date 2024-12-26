class LRU(object):
    def __init__(self, size=None):
        self.size = size
        self.m = {}
        self.head = None
        self.tail = None
        self.count = 0

    def save(self, key, value):
        if key is None:
            return None, None
        if key in self.m:
            self.m[key][0] = value
        if self.count == 0:
            self.head = key
        else:
            self.m[self.tail][2] = key
        self.m[key] = [value, self.tail, None]
        self.tail = key
        self.count += 1
        if self.size and self.count > self.size:
            return self.pop()
        return None, None

    def pop(self, key=None):
        if key is None:
            key = self.head
        if key not in self.m:
            return None, None
        value, pre, nxt = self.m[key]
        if pre:
            self.m[pre][2] = nxt
        else:
            self.head = nxt
        if nxt:
            self.m[nxt][1] = pre
        else:
            self.tail = pre
        self.count -= 1
        del self.m[key]
        return key, value

    def pop_head(self):
        return self.pop()

    def find(self, key):
        if key in self.m:
            return key, self.m[key][0]
        else:
            return None, None


def test():
    c = SingleUseLRU(5)
    for i in range(10):
        print(i, c.cache(i, i))
        print(c.m.keys())
    for i in [7, 8, 9, 10]:
        print(i, c.pop(i))
        print(c.m.keys())
    for i in [11, 12, 13, 14]:
        print(i, c.cache(i, i))
        print(c.m.keys())


if __name__ == '__main__':
    test()
