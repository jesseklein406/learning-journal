import pytest
import journal


TEST_DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://jesse:Jjk5646!@localhost:5432/test-learning-journal'
)
os.environ['DATABASE_URL'] = TEST_DATABASE_URL

os.environ['TESTING'] = "True"


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


@pytest.fixture()
def app():
    from journal import main
    from webtest import TestApp
    app = main()
    return TestApp(app)


@pytest.fixture()
def homepage(app):
    response = app.get('/')
    return response
