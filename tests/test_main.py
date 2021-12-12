import pytest

from jsonpatch2pymongo import JsonPatch2PyMongoException, jsonpatch2pymongo, to_dot


def test_to_dot():
    r = to_dot("/root/middle/leaf")
    assert r == "root.middle.leaf"


def test_jp2pym_single_add():
    patches = [{"op": "add", "path": "/name/-", "value": "dave"}]
    expected = {"$push": {"name": "dave"}}
    assert expected == jsonpatch2pymongo(patches), "should work with single add"


def test_jp2pym_escape_characters():
    patches = [{"op": "replace", "path": "/foo~1bar~0", "value": "dave"}]
    expected = {"$set": {"foo/bar~": "dave"}}
    assert expected == jsonpatch2pymongo(patches), "should work with escaped characters"


def test_jp2pym_array_set():
    patches = [{"op": "add", "path": "/name/1", "value": "dave"}]
    expected = {"$push": {"name": {"$each": ["dave"], "$position": 1}}}
    assert expected == jsonpatch2pymongo(patches), "should work with array set"


def test_jp2pym_multiple_set():
    patches = [
        {"op": "add", "path": "/name/1", "value": "dave"},
        {"op": "add", "path": "/name/2", "value": "bob"},
        {"op": "add", "path": "/name/2", "value": "john"},
    ]
    expected = {"$push": {"name": {"$each": ["dave", "john", "bob"], "$position": 1}}}
    assert expected == jsonpatch2pymongo(patches), "should work with multiple set"


def test_jp2pym_multiple_adds_in_reverse_position():
    patches = [
        {"op": "add", "path": "/name/1", "value": "dave"},
        {"op": "add", "path": "/name/1", "value": "bob"},
        {"op": "add", "path": "/name/1", "value": "john"},
    ]
    expected = {"$push": {"name": {"$each": ["john", "bob", "dave"], "$position": 1}}}
    assert expected == jsonpatch2pymongo(
        patches
    ), "should work with multiple adds in reverse position"


def test_jp2pym_multiple_adds_last():
    patches = [
        {"op": "add", "path": "/name/-", "value": "dave"},
        {"op": "add", "path": "/name/-", "value": "bob"},
        {"op": "add", "path": "/name/-", "value": "john"},
    ]
    expected = {"$push": {"name": {"$each": ["dave", "bob", "john"]}}}
    assert expected == jsonpatch2pymongo(patches), "should work with multiple adds"


def test_jp2pym_multiple_adds_last_with_nulls():
    patches = [
        {"op": "add", "path": "/name/-", "value": None},
        {"op": "add", "path": "/name/-", "value": "bob"},
        {"op": "add", "path": "/name/-", "value": None},
    ]
    expected = {"$push": {"name": {"$each": [None, "bob", None]}}}
    assert expected == jsonpatch2pymongo(
        patches
    ), "should work with multiple adds with some null at the end"


def test_jp2pym_multiple_adds_last_with_nulls_with_position():
    patches = [
        {"op": "add", "path": "/name/1", "value": None},
        {"op": "add", "path": "/name/1", "value": "bob"},
        {"op": "add", "path": "/name/1", "value": None},
    ]
    expected = {"$push": {"name": {"$each": [None, "bob", None], "$position": 1}}}
    assert expected == jsonpatch2pymongo(
        patches
    ), "should work with multiple adds with some null and position"


def test_jp2pym_remove():
    patches = [{"op": "remove", "path": "/name", "value": "dave"}]
    expected = {"$unset": {"name": 1}}
    assert expected == jsonpatch2pymongo(patches), "should work with remove"


def test_jp2pym_replace():
    patches = [{"op": "replace", "path": "/name", "value": "dave"}]
    expected = {"$set": {"name": "dave"}}
    assert expected == jsonpatch2pymongo(patches), "should work with replace"


def test_jp2pym_test():
    patches = [{"op": "test", "path": "/name", "value": "dave"}]
    expected = {}
    assert expected == jsonpatch2pymongo(patches), "should work with test"


def test_jp2pym_raise_on_add_with_non_contiguous_position():
    patches = [
        {"op": "add", "path": "/name/1", "value": "bob"},
        {"op": "add", "path": "/name/3", "value": "john"},
    ]
    with pytest.raises(JsonPatch2PyMongoException):
        jsonpatch2pymongo(patches)


def test_jp2pym_raise_on_add_with_mixed_position1():
    patches = [
        {"op": "add", "path": "/name/1", "value": "bob"},
        {"op": "add", "path": "/name/-", "value": "john"},
    ]
    with pytest.raises(JsonPatch2PyMongoException):
        jsonpatch2pymongo(patches)


def test_jp2pym_raise_on_add_with_mixed_position2():
    patches = [
        {"op": "add", "path": "/name/-", "value": "bob"},
        {"op": "add", "path": "/name/1", "value": "john"},
    ]
    with pytest.raises(JsonPatch2PyMongoException):
        jsonpatch2pymongo(patches)


def test_jp2pym_add_treated_as_replace():
    patches = [{"op": "add", "path": "/name", "value": "dave"}]
    expected = {"$set": {"name": "dave"}}
    assert expected == jsonpatch2pymongo(
        patches
    ), "should be treated as replace if adding without position"


def test_jp2pym_raise_on_move():
    patches = [{"op": "move", "path": "/name"}]
    with pytest.raises(JsonPatch2PyMongoException):
        jsonpatch2pymongo(patches)    


def test_jp2pym_move():
    patches = [{"op": "move", "path": "/name", "from": "/old_name"}]
    expected = {"$rename": {"old_name": "name"}}
    assert expected == jsonpatch2pymongo(patches)

def test_jp2pym_raise_on_copy():
    patches = [{"op": "copy", "path": "/name", "from": "/old_name"}]
    with pytest.raises(JsonPatch2PyMongoException):
        jsonpatch2pymongo(patches)
