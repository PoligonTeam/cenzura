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

class HTTPException(Exception):
    def __init__(self, description, status, original_error):
        super().__init__("%s status: %s" % (status, description))

        self.status = status
        self.original_error = original_error

class IntentNotExist(Exception):
    pass

class PermissionNotExist(Exception):
    pass

class InvalidArgument(Exception):
    pass