import socket
import tornado
import tornado.iostream
from tornado.ioloop import IOLoop
from tornado import httpclient
import dateutil.parser
import inspect
import json


class Twitch(object):
    def __init__(self, username, password, client_id):
        self.server_address = 'irc.twitch.tv'
        self.port = 6667
        self.username = username
        self.password = password
        self.client_id = client_id
        self.encoding = 'utf-8'
        self.ioloop = IOLoop.current()
        self.followers = {}
        httpclient.AsyncHTTPClient.configure('tornado.curl_httpclient.CurlAsyncHTTPClient')
        self.web_client = httpclient.AsyncHTTPClient()
        self.__handlers = {b'PING': self.ping,
                           b'376': self.motd_end,
                           b'PRIVMSG': self.message}

        # Initially load followers
        self.load_followers(say_new=False)

        # Check followers every 1 minute
        tornado.ioloop.PeriodicCallback(self.load_followers, 60000).start()

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
        idx = 0

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
        print(response)
        self.send(response)

    def motd_end(self, message):
        self.send('JOIN #darkvalkyrieprincess')

    def message(self, message, params, prefix):
        # Convert to strings
        user = prefix.decode(self.encoding)
        channel = params[0].decode(self.encoding)
        message = message.decode(self.encoding)

        # Extract user from account string
        # Example: nickname!account@server
        user = user[:user.find('!')]

        if message == '!followers':
            self.fetch('/channels/darkvalkyrieprincess/follows', self.say_followers)
        if message == '!top5':
            top_users = sorted(self.followers, key=(lambda user: self.followers[user]['follow_date']))[:5]
            top_users = [(rank + 1, self.get_name(uid)) for rank, uid in enumerate(top_users)]
            top_users = ' '.join('%s. %s' % user for user in top_users)
            self.say(top_users, channel)

        print('%s : %s : %s' % (channel, user, message))

    def get_name(self, user_id):
        return self.followers[user_id]['name']

    def say_followers(self, response):
        if not response.error:
            data = json.loads(response.body.decode(self.encoding))
            self.say('I have %s followers!' % data['_total'], '#darkvalkyrieprincess')

    def say(self, message: str, target: str):
        self.send('PRIVMSG %s :%s' % (target, message))

    def load_followers(self, say_new=True):
        self.fetch('/channels/darkvalkyrieprincess/follows', lambda x: self.check_followers(x, say_new=say_new))

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

    def fetch(self, url, handler):
        if not url.startswith('/'):
            url = '/' + url

        self.web_client.fetch('https://api.twitch.tv/kraken' + url,
                              handler,
                              validate_cert=False,
                              headers={'Accept': 'application/vnd.twitchtv.v3+json',
                                       'Client-ID': self.client_id})

    def closed(self, data):
        pass
