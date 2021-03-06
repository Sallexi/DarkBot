from .base import BaseHandler


class MainHandler(BaseHandler):
    def get(self):
        self.render('dashboard.html')


class Channel(BaseHandler):
    def get(self):
        self.render('channel.html')


class ChatStatistics(BaseHandler):
    def get(self):
        self.render('chat_statistics.html')


class Logs(BaseHandler):
    def get(self):
        self.render('logs.html')


class Development(BaseHandler):
    def get(self):
        self.render('development.html')
