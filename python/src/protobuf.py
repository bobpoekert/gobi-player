import python_pb2
from youtube_dl.extractor import gen_extractors
from youtube_dl.utils import GeoRestrictedError
from google.protobuf.message import Message
from google.protobuf import wrappers_pb2 as wrappers
from google.protobuf.internal.containers import MutableMapping, RepeatedCompositeFieldContainer
import ydl

extractors = [v for v in gen_extractors() if v.working()]
extractor_index = {}
for extractor in extractors:
    extractor_index[extractor.IE_NAME] = extractor

def get_info_extractor(name):
    return extractor_index.get(name)


class LoginRequiredException(Exception):
    pass

def raise_login_required(*args, **kwargs):
    raise LoginRequiredException()

for extractor in extractors:
    extractor.raise_login_required = raise_login_required

def get_fields(pb):
    return [v.name for v in pb.DESCRIPTOR.fields]

def set_value(pb, k, v):
    target = getattr(pb, k)
    if isinstance(target, MutableMapping):
        target.update(**v)
        return
    if isinstance(target, RepeatedCompositeFieldContainer):
        for el in v:
            target.add().value = v
        return
    if isinstance(target, wrappers.StringValue):
        v = unicode(v)
    try:
        target.value = v
    except Exception, e:
        print k, v, type(target)
        raise e

_dict2proto_cache = {}

def dict2proto(proto_type):
    if proto_type not in _dict2proto_cache:
        def _(d):
            res = proto_type()
            for k, v in d.iteritems():
                set_value(res, k, v)
            return res
        _dict2proto_cache[proto_type] = _
    return _dict2proto_cache[proto_type]

def assign_repeated(target, fieldname, values):
    if values is None:
        return
    cursor = getattr(target, fieldname)
    for value in values:
        if value is None:
            continue
        row = cursor.add()
        try:
            row.CopyFrom(value)
        except TypeError:
            row.value = value

def protomap(res, inp, t, k):
    assign_repeated(res, k, map(dict2proto(t), inp.get(k, [])))

def set_group(res, inp, t, k, ks):
    if any(inp.get(k2) for k2 in ks):
        res2 = getattr(res, k)
        for k2 in ks:
            if k2 in inp:
                set_value(res2, k2, inp.get(k2))

def format_from_dict(ie_dict):
    res = python_pb2.InfoDict.Format()

    for k, v in ie_dict.iteritems():
        if k not in ('protocol', 'fragments', 'rtmp_conn') and v is not None:
            set_value(res, k, v)

    if 'protocol' in ie_dict:
        res.protocol = getattr(res, ie_dict['protocol'].upper())

    if 'rtmp_conn' in ie_dict:
        assign_repeated(res, 'rtmp_conn', map(unicode, ie_dict['rtmp_conn']))

    protomap(res, ie_dict, python_pb2.InfoDict.Format.Fragment, 'fragments')

    return res

def subtitles_from_dict(d):
    if d is None:
        return []
    if isinstance(d, basestring):
        res = python_pb2.InfoDict.Subtitles()
        res.tag.value = d
        return [res]
    else:
        res = []
        for tag, subformats in d.iteritems():
            row = python_pb2.InfoDict.Subtitles()
            row.tag.value = tag
            for subformat in subformats:
                subpb = row.subformats.add()
                for k, v in subformat.iteritems():
                    set_value(subpb, k, v)
            res.append(row)
        return res

special_fields = (
                'formats', 'thumbnails', 'subtitles', 'automatic_captions',
                'comments', 'chapters', '_type', 'categories', 'tags', 'category', 'entries',
                'chapter', 'chapter_number', 'chapter_id', 'http_headers', 'session_speakers', 'authors',
                'series', 'season', 'season_number', 'season_id', 'episode', 'episode_number', 'episode_id',
                'track', 'track_number', 'track_id', 'artist', 'genre', 'album', 'album_type', 'album_artist',
                'disc_number', 'release_year', 'chapter_info', 'series_info', 'album_info', 'protocol')

def info_dict_from_dict(ie_dict):
    res = python_pb2.InfoDict()

    if 'thumnails' in ie_dict:
        ie_dict['thumbnails'] = ie_dict['thumnails']
        del ie_dict['thumnails']
        for row in ie_dict.get('thumbnails', []):
            if 'aspectRatio' in row:
                row['aspect_ratio'] = row['aspectRatio']
                del row['aspectRatio']

    for k, v in ie_dict.iteritems():
        if k not in special_fields and v is not None:
            set_value(res, k, v)

    if 'protocol' in ie_dict:
        res.protocol = getattr(python_pb2.InfoDict.Format, ie_dict['protocol'].upper())

    if 'session_speakers' in ie_dict:
        assign_repeated(res, 'session_speakers', ie_dict.get('session_speakers'))
    if 'authors' in ie_dict:
        assign_repeated(res, 'authors', ie_dict.get('authors'))
    if 'category' in ie_dict:
        assign_repeated(res, 'category', ie_dict.get('category'))

    protomap(res, ie_dict, python_pb2.InfoDict.Thumbnail, 'thumbnails')
    protomap(res, ie_dict, python_pb2.InfoDict.Comment, 'comments')
    protomap(res, ie_dict, python_pb2.InfoDict.Chapter, 'chapters')

    assign_repeated(res, 'formats', map(format_from_dict, ie_dict.get('formats', [])))

    assign_repeated(res, 'categories', ie_dict.get('categories'))
    assign_repeated(res, 'tags', ie_dict.get('tags'))
    assign_repeated(res, 'subtitles', subtitles_from_dict(ie_dict.get('subtitles')))
    assign_repeated(res, 'automatic_captions', subtitles_from_dict(ie_dict.get('automatic_captions')))

    set_group(res, ie_dict, python_pb2.InfoDict.ChapterInfo, 'chapter_info', ('chapter', 'chapter_number', 'chapter_id'))
    set_group(res, ie_dict, python_pb2.InfoDict.SeriesInfo, 'series_info', ('series', 'season', 'season_number', 'season_id', 'episode', 'episode_number', 'episode_id'))
    set_group(res, ie_dict, python_pb2.InfoDict.AlbumInfo, 'album_info', ('track', 'track_number', 'track_id', 'artist', 'genre', 'album', 'album_type', 'album_artist', 'disc_number', 'release_year'))

    if 'http_headers' in ie_dict:
        for k, v in ie_dict['http_headers'].iteritems():
            res.http_headers[k] = v

    return res

def unpack_value(v):
    try:
        return v.value
    except AttributeError:
        return v

def proto2dict(pb):
    if isinstance(pb, Message):
        res = {}
        for field, value in pb.ListFields():
            res[field.name] = unpack_value(value)
        return res
    else:
        return pb

def dict_from_info_dict(pb):
    res = {}

    fields = [v[0].name for v in pb.ListFields()]

    for k in fields:
        if k not in special_fields:
            res[k] = getattr(pb, k).value

    for k in ('thumbnails', 'comments', 'chapters'):
        v = map(proto2dict, getattr(pb, k))
        if v:
            res[k] = v
    if pb.protocol:
        res['protocol'] = python_pb2.InfoDict.Format.Protocol.Name(pb.protocol).lower()

    if pb.subtitles:
        subs = {}
        for sub in pb.subtitles:
            tag = sub.tag.value
            subfs = []
            for subf in sub.subformats:
                vv = {}
                if subf.ext and subf.ext.value:
                    vv['ext'] = subf.ext.value
                if subf.data and subf.data.value:
                    vv['data'] = subf.data.value
                if subf.url and subf.url.value:
                    vv['url'] = subf.url.value
                subfs.append(vv)
            if subfs:
                subs[tag] = subfs
        if subs:
            res['subtitles'] = subs

    if pb.formats:
        formats = []
        for f in pb.formats:
            v = proto2dict(f)
            if f.protocol:
                v['protocol'] = python_pb2.InfoDict.Format.Protocol.Name(f.protocol).lower()
            elif 'protocol' in v:
                del v['protocol']
            if 'fragments' in v:
                v['fragments'] = map(proto2dict, v['fragments'])
            if 'rtmp_conn' in v:
                v['rtmp_conn'] = map(unpack_value, v['rtmp_conn'])
            formats.append(v)
        res['formats'] = formats

    for fieldname in ('categories', 'tags', 'session_speakers', 'authors', 'category'):
        if getattr(pb, fieldname):
            res[fieldname] = map(unpack_value, getattr(pb, fieldname))

    for k in ('chapter_info', 'series_info', 'album_info'):
        if pb.HasField(k):
            for k, v in getattr(pb, k).ListFields():
                res[k.name] = proto2dict(v.value)

    headers = {}
    has_headers = False

    for k in pb.http_headers:
        headers[k] = pb.http_headers[k]
        has_headers = True

    if has_headers:
        res['http_headers'] = headers


    return res

def test_info_dict_roundtrip(d):
    return d == dict_from_info_dict(info_dict_from_dict(d))

def matching_extractors(url):
    return [x for x in extractors if x.suitable(url)]

def extractor_name(ex):
    return ex.IE_NAME

def url_is_resolvable(req):
    url = req.url.value
    names = map(extractor_name, matching_extractors(url))
    names = [v for v in names if v != 'generic']
    is_resolvable = len(names) > 0
    res = python_pb2.Response.URLIsResolvableResponse()
    res.is_resolvable.value = is_resolvable
    assign_repeated(res, 'resolver_names', names)
    return res

def playlist_pb2(result):
    res = info_dict_from_dict(result)
    assign_repeated(res, 'children', map(info_dict_from_dict, result['entries']))
    return res

def extract(url, username=None, password=None, extractors=None):
    res = []
    exc = []
    for extractor in extractors:
        with ydl.login_context(username, password):
            try:
                res.append((extractor, extractor.extract(url)))
            except Exception, e:
                exc.append(e)
    return res, exc

def resolve(req):
    resolver_name = req.resolver_name.value if req.resolver_name and req.resolver_name.value else None
    url = req.url.value
    username = req.username.value if req.username else None
    password = req.password.value if req.password else None

    has_login = bool(username and password)

    res = []
    if not resolver_name:
        extractors = matching_extractors(url)
    else:
        extractors = [get_info_extractor(resolver_name)]

    results, exceptions = extract(url, username=username, password=password, extractors=extractors)

    redirect_ie_key = None
    redirect_url = None

    for extractor, result in results:
        _type = result.get('_type')
        row = None
        if _type in ('playlist', 'multi_video'):
            row = playlist_pb2(results)
        elif _type in ('url', 'url_transparent'):
            redirect_ie_key = result.get('ie_key')
            redirect_url = result['url']
        else:
            row = info_dict_from_dict(result)
        if row:
            row.extractor_name.value = extractor_name(extractor)
            res.append(row)

    res_pb = python_pb2.Response.URLResolveResponse()
    res_pb.success.value = bool(len(results) > 0 and len(exceptions) < 1)
    res_pb.password_required.value = bool(any(isinstance(v, LoginRequiredException) for v in exceptions))
    res_pb.geo_restricted.value = bool(any(isinstance(v, GeoRestrictedError) for v in exceptions))
    if redirect_ie_key:
        res_pb.redirect.resolver.value = redirect_ie_key
    if redirect_url:
        res_pb.redirect.url.value = redirect_url
    for result in res:
        item = res_pb.info_dict.add()
        item.CopyFrom(result)
    return res_pb

def handle_request(req):
    res = python_pb2.Response()
    res.job_id.value = req.job_id.value
    if req.HasField('url_is_resolvable_request'):
        res.url_is_resolvable_response.CopyFrom(url_is_resolvable(req.url_is_resolvable_request))
    elif req.HasField('url_resolve_request'):
        res.url_resolve_response.CopyFrom(resolve(req.url_resolve_request))
    return res

def handle_request_blob(req_blob):
    req = python_pb2.Request()
    req.ParseFromString(req_blob)
    return handle_request(req).SerializeToString()
