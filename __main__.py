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

import logging, re, sys, io, time, config
from datetime import datetime
from bot import Bot

start_time = time.time()

class StreamHandler(io.StringIO):
    def __init__(self, stream, path, blacklist, command_line):
        super().__init__()

        self.stream = stream
        self.path = path
        self.blacklist = blacklist
        self.command_line = command_line
        self.date = None

        self.file = None

        while self.path and self.path[-1] == "/":
            self.path = self.path[:-1]

        self.create_file()

    def create_file(self):
        self.date = datetime.now()

        if self.path:
            self.file = open(self.path + "/%s.log" % self.date.strftime("%Y-%m-%d"), "a")
            self.file.write("\n\n\n\n\nTIMEZONE: %s; DATE: %s; TIMESTAMP: %d; BLACKLIST: %s; COMMAND LINE: \"<python> %s\"\n\n\n\n\n\n" % (str(time.tzname), self.date.strftime("%Y-%m-%d %H:%M:%S"), self.date.timestamp(), str(self.blacklist), self.command_line))

    def write(self, content):
        for pattern in self.blacklist:
            if re.match(pattern, content):
                return

        if not self.date.date() == datetime.now().date():
            self.create_file()

        if self.path:
            self.file.write(content)

        self.stream.write(content)      

def main():
    stream = sys.stdout
    flags = re.findall(r" -+[\w]+ ?\S*", " ".join(sys.argv))

    logging_enabled = False
    path = None
    blacklist = []

    token = None
    bot = True

    for flag in flags:
        flag = flag.split()

        if flag[0] in ["-h", "--help"]:
            print(""""cenzura to bot, bot to cenzura"

    -h  or --help                shows help
    -l  or --logging             enable logging
    -lt or --logterminal         prints logs to a specified terminal
    -p  or --path                saves logs to a specified path
    -bl or --blacklist           for example "^[\\d\\s:,-]+\\[DEBUG:.+\\].(sent.)?op:.HEARTBEAT.+$" or "^.+event.name:.PRESENCE_UPDATE$"
    -t  or --token               bot token
    -b  or --bot <true/false>    true if token is a bot token""")
            exit(0)
        elif flag[0] in ["-l", "--logging"]:
            logging_enabled = True
        elif flag[0] in ["-lt", "--logterminal"]:
            logging_enabled = True
            stream = open("/dev/pts/" + flag[1], "w")
        elif flag[0] in ["-p", "--path"]:
            path = flag[1]
        elif flag[0] in ["-bl", "--blacklist"]:
            blacklist.append(flag[1])
        elif flag[0] in ["-t", "--token"]:
            token = flag[1]
        elif flag[0] in ["-b", "--bot"]:
            bot = flag[1] == "true"

    if logging_enabled is True:
        logging.basicConfig(stream=StreamHandler(stream, path, blacklist, " ".join(sys.argv)), level=logging.DEBUG, format="%(asctime)s [%(levelname)s:%(module)s] %(message)s")

    Bot(start_time=start_time).run(token or config.TOKEN, bot=bot)

if __name__ == "__main__":
    main()