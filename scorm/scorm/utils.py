import hashlib
import mimetypes

from functools import partial

from webob import Response
from webob.exc import HTTPNotFound

BLOCK_SIZE = 8 * 1024


def get_sha1(file_descriptor):
    """
    Get file hex digest (fingerprint).
    """
    sha1 = hashlib.sha1()
    for block in iter(partial(file_descriptor.read, BLOCK_SIZE), ''):
        sha1.update(block)
    file_descriptor.seek(0)
    return sha1.hexdigest()


def get_mimetype(filename):
    type, encoding = mimetypes.guess_type(filename)
    # We'll ignore encoding, even though we shouldn't really
    return type or 'application/octet-stream'


class FileIterable(object):
    def __init__(self, storage, filename, start=None, stop=None):
        self.filename = filename
        self.storage = storage
        self.start = start
        self.stop = stop

    def __iter__(self):
        return FileIterator(self.filename, self.storage, self.start, self.stop)

    def app_iter_range(self, start, stop):
        return self.__class__(self.filename, start, stop)


class FileIterator(object):
    chunk_size = 4096

    def __init__(self, storage, filename, start, stop):
        self.storage = storage
        self.filename = filename
        self.fileobj = self.storage.open(self.filename, 'rb')
        if start:
            self.fileobj.seek(start)
        if stop is not None:
            self.length = stop - start
        else:
            self.length = None

    def __iter__(self):
        return self

    def next(self):
        if self.length is not None and self.length <= 0:
            raise StopIteration
        chunk = self.fileobj.read(self.chunk_size)
        if not chunk:
            raise StopIteration
        if self.length is not None:
            self.length -= len(chunk)
            if self.length < 0:
                # Chop off the extra:
                chunk = chunk[:self.length]
        return chunk

    __next__ = next  # py3 compat


def make_file_response(storage, filename, range=None):
    try:
        res = Response(content_type=get_mimetype(filename),
                       conditional_response=True)
        res.app_iter = FileIterable(storage, filename)
        res.content_length = storage.size(filename)
        res.last_modified = storage.modified_time(filename)
        res.etag = '%s-%s-%s' % (storage.modified_time(filename),
                                 storage.size(filename), hash(filename))
        return res
    except OSError:
        return HTTPNotFound("Not found")
