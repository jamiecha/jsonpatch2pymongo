"""Convert Json Patch format into MongoDB update
referenced from:
- [jsonpatch to mongodb](https://www.npmjs.com/package/jsonpatch-to-mongodb)
- [jsonpatch to mongodb - golang](https://github.com/ZaninAndrea/json-patch-to-mongo/blob/main/main.go)
"""


class JsonPatch2PyMongoException(Exception):
    pass


def to_dot(path: str) -> str:
    if path.startswith('/'):
        path = path[1:] 
    return path.replace('/', '.').replace('~1', '/').replace('~0', '~')


def json_patch_to_mongo_update(patch_list: list) -> dict:
    update = {'$set':{}, '$unset':{}, '$push':{}}
    for p in patch_list:
        op, path, value = p['op'], p['path'], p.get('value', None)
        if op == 'add':
            path = to_dot(path)
            parts = path.split('.')
            position_part = parts[-1]
            add_to_end = True if position_part == '-' else False
            key = '.'.join(parts[:-1])
            try:
                position = int(position_part)
            except ValueError as e:
                position = None

            # debug
            print(f'{path=} {parts=} {position_part=} {position=} {add_to_end=} {key=}')

            if position:
                if key not in update['$push']:
                    update['$push'][key] = {'$each':[value], '$position': position}
                else:
                    if update['$push'][key] is None or '$position' not in update['$push'][key]:
                        msg = "Unsupported Operation! can't use add op with mixed positions"
                        raise JsonPatch2PyMongoException(msg)
                    pos_diff = position - update['$push'][key]['$position']
                    if pos_diff > len(update['$push'][key]['$each']):
                        msg = "Unsupported Operation! can use add op only with contiguous positions"
                        raise JsonPatch2PyMongoException(msg)
                    update['$push'][key]['$each'].insert(pos_diff, value)
                    update['$push'][key]['$position'] = min(position, update['$push'][key]['$position'])
            elif add_to_end:
                if key not in update['$push']:
                    update['$push'][key] = value
                else:
                    if update['$push'][key] is None or '$each' not in update['$push'][key]:
                        update['$push'][key] = {'$each': [update['$push'][key]]}
                    if '$position' in update['$push'][key]:
                        msg = "Unsupported Operation! can't use add op with mixed positions"
                        raise JsonPatch2PyMongoException(msg)
                    update['$push'][key]['$each'].append(value)
            else:
                msg = "Unsupported Operation! can't use add op without position"
                raise JsonPatch2PyMongoException(msg)
        elif op == 'remove':
            update['$unset'][to_dot(path)] = 1
        elif op == 'replace':
            update['$set'][to_dot(path)] = value
        elif op == 'test':
            pass  # the test op does not change the query
        else:
            raise JsonPatch2PyMongoException('unsupported operation type')

    # remove empty value operations before return
    return {k:v for k, v in update.items() if v}


tcs = [
    {
        "comment": "should work with single add",
        "patches": [
            {'op': 'add', 'path': '/name/-', 'value': 'dave'},
        ],
        "expected": {'$push': {'name': 'dave'}}
    },
    {
        "comment": "should work with escaped characters",
        "patches": [
            {'op': 'replace', 'path': '/foo~1bar~0', 'value': 'dave'},
        ],
        "expected": {'$set': {'foo/bar~': 'dave'}}
    },
    {
        "comment": "should work with array set",
        "patches": [
            {'op': 'add', 'path': '/name/1', 'value': 'dave'},
        ],
        "expected": {'$push': {'name': {'$each': ['dave'], '$position': 1}}}
    },
    {
        "comment": "should work with multiple set",
        "patches": [
            {'op': 'add', 'path': '/name/1', 'value': 'dave'},
            {'op': 'add', 'path': '/name/2', 'value': 'bob'},
            {'op': 'add', 'path': '/name/2', 'value': 'john'},
        ],
        "expected": {'$push': {'name': {'$each': ['dave', 'john', 'bob'], '$position': 1}}}
    },
    {
        "comment": "should work with multiple adds in reverse position",
        "patches": [
            {'op': 'add', 'path': '/name/1', 'value': 'dave'},
            {'op': 'add', 'path': '/name/1', 'value': 'bob'},
            {'op': 'add', 'path': '/name/1', 'value': 'john'},
        ],
        "expected": {'$push': {'name': {'$each': ['john', 'bob', 'dave'], '$position': 1}}}
    },
    {
        "comment": "should work with multiple adds",
        "patches": [
            {'op': 'add', 'path': '/name/-', 'value': 'dave'},
            {'op': 'add', 'path': '/name/-', 'value': 'bob'},
            {'op': 'add', 'path': '/name/-', 'value': 'john'},
        ],
        "expected": {'$push': {'name': {'$each': ['dave', 'bob', 'john']}}}
    },
    {
        "comment": "should work with multiple adds with some null at the end",
        "patches": [
            {'op': 'add', 'path': '/name/-', 'value': None},
            {'op': 'add', 'path': '/name/-', 'value': 'bob'},
            {'op': 'add', 'path': '/name/-', 'value': None},
        ],
        "expected": {'$push': {'name': {'$each': [None, 'bob', None]}}}
    },
    {
        "comment": "should work with multiple adds with some null and position",
        "patches": [
            {'op': 'add', 'path': '/name/1', 'value': None},
            {'op': 'add', 'path': '/name/1', 'value': 'bob'},
            {'op': 'add', 'path': '/name/1', 'value': None},
        ],
        "expected": {'$push': {'name': {'$each': [None, 'bob', None], '$position': 1}}}
    },
    {
        "comment": "should work with remove",
        "patches": [
            {'op': 'remove', 'path': '/name', 'value': 'dave'},
        ],
        "expected": {'$unset': {'name': 1}}
    },
    {
        "comment": "should work with replace",
        "patches": [
            {'op': 'replace', 'path': '/name', 'value': 'dave'},
        ],
        "expected": {'$set': {'name': 'dave'}}
    },
    {
        "comment": "should work with test",
        "patches": [
            {'op': 'test', 'path': '/name', 'value': 'dave'},
        ],
        "expected": {}
    },
    {
        "comment": "blow up on adds with non contiguous positions",
        "patches": [
            {'op': 'add', 'path': '/name/1', 'value': 'bob'},
            {'op': 'add', 'path': '/name/3', 'value': 'john'},
        ],
        "expected": JsonPatch2PyMongoException
    },
    {
        "comment": "blow up on adds with mixed position 1",
        "patches": [
            {'op': 'add', 'path': '/name/1', 'value': 'bob'},
            {'op': 'add', 'path': '/name/-', 'value': 'john'},
        ],
        "expected": JsonPatch2PyMongoException
    },
    {
        "comment": "blow up on adds with mixed position 2",
        "patches": [
            {'op': 'add', 'path': '/name/-', 'value': 'bob'},
            {'op': 'add', 'path': '/name/1', 'value': 'john'},
        ],
        "expected": JsonPatch2PyMongoException
    },
    {
        "comment": "should blow up on add without position",
        "patches": [
            {'op': 'add', 'path': '/name', 'value': 'dave'},
        ],
        "expected": JsonPatch2PyMongoException
    },
    {
        "comment": "should blow up on move",
        "patches": [
            {'op': 'move', 'path': '/name', 'from': '/old_name'},

        ],
        "expected": JsonPatch2PyMongoException
    },
    {
        "comment": "should blow up on move",
        "patches": [
            {'op': 'copy', 'path': '/name', 'from': '/old_name'},

        ],
        "expected": JsonPatch2PyMongoException
    },
]


def run_tc(comment, patches, expected):
    """should work with escaped characters
    """
    if not patches:
        return
    print(f'------------- {comment} -------------')
    try:
        result = json_patch_to_mongo_update(patches)
        print(f'{expected = }')
        print(f'{result   = }')
        assert result == expected
    except JsonPatch2PyMongoException as e:
        if expected is JsonPatch2PyMongoException:
            print('* Exception raised as expected: ', e)
        else:
            raise


if __name__ == '__main__':
    for tc in tcs:
        run_tc(tc['comment'], tc['patches'], tc['expected'])
