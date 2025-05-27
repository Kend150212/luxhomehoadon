from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
import os

# Initialize extensions without app context
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'
migrate = Migrate() # Initialize migrate without app and db here

def create_app(config_class_name='config.DevelopmentConfig'):
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class_name) # Load config from object

    # Initialize extensions with app context
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db) # Initialize migrate here

    # Import routes and models
    # It's crucial that models are imported after db is initialized with app
    # and routes are imported after app is created and configured.
    with app.app_context():
        from . import routes  # Import routes
        from . import models  # Import models (ensure they are defined to use 'db')

        # User loader callback for Flask-Login
        @login_manager.user_loader
        def load_user(user_id):
            return models.User.query.get(int(user_id))

    return app
