import webapp2
import jinja2
import os
import time

from google.appengine.ext import db
from google.appengine.api import memcache
from datetime import datetime, timedelta

template_path = os.path.join(os.path.dirname(__file__),'templates')
environment = jinja2.Environment(loader = jinja2.FileSystemLoader(template_path), autoescape = False)
environment_escaped = jinja2.Environment(loader = jinja2.FileSystemLoader(template_path), autoescape = True)

class Pluses(db.Model):
    thx_value = db.IntegerProperty(required = True)
    ip_address = db.StringProperty(required = True)
    thx_created = db.DateTimeProperty(auto_now_add = True)

def load_plus(thx_value = None, ip_address = None, update = False):
    key = 'last_thx'

    if update and thx_value:
            pluses = Pluses(thx_value=thx_value, ip_address=ip_address)
            pluses.put()

            memcache.set(key, thx_value)
    else:
        result = memcache.get(key)

        if not result:
            pl = Pluses.gql("ORDER BY thx_created DESC")
            pl.get()
            
            if pl.count() > 0:
                memcache.set(key, pl[0].thx_value)
            else:
                memcache.set(key, 0)

    return memcache.get(key)

class Handler(webapp2.RequestHandler):
    
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        t = environment.get_template(template)

        return t.render(params)

    def render_str_escaped(self, template, **params):
        t = environment_escaped.get_template(template)

        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
        
    def render_content(self, template, **kw):
        content = self.render_str(template, **kw)
        self.render("index.htm", content=content, **kw)

    def render_trucking(self, template, **kw):
        content = self.render_str(template, **kw)
        self.render("trucking.htm", content=content, **kw)

class Passenger(Handler):

    def post(self):
        thx_value = load_plus()
        ip_address = self.request.remote_addr
        result = db.GqlQuery("SELECT * FROM Pluses WHERE ip_address = :1 ORDER BY thx_created DESC", ip_address)

        if result.count() > 0:
            restriction = 360 # Time limit for next voiting if IP equals.
            if (datetime.now() - result[0].thx_created) < timedelta(minutes = restriction):
                msg = 'err'
            else:
                msg = 'thx'
                thx_value = thx_value + 1
                load_plus(thx_value=thx_value, ip_address=ip_address, update = True)
        else:
            msg = 'thx'
            thx_value = thx_value + 1
            load_plus(thx_value=thx_value, ip_address=ip_address, update = True)

        extra = [thx_value, msg]
        self.render_content("plus.htm", extra=extra)

    def get(self):
        msg=''
        thx_value = load_plus()

        extra = [thx_value, msg]
        self.render_content("plus.htm", extra=extra)


class Trucking(Handler):
    
    def get(self):
        self.render_trucking("info.htm")


class Tariffs(Handler):
    
    def get(self):
        self.render_trucking("tariffs.htm")

class Contacts(Handler):
    
    def get(self):
        self.render_trucking("contacts.htm")

class Request(Handler):
    
    def get(self):
        self.render_trucking("request.htm")


class RedirectPassenger(Handler):

    def get(self):
        self.redirect("/passenger")


class NotFound(Handler):

    def get(self):
        self.render("404.htm")


app = webapp2.WSGIApplication([
        ('/passenger', Passenger)
        , ('/trucking', Trucking)
        , ('/trucking/tariffs', Tariffs)
        , ('/trucking/contacts', Contacts)
        , ('/trucking/request', Request)
        , ('/', RedirectPassenger)
        , ('/.*', NotFound)
    ], debug=False)