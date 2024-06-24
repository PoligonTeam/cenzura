"""
Copyright 2022-2024 PoligonTeam

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

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