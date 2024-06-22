import dataclasses

def dataclass(cls, **kwargs):
    if hasattr(cls, "from_raw") is True:
        cls.original_from_raw = cls.from_raw

        @classmethod
        def new_from_raw(cls, client, *args):
            data_argument = args[0]

            if isinstance(data_argument, cls):
                return data_argument

            if len(args) > 1:
                data_argument = args[1]

            used_keys = list(cls.__annotations__.keys())
            change_keys = getattr(cls, "__CHANGE_KEYS__", ())

            for old_key, new_key in change_keys:
                used_keys.remove(new_key)
                used_keys.append(old_key)

            to_remove = []

            for key in data_argument:
                if not key in used_keys:
                    to_remove.append(key)

            for key in to_remove:
                del data_argument[key]

            for old_key, new_key in change_keys:
                if old_key in data_argument:
                    data_argument[new_key] = data_argument.pop(old_key)

            return cls.original_from_raw(client, *args)

        cls.from_raw = new_from_raw

    return dataclasses.dataclass(cls, **kwargs)