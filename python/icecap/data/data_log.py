"""Implements ``DataLog``."""

import fcntl
import os
import re
import threading

def neb_escape(s):
    """Doubles backslashes and replaces newlines with ``\\n``."""
    return s.replace('\\', '\\\\').replace('\n', '\\n')

def _unescape_char(m):
    c = m.group(1)
    return '\n' if c == 'n' else c

def neb_unescape(s):
    """Replaces ``\\x`` with a newline if *x* is ``n``, else with *x* itself."""
    return re.sub(r'\\(.)', _unescape_char, s)

class DataLog(object):
    """A ``DataLog`` is a persistent sequence of strings.

    Data is stored as a sequence of newline-escaped strings with ``\\n`` terminators.

    This avoids restrictions on line length, allows us to iterate
    forwards and backwards with equal ease, and is somewhat robust in
    the event of an incomplete write.

    Each data item has a sequence number. By default these start from 0 and
    go up by steps of 1, but any increasing sequence of (signed 64-bit) numbers
    can be used when appending items (such as millisecond time-stamps for example).

    Data is divided into files named ``data.0, data.1,...``. Items are appended
    to the highest numbered file until its size reaches *chunk_limit* at which
    point a new file is started.

    Files may be removed at any time. A ``truncate(seq)`` function is provided
    for cleanup which removes all files which contain only items below ``seq``.

    Item lookup and finding the starting point for any iteration are done by
    binary search, so even quite large logs should provide fast access.

    Usage::

        log = DataLog('/var/my-app/log')

        log.append('first item')     # can be arbitrary binary data
        log.append('second item')

        log.first()                  # -> 0
        log.last()                   # -> 1
        log[0]                       # -> 'first item'

        for item in log.iteritems(): # yields (0, 'first item'), ...
            print item             

        ...
        log.truncate(5000)           # remove files containing only items below 5000

    :param dir: directory in which to put data files (parent must exist)
    :param chunk_limit: size at which to start a new data file
    """

    _block_size = 1024

    def __init__(self, dir, chunk_limit=10240000):
        self._dir = dir
        self._chunk_limit = chunk_limit
        if not os.path.exists(dir):
            os.makedirs(dir)
        self._lock = threading.Lock()
        
    def first(self):
        """Sequence number of first item, or ``None`` if log is empty."""
        with self._lock:
            nums = self._nums()
            if not nums:
                return None
            fh = self._open(nums[0])
            return self._read_seq(fh)

    def last(self):
        """Sequence number of last item, or ``None`` if log is empty."""
        with self._lock:
            nums = self._nums()
            if not nums:
                return None
            fh = self._open(nums[-1])
            if not self._seek_last_line(fh):
                return None
            return self._read_seq(fh)

    def _nums(self):
        nums = [int(n[5:]) for n in os.listdir(self._dir) if n.startswith('data.')]
        nums.sort()
        return nums

    def _end_file(self):
        nums = self._nums()
        if not nums:
            max_n = 0
            exists = False
        else:
            max_n = nums[-1]
            exists = True
        return max_n, exists

    def _last_seq(self, fh):
        if not self._seek_last_line(fh):
            return None
        return self._read_seq(fh)

    def _open_rw(self, n, exists):
        path = os.path.join(self._dir, 'data.%d' % n)
        mode = os.O_RDWR | (0 if exists else os.O_CREAT)
        fd = os.open(path, mode)
        return os.fdopen(fd, 'r+')

    def append(self, s, seq=None):
        """Append a string to the log with optional minimum sequence number.

        The optional sequence number will only be used if it is greater than the
        last sequence number. Otherwise one higher than the current
        highest sequence number is used so that sequence numbers are always increasing.

        If not supplied, *seq* will be one more than the current highest.

        Returns (*seq*, *existing*) where *seq* is the sequence number written and
        *existing* is False if a new data file was started.

        :param s: string to append
        :param seq: sequence number
        """
        with self._lock:
            n, exists = self._end_file()
            if not exists and seq is None:
                seq = 0
            fh = self._open_rw(n, exists)
            lseq = self._last_seq(fh)
            if lseq is not None:
                seq = lseq + 1 if seq is None else max(seq, lseq + 1)

            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            if size >= self._chunk_limit:
                exists = False
                fh = self._open_rw(n + 1, exists)

            fh.write('%d ' % seq)
            fh.write(neb_escape(s))
            fh.write('\n')
            return seq, exists

    def _remove(self, n):
        """Remove the *n*-th file.

        :param n: file number
        """
        os.unlink(os.path.join(self._dir, 'data.%d' % n))

    def truncate(self, seq):
        """Remove all data files which contain only items strictly less than *seq*.

        :param seq: cutoff at which to retain items
        """
        with self._lock:
            nums = self._nums()
            for n in nums:
                fh = self._open(n)
                if self._seek_last_line(fh):
                    start = self._read_seq(fh)
                    if start is None or start >= seq:
                        break
                self._remove(n)

    def _seek_start_of_line(self, fh):
        """Position *fh* at start of the line it is in.

        After call either ``fh.tell()`` is 0 or the char before is ``\\n``.
        """
        e = fh.tell()
        while e > 0:
            b = max(e - self._block_size, 0)
            fh.seek(b)
            chunk = fh.read(e - b)
            pos = chunk.rfind('\n')
            if pos > 0:
                fh.seek(b + pos + 1)
                return
            e = b
        fh.seek(0)

    def _seek_next_line(self, fh):
        """Move *fh* to start of the next line, if any.

        Returns True if successful. If successful, *fh* will be
        moved one beyond the next ``\\n``.
        """
        while True:
            b = fh.tell()
            chunk = fh.read(self._block_size)
            if not chunk:
                return False
            pos = chunk.find('\n')
            if pos > 0:
                fh.seek(b + pos + 1)
                return True

    def _read_seq(self, fh):
        """Reads a sequence number from *fh*.

        :param fh: file handle
        """
        pos = fh.tell()
        data = fh.read(36)
        fh.seek(pos)
        if not ' ' in data:
            # Empty or incomplete write.
            return None
        return int(data.split(' ', 1)[0])

    def _seek_last_line(self, fh):
        """Find the start of the last ``\\n`` terminated line in the file.

        Returns True if successful.
        If successful, *fh* will be at the start of the last ``\\n`` terminated line.

        :param fh: file handle
        """
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        if not size:
            return False
        fh.seek(-1, os.SEEK_END)
        if fh.read(1) != '\n':
            # last line is incomplete so go back before it
            self._seek_start_of_line(fh)
            if fh.tell() == 0:
                return False
        fh.seek(-1, os.SEEK_CUR)
        self._seek_start_of_line(fh)
        return True

    def _seek_seq(self, fh, seq):
        """Position *fh* at start of all items >= *seq*.

        If there are no items >= *seq*, returns None.

        :param fh: file handle
        :param seq: sequence number to bisect file at
        """
        if not self._seek_last_line(fh):
            return None
        hi = fh.tell()
        hi_seq = self._read_seq(fh)
        if seq > hi_seq:
            return None
        # NOTE: hi_seq >= seq so iterating from the position
        # we return will always yeild at least one line.
        if seq == hi_seq:
            return hi
        lo = 0
        fh.seek(0)
        lo_seq = self._read_seq(fh)
        if seq <= lo_seq:
            return lo
        assert self._seek_next_line(fh) # must find hi at least since hi != lo.
        lo = fh.tell()
        while lo < hi:
            fh.seek((lo + hi) / 2)
            self._seek_start_of_line(fh)
            mid = fh.tell()
            mid_seq = self._read_seq(fh)
            if seq == mid_seq:
                return mid
            elif seq > mid_seq:
                self._seek_next_line(fh)
                lo = fh.tell()
                lo_seq = mid_seq + 1
            else: # seq < mid_seq
                hi = mid
                hi_seq = mid_seq
        return hi

    def _seq_start(self, n):
        """Return the sequence number of the first item in ``data.<n>``.

        :param n: file number
        """
        fh = self._open(n)
        return self._read_seq(fh)

    def _find_file(self, seq, nums):
        """Find the file number *n* such that *seq* must be in ``data.<n>`` if any.

        Caller must ensure that nums is not empty.

        :param seq: the sequence number to find
        :param nums: sorted list of file numbers
        """
        lo = 0
        hi = len(nums) - 1
        while lo < hi:
            mid = (lo + 1 + hi) / 2
            mid_seq = self._seq_start(nums[mid])
            assert (mid_seq is not None) or mid == hi
            if hi == lo + 1:
                if mid_seq is None or seq < mid_seq:
                    return nums[lo]
                else:
                    return nums[hi]
            if seq < mid_seq:
                hi = mid
            else:
                lo = mid
        return nums[lo]

    def iteritems(self, seq=None, reverse=False):
        """Yields consecutive (*n*, *data*) starting from *seq*.

        If there is no matching item this starts with the first item
        with a higher (resp. lower) sequence number when iterating forwards 
        (resp. backwards).

        :param seq: sequence number to start at
        :param reverse: whether to iterate backwards
        """
        with self._lock:
            nums = self._nums()
            if not nums:
                return
            n = None
            if seq is not None:
                # If reverse iteration, find seq+1 and iterate below it.
                if reverse:
                    seq += 1
                n = self._find_file(seq, nums)
                fh = self._open(n)
                pos = self._seek_seq(fh, seq)
                if pos is not None:
                    fh.seek(pos)
                    if reverse:
                        for item in self._rev_iter_file(fh):
                            yield item
                    else:
                        for item in self._iter_file(fh):
                            yield item

            # Get list of remaining data files to iterate.
            if reverse:
                if n is None:
                    n = nums[-1] + 1
                nums = [i for i in reversed(nums) if i < n]
            else:
                if n is None:
                    n = -1
                nums = [i for i in nums if i > n]

            # Iterate remaining data files.
            for i in nums:
                fh = self._open(i)
                if reverse:
                    fh.seek(0, os.SEEK_END)
                    for item in self._rev_iter_file(fh):
                        yield item
                else:
                    for item in self._iter_file(fh):
                        yield item

    def __getitem__(self, seq):
        """Returns the string with sequence number *seq*.

        Raises ``IndexError`` if no such item exists.

        :param seq: the sequence number of the string to return
        """
        with self._lock:
            nums = self._nums()
            if not nums:
                raise IndexError(seq)
            n = self._find_file(seq, nums)
            fh = self._open(n)
            pos = self._seek_seq(fh, seq)
            if pos is None:
                raise IndexError(seq)
            fh.seek(pos)
            for iseq, data in self._iter_file(fh):
                # _seek_seq not None guarantees at least one item.
                break
            if iseq != seq:
                raise IndexError(seq)
            return data

    def _open(self, n):
        """Return file handle for ``data.<n>`` open for reading.

        :param n: file number
        """
        path = os.path.join(self._dir, 'data.%d' % n)
        return open(path) 

    def _iter_file(self, fh):
        """Yeilds (*n*, *data*) for each line read from *fh*.

        Each line is assumed to be newline-escaped binary with a big-endian
        8-byte sequence number at the start, followed by the data.

        :param fh: file handle
        """
        buf = []
        while True:
            data = fh.read(self._block_size)
            if not data:
                break
            if '\n' not in data:
                buf.append(data)
                continue
            lines = data.split('\n')
            buf.append(lines[0])
            lines[0] = ''.join(buf)
            for l in lines[:-1]:
                seq_s, data = l.split(' ', 1)
                yield int(seq_s), neb_unescape(data)
            buf = [lines[-1]]

    def _rev_iter_file(self, fh):
        e = fh.tell()
        buf = []
        while e > 0:
            b = max(e - self._block_size, 0)
            fh.seek(b)
            data = fh.read(e - b)
            lines = data.split('\n')
            # If nothing in buffer and no \n, we haven't seen
            # a newline yet.
            if not buf:
                del lines[-1]
            else:
                buf.append(lines[-1])
                if len(lines) == 1: # no \n.
                    e = b
                    continue
                lines[-1] = ''.join(reversed(buf))
            # If we haven't seen a newline yet, lines is empty.
            # Otherwise, lines[0] is a line whose start we
            # haven't seen yet while lines[1:] are complete and
            # can be emitted.
            for l in reversed(lines[1:]):
                seq_s, data = l.split(' ', 1)
                yield int(seq_s), neb_unescape(data)
            if lines:
                buf = [lines[0]]
            e = b
        if buf:
            l = ''.join(reversed(buf))
            seq_s, data = l.split(' ', 1)
            yield int(seq_s), neb_unescape(data)
