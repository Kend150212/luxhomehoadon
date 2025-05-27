import pytest
from app import create_app, db as _db # Renamed to _db to avoid conflict

@pytest.fixture(scope='session')
def app():
    """Session-wide test `Flask` application."""
    # Ensure test_config.py defines SQLALCHEMY_DATABASE_URI for an in-memory SQLite or a test DB
    _app = create_app(config_class_name='test_config.TestConfig')
    return _app

@pytest.fixture(scope='function')
def test_client(app):
    """A test client for the app."""
    with app.test_client() as client:
        with app.app_context(): # Ensure context is active for db operations
            yield client

@pytest.fixture(scope='function')
def db_instance(app): # Renamed from 'db' to avoid fixture name conflict if 'db' is imported directly
    """Session-wide test database."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()
