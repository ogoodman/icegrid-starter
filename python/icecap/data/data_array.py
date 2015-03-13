from icecap.base.lru_cache import LRUCache
from icecap.data.data_log import DataLog

class DataArray(DataLog):
    def __init__(self, dir, chunk_limit=10240000, n_chunks=4, chunk_size=100):
        DataLog.__init__(self, dir, chunk_limit)
        self._chunks = LRUCache(n_chunks)
        self._chunk_size = chunk_size
        self._end = None

    def append(self, v, seq=None):
        with self._lock:
            end = self.end()
            if seq is None:
                seq = end
            elif self._end is not None:
                assert seq == self._end
            s_e = DataLog.append(self, v, seq)
            self._end = seq + 1

            # Cache the last inserted value.
            if self._chunks:
                mc = max(self._chunks)
                if self._end <= mc + self._chunk_size:
                    self._chunks[mc].append(v)
                else:
                    self._chunks[seq] = [v]
            else:
                self._chunks[seq] = [v]
            return s_e

    def __getitem__(self, i):
        with self._lock:
            lo, hi = None, None
            for a, chunk in self._chunks.iteritems():
                b = a + len(chunk)
                if a <= i < b:
                    return chunk[i - a]
                elif i < a:
                    if hi is None or a < hi:
                        hi = a
                elif i >= b:
                    if lo is None or b > lo:
                        lo = b
            if lo is None:
                lo = self.first()
                if lo is None or i < lo:
                    raise IndexError(i)
            if hi is None:
                hi = self.last() + 1
            if i >= hi:
                raise IndexError(i)

            # Now [lo:hi] is now the biggest chunk containing i which
            # does not overlap with any existing chunk.

            if hi - lo > self._chunk_size:
                if hi - i < self._chunk_size/2:
                    lo = hi - self._chunk_size # bring lo up.
                elif i - lo < self._chunk_size/2:
                    hi = lo + self._chunk_size # bring hi down.
                else:
                    lo = i - self._chunk_size/2
                    hi = lo + self._chunk_size

            new = []
            for j, val in self.iteritems(lo):
                if j >= hi:
                    break
                new.append(val)
            assert len(new) == hi - lo
            self._chunks[lo] = new
            return new[i - lo]

    def begin(self):
        return self.first() or 0

    def end(self):
        if self._end is None:
            last = self.last()
            if last is None:
                return 0
            self._end = last + 1
        return self._end

    def __len__(self):
        first = self.first()
        return 0 if first is None else self.last() + 1 - first

    def truncate(self, n):
        with self._lock:
            DataLog.truncate(self, n)
            for a in list(self._chunks):
                if a < n:
                    del self._chunks[a]

    def clear(self):
        with self._lock:
            DataLog.clear(self)
            self._chunks.clear()
