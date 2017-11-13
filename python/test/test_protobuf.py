import unittest
from protobuf import *
import protobuf
from helper import expect_info_dict
import random
import json
from pprint import pprint
import traceback
import gzip
from contextlib import contextmanager

def url_request(url):
    res = python_pb2.Request.URLIsResolvableRequest()
    res.url.value = url
    return res

def random_string():
    return ''.join(
            chr(random.randint(0, 255)) for i in xrange(random.randint(0, 1000)))

generators = {
        int: lambda : random.randint(0, 9999999),
        str: random_string
        }

sanitize_espect_dict = None

def sanitize_expect_value(v):
    if isinstance(v, dict):
        return sanitize_expect_dict(v)
    elif isinstance(v, list):
        return map(sanitize_expect_value, v)
    elif v in generators:
        return generators[v]()
    elif isinstance(v, type):
        return None
    else:
        return v

def remove_none_values(d):
    if not isinstance(d, dict):
        return d
    res = {}
    for k, v in d.iteritems():
        if v is None or v in ({}, []):
            continue
        if type(v) in (list, tuple) and all(vv is None for vv in v):
            continue
        if k.startswith('_'):
            continue
        if k == 'id' or '_id' in k:
            res[k] = unicode(v)
            continue
        if k == 'subtitles':
            continue
        if k == 'view_count':
            res[k] = int(v)
            continue
        if isinstance(v, dict):
            res[k] = remove_none_values(v)
        elif isinstance(v, list) or isinstance(v, tuple):
            res[k] = map(remove_none_values, v)
        else:
            res[k] = v
    return res

def sanitize_expect_dict(d):
    res = {}
    for k, v in d.iteritems():
        vv = sanitize_expect_value(v)
        if vv is not None and vv != '' and vv != 0 and not \
                (isinstance(vv, basestring) and vv.startswith('mincount:')):
            res[k] = vv
    return res

def sanitize_info_dict(d):
    inp = remove_none_values(d)
    if 'release_year' in inp:
        inp['release_year'] = int(inp['release_year'])
    for row2 in inp.get('thumbnails', []):
        if 'id' in row2:
            row2['id'] = str(row2['id'])
        if 'aspectRatio' in row2:
            row2['aspect_ratio'] = row2['aspectRatio']
            del row2['aspectRatio']
    if '_type' in inp:
        inp = dict(**inp)
        del inp['_type']
    return inp

def _parse(s):
    res = python_pb2.InfoDict()
    res.ParseFromString(s)
    return res

def roundtrip(v):
    return dict_from_info_dict(_parse(info_dict_from_dict(v).SerializeToString()))

@contextmanager
def extraction_results(results, exceptions):
    def _(*args, **kwargs):
        extractors = kwargs.get('extractors')
        return ([(extractors[0] if extractors else None, v) for v in results], exceptions)
    old_extractor = protobuf.extract
    protobuf.extract = _
    try:
        yield
    finally:
        protobuf.extract = old_extractor

here = '/'.join(__file__.split('/')[:-1])

class TestWithTestData(unittest.TestCase):

    def setUp(self):
        self.maxDiff = None
        self.test_data = []
        self.test_json = []

        with gzip.open('%s/test_data.jsons.gz' % here, 'r') as inf:
            for row in inf:
                self.test_json.append(json.loads(row.strip()))

        for extractor in extractors:
            try:
                tests = extractor._TESTS
            except AttributeError:
                try:
                    tests = [extractor._TEST]
                except AttributeError:
                    continue
            for row in tests:
                if row is None:
                    continue
                row['info_extractor'] = extractor.IE_NAME
                self.test_data.append(row)

    def test_ie_pb_roundtrip(self):

        for row in self.test_json:
            if not row.get('res'):
                continue
            if type(row['res']) == unicode:
                continue
            if row['res'].get('_type') not in ('video', None):
                continue

            inp = sanitize_info_dict(row['res'])

            try:
                res = roundtrip(inp)
            except Exception, e:
                traceback.print_exc()
                pprint(inp)
                raise e
            self.assertDictEqual(res, inp)

        for row in self.test_data:
            if 'info_dict' in row:
                ie = row['info_dict']
                san = sanitize_info_dict(sanitize_expect_value(ie))
                try:
                    res = roundtrip(san)
                except Exception, e:
                    traceback.print_exc()
                    pprint(san)
                    raise e
                self.assertDictEqual(san, res)

    def test_playlist_roundtrip(self):
        playlists = [v for v in self.test_json if v.get('_type') in ('playlist', 'multi_video')]
        for playlist in playlists:
            res = playlist_pb2(playlist)
            for a, b in zip(res.entries, playlist['entries']):
                self.assertDictEquals(dict_from_info_dict(a), b)

    def test_url_resolution(self):
        urls = []

        for row in self.test_json:
            urls.append((row['url'], row['extractor']))

        for row in self.test_data:
            if 'url' not in row:
                continue
            urls.append((row['url'], row['info_extractor']))

        for url, info_extractor in urls:
            response = url_is_resolvable(url_request(url))
            self.assertTrue(response.is_resolvable.value)
            self.assertIn(info_extractor, [v.value for v in response.resolver_names])

    def test_resolve_request(self):
        for row in self.test_json:
            if not row.get('res'):
                continue
            if type(row['res']) == unicode:
                continue
            if row['res'].get('_type') not in ('video', None):
                continue
            res = sanitize_info_dict(row['res'])
            with extraction_results([res], []):
                req = python_pb2.Request.URLResolveRequest()
                req.url.value = row['url']
                response = resolve(req)
                response_dict = dict_from_info_dict(response.info_dict[0])
                del response_dict['extractor_name']
                self.assertEqual(response.success.value, True)
                self.assertEqual(response.password_required.value, False)
                self.assertEqual(response.geo_restricted.value, False)
                self.assertEqual(response.info_dict[0].extractor_name.value, row['extractor'])
                self.assertDictEqual(res, response_dict)

                req = python_pb2.Request.URLResolveRequest()
                req.url.value = row['url']
                req.resolver_name.value = row['extractor']
                response = resolve(req)
                response_dict = dict_from_info_dict(response.info_dict[0])
                del response_dict['extractor_name']
                self.assertEqual(response.success.value, True)
                self.assertEqual(response.password_required.value, False)
                self.assertEqual(response.geo_restricted.value, False)
                self.assertEqual(response.info_dict[0].extractor_name.value, row['extractor'])
                self.assertDictEqual(res, response_dict)

if __name__ == '__main__':
    unittest.main()
