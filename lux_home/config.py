import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'a_super_secret_key_for_production_env'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Add other common configurations here

class DevelopmentConfig(Config):
    DEBUG = True
    # SQLALCHEMY_ECHO = True # Useful for debugging SQL queries

class TestConfig(Config): # This will be used by test_config.py, but good to have a base here
    TESTING = True
    SECRET_KEY = 'test_secret_key' # Override for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # Ensure tests use in-memory
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False
    BCRYPT_LOG_ROUNDS = 4
    LOGIN_DISABLED = False # Ensure login is not disabled unless testing that

class ProductionConfig(Config):
    DEBUG = False
    # Example: Use a different database for production
    # SQLALCHEMY_DATABASE_URI = os.environ.get('PROD_DATABASE_URL') or 'your_production_db_uri'
    # Add other production specific settings like logging, security headers etc.
