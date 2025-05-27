import os
basedir = os.path.abspath(os.path.dirname(__file__))

class TestConfig:
    TESTING = True
    SECRET_KEY = 'test_secret_key'
    # Use in-memory SQLite for tests for speed and isolation
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False # Often disabled for tests for simplicity
    BCRYPT_LOG_ROUNDS = 4 # Speed up hashing for tests, default is 12
    LOGIN_DISABLED = False # Ensure login is not disabled unless specifically testing that feature
    # For Flask-Login, ensure it knows we're testing
    # SERVER_NAME = 'localhost.localdomain' # Can be needed for url_for in some test contexts without live server
    # APPLICATION_ROOT = '/'
    # PREFERRED_URL_SCHEME = 'http'
