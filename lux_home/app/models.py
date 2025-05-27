from datetime import datetime
from app import db, bcrypt # Import bcrypt
from flask_login import UserMixin # Import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}')"

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(50), unique=True, nullable=False)
    room_type = db.Column(db.String(100), nullable=False)
    rate_per_night = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False, default='available')
    bookings = db.relationship('Booking', backref='room', lazy=True)

    def __repr__(self):
        return f"Room('{self.room_number}', '{self.room_type}', '{self.status}')"

class Guest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    bookings = db.relationship('Booking', backref='guest', lazy=True)

    def __repr__(self):
        return f"Guest('{self.name}', '{self.email}')"

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    check_in_date = db.Column(db.DateTime, nullable=False)
    check_out_date = db.Column(db.DateTime, nullable=True)
    total_amount = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    invoice = db.relationship('Invoice', backref=db.backref('booking', uselist=False), lazy=True)
    booking_services = db.relationship('BookingService', backref='booking', lazy=True)

    def __repr__(self):
        return f"Booking('{self.guest_id}', '{self.room_id}', '{self.check_in_date}')"

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False, unique=True)
    issue_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=True)
    amount_paid = db.Column(db.Float, nullable=False, default=0.0)
    payment_status = db.Column(db.String(50), nullable=False, default='pending')

    def __repr__(self):
        return f"Invoice('{self.booking_id}', '{self.issue_date}', '{self.payment_status}')"

class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    price = db.Column(db.Float, nullable=False)
    booking_services = db.relationship('BookingService', backref='service', lazy=True)

    def __repr__(self):
        return f"Service('{self.name}', '{self.price}')"

class BookingService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    def __repr__(self):
        return f"BookingService('{self.booking_id}', '{self.service_id}', '{self.quantity}')"
