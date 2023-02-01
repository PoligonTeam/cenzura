"""
Copyright 2022 PoligonTeam

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

class InvalidApiKey(Exception):
    pass

class BadGateway(Exception):
    pass

class NotFound(Exception):
    pass

class InvalidSignature(Exception):
    pass

class UnauthorizedToken(Exception):
    pass

class InvalidToken(Exception):
    pass

class ExpiredToken(Exception):
    pass

class TemporaryError(Exception):
    pass

class SuspendedApiKey(Exception):
    pass

class RateLimitExceeded(Exception):
    pass