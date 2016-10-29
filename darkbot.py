import tornado.ioloop
import tornado.web
import momoko
from twitch import Twitch
from config import load_config
from page_handlers import pages


def make_app():
    return tornado.web.Application(
        [(r'/', pages.MainHandler),
         (r'/channel', pages.Channel),
         (r'/chat_statistics', pages.ChatStatistics),
         (r'/logs', pages.Logs),
         (r'/development', pages.Development),
         (r'/images/(.*)', tornado.web.StaticFileHandler, {'path': 'web/static/images'})],
        compiled_template_cache=conf['web']['compiled_template_cache'],
        static_path='web/static',
        template_path='web/templates'
    )


if __name__ == '__main__':
    conf = load_config()

    # Create a new web application
    app = make_app()
    app.listen(8181)

    # Connect to the database
    ioloop = tornado.ioloop.IOLoop.current()
    app.db = momoko.Pool(dsn='dbname=%s user=%s password=%s host=%s port=%s application_name=DarkBot' %
                             (conf['db']['name'], conf['db']['user'], conf['db']['pass'],
                              conf['db']['host'], conf['db']['port']),
                         size=1,
                         max_size=10,
                         auto_shrink=True,
                         ioloop=ioloop)
    future = app.db.connect()
    ioloop.add_future(future, lambda f: ioloop.stop())
    ioloop.start()
    future.result()  # raises exception on connection error
    app.bot = Twitch(conf['username'],
                     conf['password'],
                     conf['client_id'],
                     app.db)
    ioloop.start()
