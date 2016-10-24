import tornado.web
from datetime import date


class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def parse_query(self, data, description):
        if type(data) == list:
            result = []
            for value in data:
                result.append(self.parse_query(value, description))
        elif type(data) == tuple:
            result = {}
            for i in range(len(description)):
                if type(data[i]) == date:
                    value = data[i].strftime('%Y-%m-%d')
                else:
                    value = data[i]
                result[description[i][0]] = value
        else:
            result = {}
        return result
