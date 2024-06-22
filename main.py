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

import logging, socket, threading, re, sys, io, time, config, argparse, os, tarfile
from datetime import datetime
from bot import Bot

start_time = time.time()

class TCPServer:
    def __init__(self, port, max_clients):
        self.port = port
        self.max_clients = max_clients

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(("127.0.0.1", self.port))
        self.server.listen(self.max_clients)

        self.clients = []

        self.accept_thread = threading.Thread(target=self.accept_clients, daemon=True)
        self.accept_thread.start()

    def send(self, message):
        data = message.encode("utf-8")

        for client in self.clients:
            try:
                client.send(data)
            except Exception:
                self.clients.remove(client)
                client.close()
                continue

    def accept_clients(self):
        while True:
            client, _ = self.server.accept()
            self.clients.append(client)

class StreamHandler(io.StringIO):
    def __init__(self, stream, path, blacklist, command_line, tcp_server):
        super().__init__()

        self.stream = stream
        self.path = path
        self.blacklist = blacklist
        self.command_line = command_line
        self.tcp_server = tcp_server
        self.date = None

        self.file = None

        while self.path and self.path[-1] == "/":
            self.path = self.path[:-1]

        self.init_file()

    def init_file(self):
        self.date = datetime.now()

        if self.path:
            self.file = open(self.path + "/latest.log", "a")
            self.file.write("\n\n\n\n\nTIMEZONE: %s; DATE: %s; TIMESTAMP: %d; BLACKLIST: %s; COMMAND LINE: \"<python> %s\"\n\n\n\n\n\n" % (str(time.tzname), self.date.strftime("%Y-%m-%d %H:%M:%S"), self.date.timestamp(), str([expression.pattern for expression in self.blacklist]), self.command_line))

    def write(self, content):
        for pattern in self.blacklist:
            if pattern.match(content):
                return

        if not self.date.date() == datetime.now().date():
            y, m, d = self.date.strftime("%Y %m_%B %d").split()

            if not os.path.exists(self.path + "/%s" % y):
                os.mkdir(self.path + "/%s" % y)
            if not os.path.exists(self.path + "/%s/%s" % (y, m)):
                os.mkdir(self.path + "/%s/%s" % (y, m))

            with tarfile.open(self.path + "/%s/%s/%s" % (y, m, d) + ".tar.gz", "w:gz") as tar:
                tar.add(self.path + "/latest.log", "%s-%s-%s.log" % (y, m.split("_")[0], d))

            old_file = self.file
            self.file = None
            old_file.close()
            with open(self.path + "/latest.log", "w") as file:
                file.write("")
            self.init_file()

        if self.path is not None:
            self.file.write(content)

        self.stream.write(content)

        if self.tcp_server is not None:
            threading.Thread(target=self.tcp_server.send, args=(content,), daemon=True).start()

def main():
    parser = argparse.ArgumentParser(description="cenzura is a bot, the bot is cenzura")
    parser.add_argument("--logging", "-l", help="enable logging")
    parser.add_argument("--logterminal", "-lt", help="prints logs to specified terminal")
    parser.add_argument("--path", "-p", help="saves logs to specified path")
    parser.add_argument("--blacklist", "-bl", nargs="*", action="append", help="for example \"^[\\d\\s:,-]+\\[DEBUG:.+\\].(sent.)?op:.(HEARTBEAT|PRESENCE_UPDATE).+$" or "^.+event.name:.PRESENCE_UPDATE$\"")
    parser.add_argument("--serverport", "-sp", type=int, help="tcp server port")
    parser.add_argument("--clients", "-c", type=int, help="maximum number of clients")
    parser.add_argument("--token", "-t", help="bot token")
    parser.add_argument("--bot", "-b", help="true if token is a bot token", choices=("true", "false"))

    args = parser.parse_args()

    stream = sys.stdout

    logging_enabled = False
    path = None
    blacklist = []

    server_port = None
    max_clients = None

    token = None
    bot = True

    if args.logging:
        logging_enabled = True

    if args.logterminal:
        logging_enabled = True
        stream = open("/dev/pts/" + args.logterminal, "w")

    if args.path:
        path = args.path

    if args.blacklist:
        blacklist = [re.compile(blacklisted[0]) for blacklisted in args.blacklist]

    if args.serverport:
        server_port = args.serverport

    if args.clients:
        max_clients = args.clients

    if args.token:
        token = args.token

    if args.bot:
        bot = args.bot == "true"

    if logging_enabled is True:
        tcp_server = None

        if server_port is not None:
            tcp_server = TCPServer(server_port, max_clients or 5)

        logging.basicConfig(stream=StreamHandler(stream, path, blacklist, " ".join(sys.argv), tcp_server), level=logging.DEBUG, format="%(asctime)s [%(levelname)s:%(module)s] %(message)s")

    Bot(start_time=start_time).run(token or config.TOKEN, bot=bot)

    if tcp_server is not None:
        try:
            while True:
                time.sleep(60)
        except (Exception, KeyboardInterrupt, SystemExit):
            tcp_server.server.close()

            for client in tcp_server.clients:
                client.close()

if __name__ == "__main__":
    main()