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

import lib
from lib import commands, types
from bs4 import BeautifulSoup
from datetime import datetime
from config import LASTFM_API_KEY, LASTFM_API_SECRET, LASTFM_API_URL
import urllib, urllib.parse, hashlib, asyncio

class Fm(commands.Cog):
    name = "Muzyka"

    def __init__(self, bot):
        self.bot = bot

def setup(bot):
    bot.load_cog(Fm(bot))