import tornado.ioloop
from twitch import Twitch
from config import load_config


conf = load_config()
bot = Twitch(conf['username'],
             conf['password'],
             conf['client_id'])
tornado.ioloop.IOLoop.instance().start()
