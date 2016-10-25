from .base import BaseHandler


class MainHandler(BaseHandler):
    def get(self):
        self.render('dashboard.html')


class Channel(BaseHandler):
    def get(self):
        self.render('channel.html')
