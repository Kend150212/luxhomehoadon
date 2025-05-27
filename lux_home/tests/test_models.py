import pytest
from app.models import User, Room, Guest, Booking, Invoice
from app import db as _db # Use the db instance from app, not the fixture directly for model definitions
from datetime import datetime, timedelta

# Test User Model
def test_user_password_hashing(db_instance):
    user = User(username='testuser')
    user.set_password('password123')
    assert user.password_hash is not None
    assert user.password_hash != 'password123'
    assert user.check_password('password123')
    assert not user.check_password('wrongpassword')

def test_user_username_uniqueness(db_instance):
    user1 = User(username='uniqueuser')
    user1.set_password('password')
    db_instance.session.add(user1)
    db_instance.session.commit()

    user2 = User(username='uniqueuser')
    user2.set_password('password')
    db_instance.session.add(user2)
    with pytest.raises(Exception): # Expect an IntegrityError or similar from SQLAlchemy
        db_instance.session.commit()
    db_instance.session.rollback() # Rollback to clean state for next test

# Test Room Model
def test_room_creation(db_instance):
    room = Room(room_number='101', room_type='Standard', rate_per_night=100.00)
    db_instance.session.add(room)
    db_instance.session.commit()
    assert room.id is not None
    assert room.status == 'available' # Default status

# Test Guest Model
def test_guest_email_uniqueness(db_instance):
    guest1 = Guest(name='John Doe', email='john.doe@example.com')
    db_instance.session.add(guest1)
    db_instance.session.commit()

    guest2 = Guest(name='Jane Doe', email='john.doe@example.com')
    db_instance.session.add(guest2)
    with pytest.raises(Exception):
        db_instance.session.commit()
    db_instance.session.rollback()

# Test Booking Model
def test_booking_creation_and_relationships(db_instance):
    guest = Guest(name='Test Guest', email='guest@example.com')
    room = Room(room_number='102', room_type='Deluxe', rate_per_night=150.00)
    db_instance.session.add_all([guest, room])
    db_instance.session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=datetime.utcnow()
    )
    db_instance.session.add(booking)
    db_instance.session.commit()

    assert booking.id is not None
    assert booking.is_active is True # Default status
    assert booking.guest == guest
    assert booking.room == room

# Test Invoice Model
def test_invoice_creation_and_relationships(db_instance):
    guest = Guest(name='Invoice Guest', email='invoice.guest@example.com')
    room = Room(room_number='103', room_type='Suite', rate_per_night=250.00)
    db_instance.session.add_all([guest, room])
    db_instance.session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=datetime.utcnow(),
        check_out_date=datetime.utcnow() + timedelta(days=2),
        total_amount=500.00
    )
    db_instance.session.add(booking)
    db_instance.session.commit()

    invoice = Invoice(booking_id=booking.id)
    db_instance.session.add(invoice)
    db_instance.session.commit()

    assert invoice.id is not None
    assert invoice.payment_status == 'pending' # Default status
    assert invoice.issue_date is not None
    assert abs((datetime.utcnow() - invoice.issue_date).total_seconds()) < 5 # Check if issue_date is recent
    assert invoice.booking == booking

    # Test one-to-one relationship (Invoice with unique booking_id)
    invoice2 = Invoice(booking_id=booking.id)
    db_instance.session.add(invoice2)
    with pytest.raises(Exception):
        db_instance.session.commit()
    db_instance.session.rollback()
