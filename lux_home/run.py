from app import create_app
import os

# Use DevelopmentConfig by default, or allow overriding via environment variable
config_name = os.getenv('FLASK_CONFIG', 'config.DevelopmentConfig')
app = create_app(config_name)

if __name__ == '__main__':
    # Debug mode should be controlled by the config now
    app.run(debug=app.config.get('DEBUG', True))
