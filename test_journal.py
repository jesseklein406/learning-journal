# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
import webtest
from pyramid import testing
from cryptacular.bcrypt import BCRYPTPasswordManager

TEST_DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://jesse:Jjk5646!@localhost:5432/test-learning-journal'
)
os.environ['DATABASE_URL'] = TEST_DATABASE_URL

os.environ['TESTING'] = "True"

import journal


@pytest.fixture(scope='session')
def connection(request):
    engine = create_engine(TEST_DATABASE_URL)
    journal.Base.metadata.create_all(engine)
    connection = engine.connect()
    journal.DBSession.registry.clear()
    journal.DBSession.configure(bind=connection)
    journal.Base.metadata.bind = engine
    request.addfinalizer(journal.Base.metadata.drop_all)
    return connection


@pytest.fixture()
def db_session(request, connection):
    from transaction import abort
    trans = connection.begin()
    request.addfinalizer(trans.rollback)
    request.addfinalizer(abort)

    from journal import DBSession
    return DBSession


def test_write_entry(db_session):
    kwargs = {'title': "Test Title", 'content': "Test entry text"}
    kwargs['session'] = db_session
    # first, assert that there are no entries in the database:
    assert db_session.query(journal.Entry).count() == 0
    # now, create an entry using the 'write' class method
    entry = journal.Entry.write(**kwargs)
    # the entry we get back ought to be an instance of Entry
    assert isinstance(entry, journal.Entry)
    # id and created are generated automatically, but only on writing to
    # the database
    auto_fields = ['id', 'date']
    for field in auto_fields:
        assert getattr(entry, field, None) is None
    # flush the session to "write" the data to the database
    db_session.flush()
    # now, we should have one entry:
    assert db_session.query(journal.Entry).count() == 1
    for field in ['title', 'content']:
        if field != 'session':
            assert getattr(entry, field, '') == kwargs[field]
    # id and created should be set automatically upon writing to db:
    for auto in ['id', 'date']:
        assert getattr(entry, auto, None) is not None


def test_entry_no_title_fails(db_session):
    bad_data = {'content': 'test text'}
    journal.Entry.write(session=db_session, **bad_data)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_entry_no_text_fails(db_session):
    bad_data = {'title': 'test title'}
    journal.Entry.write(session=db_session, **bad_data)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_read_entries_empty(db_session):
    entries = journal.Entry.all()
    assert len(entries) == 0


def test_read_entries_one(db_session):
    title_template = "Title {}"
    text_template = "Entry Text {}"
    # write three entries, with order clear in the title and text
    for x in range(3):
        journal.Entry.write(
            title=title_template.format(x),
            content=text_template.format(x),
            session=db_session)
        db_session.flush()
    entries = journal.Entry.all()
    assert len(entries) == 3
    assert entries[0].title > entries[1].title > entries[2].title
    for entry in entries:
        assert isinstance(entry, journal.Entry)


@pytest.fixture()
def app():
    from journal import main
    from webtest import TestApp
    app = main()
    return TestApp(app)


def test_empty_listing(app):
    response = app.get('/')
    assert response.status_code == 200
    actual = response.body
    expected = 'No entries here so far'
    assert expected in actual


@pytest.fixture()
def entry(db_session):
    kwargs = {'title': "Test Title", 'content': "Test Entry Text"}
    kwargs['session'] = db_session
    # first, assert that there are no entries in the database:
    # assert db_session.query(journal.Entry).count() == 0
    # now, create an entry using the 'write' class method
    entry = journal.Entry.write(**kwargs)
    db_session.flush()
    return entry


def test_listing(app, entry):
    response = app.get('/')
    assert response.status_code == 200
    actual = response.body
    for field in ['title']:   # Remove 'content' from field in list view
        expected = getattr(entry, field, 'absent')
        assert expected in actual


def test_post_to_add_view(app):
    entry_data = {
        'title': 'Hello there',
        'content': 'This is a post',
    }
    response = app.post('/add', params=entry_data, status='3*')
    redirected = response.follow()
    actual = redirected.body
    for expected in entry_data.values()[0]:   # Just the 'title' for list view
        assert expected in actual


def test_try_to_get(app):
    with pytest.raises(webtest.AppError):
        app.get('/add')


def test_add_no_params(app):
    test_login_success(app)
    response = app.post('/add', status=500)
    assert 'IntegrityError' in response.body


@pytest.fixture(scope='function')
def auth_req(request):
    manager = BCRYPTPasswordManager()
    settings = {
        'auth.username': 'admin',
        'auth.password': manager.encode('secret')
    }
    testing.setUp(settings=settings)
    req = testing.DummyRequest()

    def cleanup():
        testing.tearDown()

    request.addfinalizer(cleanup)

    return req


def test_do_login_success(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'admin', 'password': 'secret'}
    assert do_login(auth_req)


def test_do_login_bad_pass(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'admin', 'password': 'wrong'}
    assert not do_login(auth_req)


def test_do_login_bad_user(auth_req):
    from journal import do_login
    auth_req.params = {'username': 'bad', 'password': 'secret'}
    assert not do_login(auth_req)


def test_do_login_missing_params(auth_req):
    from journal import do_login
    for params in ({'username': 'admin'}, {'password': 'secret'}):
        auth_req.params = params
        with pytest.raises(ValueError):
            do_login(auth_req)


INPUT_BTN = '<input type="submit" value="Share" name="Share"/>'
CREATE_LINK = '<a href="http://localhost/create">CREATE</a>'   # nav bar link


def login_helper(username, password, app):
    """encapsulate app login for reuse in tests

    Accept all status codes so that we can make assertions in tests
    """
    login_data = {'username': username, 'password': password}
    return app.post('/login', params=login_data, status='*')


def test_start_as_anonymous(app):
    response = app.get('/', status=200)
    actual = response.body
    assert CREATE_LINK not in actual   # check for 'CREATE' in nav bar


def test_login_success(app):
    username, password = ('admin', 'secret')
    redirect = login_helper(username, password, app)
    assert redirect.status_code == 302
    response = redirect.follow()
    assert response.status_code == 200
    actual = response.body
    assert CREATE_LINK in actual


def test_login_fails(app):
    username, password = ('admin', 'wrong')
    response = login_helper(username, password, app)
    assert response.status_code == 200
    actual = response.body
    assert "Login Failed" in actual
    assert CREATE_LINK not in actual


def test_logout(app):
    # re-use existing code to ensure we are logged in when we begin
    test_login_success(app)
    redirect = app.get('/logout', status="3*")
    response = redirect.follow()
    assert response.status_code == 200
    actual = response.body
    assert CREATE_LINK not in actual


def test_no_create_form_on_home(app):
    username, password = ('admin', 'secret')
    redirect = login_helper(username, password, app)
    assert redirect.status_code == 302
    response = redirect.follow()
    assert response.status_code == 200
    actual = response.body
    assert INPUT_BTN not in actual    # check that create form is not at home


def test_create_page_has_form(app):
    test_login_success(app)
    response = app.get('/create', status=200)
    actual = response.body
    assert INPUT_BTN in actual    # check that create form is in create page


def test_hacker_cannot_create(app):
    redirect = app.get('/create', status="3*")
    assert redirect.status_code == 302
    response = redirect.follow()
    assert response.status_code == 200
    actual = response.body
    assert INPUT_BTN not in actual    # ensure that hackers get redirected


# Issue 1

def test_view_unit_test_for_permalink():
    form_str = '<form action="{{ request.route_url(%s) }}" method="get">' % "'detail'"
    with open('templates/index.jinja2') as f:
        home = f.read()
    assert form_str in home


def test_bdd_test_for_permalink(app, entry):  # Add 'entry' to get a test entry
    form_str = '<form action="http://localhost/detail" method="get">'
    response = app.get('/', status=200)
    assert form_str in response


def test_bdd_test_for_detail_content(app, entry):  # Add 'entry' to get a test entry
    content_str = '<p>Test Entry Text</p>'
    response = app.get('/detail', params={'id': entry.id}, status=200)
    assert content_str in response


# Issue 2

def test_view_unit_test_for_add_editing():
    form_str = '<form action="{{ request.route_url(%s) }}" method="get">' % "'edit'"
    with open('templates/detail.jinja2') as f:
        detail = f.read()
    assert form_str in detail


def test_bdd_test_for_edit_button(app, entry):  # Add 'entry' to get a test entry
    test_login_success(app)
    form_str = '<form action="http://localhost/edit" method="get">'
    response = app.get('/detail', params={'id': entry.id}, status=200)
    assert form_str in response


def test_bdd_test_for_add_editing(app, entry):  # Add 'entry' to get a test entry
    test_login_success(app)
    # Test for editable title form in response
    form_str = '<input type="text" name="title" value="Test Title" class="title-input">'
    response = app.get('/edit', params={'id': entry.id}, status=200)
    assert form_str in response


def test_bdd_test_for_try_editing(app, entry):  # Add 'entry' to get a test entry
    test_login_success(app)
    # Test for editable title form in response
    new_title = 'new title'
    params = {'title': 'new title', 'content': 'new stuff', 'id': entry.id}
    response = app.post('/commit', params=params, status='3*')
    redirected = response.follow()
    assert new_title in redirected


# Check security against sneaky requests penetration

def test_hacker_cannot_post_to_add(app):
    params = {'title': 'hacker', 'content': 'going hacking'}
    response = app.post('/add', params=params, status='3*')
    redirected = response.follow()
    assert "Login" in redirected    # hackers get redirected to Login


def test_hacker_cannot_post_to_commit(app):
    params = {'title': 'hacker', 'content': 'going hacking', 'id': 1}
    response = app.post('/commit', params=params, status='3*')
    redirected = response.follow()
    assert "Login" in redirected    # hackers get redirected to Login
