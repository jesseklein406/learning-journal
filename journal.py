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


DBSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://jesse:Jjk5646!@localhost:5432/learning-journal'
)


Base = declarative_base()
engine = sa.create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


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


#@view_config(route_name='home', renderer='string')
#def home(request):
#    return "Hello World"


def main():
    """Create a configured wsgi app"""
    settings = {}
    debug = os.environ.get('DEBUG', True)
    settings['reload_all'] = debug
    settings['debug_all'] = debug
    if not os.environ.get('TESTING', False):
        # only bind the session if we are not testing
        engine = sa.create_engine(DATABASE_URL)
        DBSession.configure(bind=engine)
    # configuration setup
    config = Configurator(
        settings=settings
    )
    config.include('pyramid_tm')
    config.include('pyramid_jinja2')
    config.add_route('home', '/')
    config.scan()
    app = config.make_wsgi_app()
    return app


if __name__ == '__main__':
    app = main()
    port = os.environ.get('PORT', 5000)
    serve(app, host='0.0.0.0', port=port)
