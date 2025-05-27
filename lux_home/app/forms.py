from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Optional, Length, EqualTo, ValidationError
from app.models import User # To check for existing username

class NewGuestForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[Optional()])
    submit = SubmitField('Create Guest')

class CheckInForm(FlaskForm):
    guest_id = SelectField('Select Existing Guest', coerce=int, validators=[DataRequired()])
    new_guest_name = StringField('New Guest Name', validators=[Optional()])
    new_guest_email = StringField('New Guest Email', validators=[Optional(), Email(message="Valid email required if provided for new guest.")])
    new_guest_phone = StringField('New Guest Phone', validators=[Optional()])
    room_id = SelectField('Select Available Room', coerce=int, validators=[DataRequired()])
    check_in_date = DateField('Check-in Date', validators=[DataRequired()], format='%Y-%m-%d')
    check_out_date = DateField('Check-out Date', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Check-in')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')
