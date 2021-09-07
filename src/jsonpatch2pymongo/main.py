"""Convert Json Patch format into MongoDB update
referenced from:
- [jsonpatch to mongodb](https://www.npmjs.com/package/jsonpatch-to-mongodb)
- [jsonpatch to mongodb - golang](https://github.com/ZaninAndrea/json-patch-to-mongo/blob/main/main.go)
"""


version = "1.0"


class JsonPatch2PyMongoException(Exception):
    pass


def to_dot(path: str) -> str:
    if path.startswith("/"):
        path = path[1:]
    return path.replace("/", ".").replace("~1", "/").replace("~0", "~")


def jsonpatch2pymongo(patch_list: list) -> dict:
    update = {"$set": {}, "$unset": {}, "$push": {}}
    for p in patch_list:
        op, path, value = p["op"], p["path"], p.get("value", None)
        dot_path = to_dot(path)
        if op == "add":
            parts = dot_path.split(".")
            position_part = parts[-1]
            add_to_end = True if position_part == "-" else False
            key = ".".join(parts[:-1])
            try:
                position = int(position_part)
            except ValueError as e:
                position = None

            # debug
            # print(f'{dot_path=} {parts=} {position_part=} {position=} {add_to_end=} {key=}')

            if position:
                if key not in update["$push"]:
                    update["$push"][key] = {"$each": [value], "$position": position}
                else:
                    if update["$push"][key] is None or "$position" not in update["$push"][key]:
                        msg = "Unsupported Operation! can't use add op with mixed positions"
                        raise JsonPatch2PyMongoException(msg)
                    pos_diff = position - update["$push"][key]["$position"]
                    if pos_diff > len(update["$push"][key]["$each"]):
                        msg = "Unsupported Operation! can use add op only with contiguous position"
                        raise JsonPatch2PyMongoException(msg)
                    update["$push"][key]["$each"].insert(pos_diff, value)
                    update["$push"][key]["$position"] = min(
                        position, update["$push"][key]["$position"]
                    )
            elif add_to_end:
                if key not in update["$push"]:
                    update["$push"][key] = value
                else:
                    if update["$push"][key] is None or "$each" not in update["$push"][key]:
                        update["$push"][key] = {"$each": [update["$push"][key]]}
                    if "$position" in update["$push"][key]:
                        msg = "Unsupported Operation! can't use add op with mixed positions"
                        raise JsonPatch2PyMongoException(msg)
                    update["$push"][key]["$each"].append(value)
            else:
                # The original javascript version raises exception here.
                # But according to the RFC 6902 spec, we should handle this as a new set
                update["$set"][dot_path] = value
        elif op == "remove":
            update["$unset"][dot_path] = 1
        elif op == "replace":
            update["$set"][dot_path] = value
        elif op == "test":
            pass  # the test op does not change the query
        else:
            raise JsonPatch2PyMongoException("unsupported operation type")

    # remove empty value operations before return
    return {k: v for k, v in update.items() if v}
