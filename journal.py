#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A Pyramid app for my learning journal

"""
from __future__ import unicode_literals
import os
from pyramid.config import Configurator
from pyramid.view import view_config
from waitress import serve
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from zope.sqlalchemy import ZopeTransactionExtension
import datetime
from pyramid.httpexceptions import HTTPFound
from sqlalchemy.exc import DBAPIError
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from cryptacular.bcrypt import BCRYPTPasswordManager


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://jesse:Jjk5646!@localhost:5432/learning-journal'
)


Base = declarative_base()
engine = sa.create_engine(DATABASE_URL)
# Session = sessionmaker(bind=engine)


class Entry(Base):
    """Make a new entry
    """
    __tablename__ = 'entries'
    id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
    title = sa.Column(sa.Unicode(127), nullable=False)
    date = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    content = sa.Column(sa.UnicodeText, nullable=False)

    @classmethod
    def write(cls, title=None, content=None, session=None):
        if session is None:
            session = DBSession
        instance = cls(title=title, content=content)
        session.add(instance)
        return instance

    @classmethod
    def all(cls, session=None):
        if session is None:
            session = DBSession
        return session.query(cls).order_by(cls.date.desc()).all()


def init_db():
    """Make a new entries table
    """
    Base.metadata.create_all(bind=engine)


@view_config(route_name='home', renderer='templates/list.jinja2')
def list_view(request):
    entries = Entry.all()
    return {'entries': entries}


@view_config(route_name='add', request_method='POST')
def add_entry(request):
    title = request.params.get('title')
    content = request.params.get('content')
    Entry.write(title=title, content=content)
    return HTTPFound(request.route_url('home'))


@view_config(context=DBAPIError)
def db_exception(context, request):
    from pyramid.response import Response
    response = Response(context.message)
    response.status_int = 500
    return response


#@view_config(route_name='home', renderer='string')
#def home(request):
#    return "Hello World"


def main():
    """Create a configured wsgi app"""
    settings = {}
    debug = os.environ.get('DEBUG', True)
    settings['reload_all'] = debug
    settings['debug_all'] = debug
    settings['auth.username'] = os.environ.get('AUTH_USERNAME', 'admin')
    manager = BCRYPTPasswordManager()
    settings['auth.password'] = os.environ.get(
        'AUTH_PASSWORD', manager.encode('secret')
    )
    if not os.environ.get('TESTING', False):
        # only bind the session if we are not testing
        engine = sa.create_engine(DATABASE_URL)
        DBSession.configure(bind=engine)
    # add a secret value for auth tkt signing
    auth_secret = os.environ.get('JOURNAL_AUTH_SECRET', 'itsaseekrit')
    # and add a new value to the constructor for our Configurator:
    config = Configurator(
        settings=settings,
        authentication_policy=AuthTktAuthenticationPolicy(
            secret=auth_secret,
            hashalg='sha512'
        ),
        authorization_policy=ACLAuthorizationPolicy(),
    )
    config.include('pyramid_tm')
    config.include('pyramid_jinja2')
    config.add_route('home', '/')
    config.add_route('add', '/add')
    config.scan()
    app = config.make_wsgi_app()
    return app


def do_login(request):
    username = request.params.get('username', None)
    password = request.params.get('password', None)
    if not (username and password):
        raise ValueError('both username and password are required')

    settings = request.registry.settings
    manager = BCRYPTPasswordManager()
    if username == settings.get('auth.username', ''):
        hashed = settings.get('auth.password', '')
        return manager.check(hashed, password)
    return False


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
