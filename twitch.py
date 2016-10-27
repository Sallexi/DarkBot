import socket
import tornado
import tornado.iostream
import tornado.gen
from tornado.ioloop import IOLoop
from tornado import httpclient
from datetime import datetime
import dateutil.parser
import inspect
import json


class Twitch(object):
    def __init__(self, username, password, client_id, db):
        self.server_address = 'irc.twitch.tv'
        self.port = 6667
        self.username = username
        self.password = password
        self.client_id = client_id
        self.encoding = 'utf-8'
        self.ioloop = IOLoop.current()
        self.followers = {}
        self.chatters_last_update = None
        self.db = db
        self.__handlers = {b'PING': self.ping,
                           b'376': self.motd_end,
                           b'PRIVMSG': self.message}

        # Create a web client
        httpclient.AsyncHTTPClient.configure('tornado.curl_httpclient.CurlAsyncHTTPClient')
        self.web_client = httpclient.AsyncHTTPClient()

        # Initially load data
        self.load_followers(say_new=False)
        self.load_chatters()

        # Check every 1 minute
        tornado.ioloop.PeriodicCallback(self.load_followers, 60000).start()
        tornado.ioloop.PeriodicCallback(self.load_chatters, 60000).start()

        # Create a new TCP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        # Create an async io stream
        self.stream = tornado.iostream.IOStream(sock)
        # Open the connection
        self.stream.connect((self.server_address, self.port),
                            self.__connected,
                            self.server_address)

    def __connected(self):
        self.send('PASS ' + self.password)
        self.send('NICK ' + self.username)
        self.stream.read_until_close(self.closed, self.__route)

    def __route(self, data):
        lines = data.split(b'\r\n')
        prefix = b''

        for line in lines:
            # Make sure line is not empty
            if line:
                if line.startswith(b':'):
                    idx = line.find(b' ')
                    prefix = line[1:idx]
                else:
                    idx = 0
                irc_msg = line[idx + 1 if idx > 0 else idx:].split(b' :')
                message = b''.join(irc_msg[1:]).strip()
                irc_msg = irc_msg[0].split(b' ')
                command = irc_msg[0]
                params = irc_msg[1:]

                if command in self.__handlers.keys():
                    handler = self.__handlers[command]
                    kwargs = inspect.signature(handler).parameters.keys()
                    if len(inspect.signature(handler).parameters) > 0:
                        irc_args = {'prefix': prefix,
                                    'command': command,
                                    'params': params,
                                    'message': message}
                        kwargs = {k: irc_args[k] for k in irc_args if k in kwargs}
                        handler(**kwargs)
                    else:
                        handler()
                else:
                    print(line)
                    print('(Unhandled) Pfx: %s,Cmd: %s,Param: %s, Msg: %s' % (prefix, command, params, message))

    def send(self, message: str):
        if message[-2:] != '\r\n':
            message += '\r\n'
        message = message.encode(self.encoding)
        self.stream.write(message)

    def ping(self, message):
        response = 'PONG %s' % message.decode(self.encoding)
        self.send(response)

    def motd_end(self, message):
        self.send('JOIN #darkvalkyrieprincess')

    @tornado.gen.coroutine
    def message(self, message, params, prefix):
        # Convert to strings
        user = prefix.decode(self.encoding)
        channel = params[0].decode(self.encoding)
        message = message.decode(self.encoding)

        # Extract user from account string
        # Example: nickname!account@server
        user = user[:user.find('!')]

        if message == '!followers':
            self.fetch_api('/channels/darkvalkyrieprincess/follows', self.say_followers)
        elif message == '!top5':
            top_users = sorted(self.followers, key=(lambda user: self.followers[user]['follow_date']))[:5]
            top_users = [(rank + 1, self.get_name(uid)) for rank, uid in enumerate(top_users)]
            top_users = ' '.join('%s. %s' % user for user in top_users)
            self.say(top_users, channel)
        elif message == '!topviewer':
            result = yield self.db.execute(
                """
                SELECT username, watch_time
                FROM darkbot.users
                WHERE username <> 'darkvalkyrieprincess'
                ORDER BY watch_time DESC
                LIMIT 1
                """)
            result = result.fetchone()
            self.say('%s has watched for a total of %s hours!!' % (result[0], round(result[1]/3600, 2)), channel)
        print('%s : %s : %s' % (channel, user, message))

    def get_name(self, user_id):
        return self.followers[user_id]['name']

    def say_followers(self, response):
        if not response.error:
            data = json.loads(response.body.decode(self.encoding))
            self.say('I have %s followers!' % data['_total'], '#darkvalkyrieprincess')

    def say(self, message: str, target: str):
        self.send('PRIVMSG %s :%s' % (target, message))

    @tornado.gen.coroutine
    def load_chatters(self, response=None):
        if response and not response.error:
            chatters = json.loads(response.body.decode(self.encoding))
            users = []

            if chatters['chatter_count'] == 0:
                return

            if self.chatters_last_update is not None:
                time_delta = datetime.now() - self.chatters_last_update
            else:
                time_delta = datetime.now() - datetime.now()

            for group in chatters['chatters']:
                for user in chatters['chatters'][group]:
                    users.append(user)
                    users.append(group)
                    users.append(time_delta.seconds)
                    users.append(datetime.utcnow())
                    users.append(datetime.utcnow())

            if len(users) > 1:
                values = ' (%s, %s, %s, %s, %s),' * int(len(users) / 5)
                values = values[:-1]
            else:
                values = ' (%s %s %s %s %s)'

            self.chatters_last_update = datetime.now()
            yield self.db.execute(
                "INSERT INTO darkbot.users (username, chat_group, watch_time, first_noticed, last_noticed) "
                "VALUES" + values +
                " ON CONFLICT (username) "
                "DO UPDATE SET "
                "chat_group = EXCLUDED.chat_group, "
                "watch_time = EXCLUDED.watch_time + users.watch_time, "
                "last_noticed = EXCLUDED.last_noticed",
                users)

            print(datetime.now().strftime('%I:%M') + ' Updated chatters')
        else:
            self.fetch_tmi('/group/user/darkvalkyrieprincess/chatters', self.load_chatters)

    def load_followers(self, say_new=True):
        self.fetch_api('/channels/darkvalkyrieprincess/follows', lambda x: self.check_followers(x, say_new=say_new))

    def check_followers(self, response=None, say_new=True):
        if response and not response.error:
            followers = json.loads(response.body.decode(self.encoding))

            # Get user ids and names
            users = {}
            for follower in followers['follows']:
                user_id = follower['user']['_id']
                users[user_id] = {}
                users[user_id]['name'] = follower['user']['display_name']
                users[user_id]['follow_date'] = dateutil.parser.parse(follower['created_at'])
                if user_id not in self.followers and say_new:
                    self.say('%s is now following!' % users[user_id]['name'], '#darkvalkyrieprincess')
            self.followers = users

    def fetch_tmi(self, url, handler):
        if not url.startswith('/'):
            url = '/' + url

        self.web_client.fetch('https://tmi.twitch.tv' + url,
                              handler,
                              validate_cert=False,
                              headers={'Accept': 'application/vnd.twitchtv.v3+json',
                                       'Client-ID': self.client_id})

    def fetch_api(self, url, handler):
        if not url.startswith('/'):
            url = '/' + url

        self.web_client.fetch('https://api.twitch.tv/kraken' + url,
                              handler,
                              validate_cert=False,
                              headers={'Accept': 'application/vnd.twitchtv.v3+json',
                                       'Client-ID': self.client_id})

    def closed(self, data):
        pass
