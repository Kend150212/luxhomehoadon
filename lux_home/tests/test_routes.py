import pytest
from flask import url_for
from app.models import User, Room, Guest, Booking, Invoice
from app import db as _db # Use the db instance from app

# Helper function to register a user
def register_user(client, username, password):
    return client.post(url_for('register'), data=dict(
        username=username,
        password=password,
        confirm_password=password
    ), follow_redirects=True)

# Helper function to login a user
def login_user(client, username, password):
    return client.post(url_for('login'), data=dict(
        username=username,
        password=password,
        remember=False
    ), follow_redirects=True)

# Helper function to logout a user
def logout_user(client):
    return client.get(url_for('logout'), follow_redirects=True)

# --- Authentication Flow Tests ---

def test_registration_page_loads(test_client):
    response = test_client.get(url_for('register'))
    assert response.status_code == 200
    assert b"Join Today" in response.data

def test_successful_registration(test_client, db_instance):
    response = register_user(test_client, 'newuser', 'password123')
    assert response.status_code == 200 # Should redirect to login
    assert b"Your account has been created!" in response.data
    assert b"Login" in response.data # On the login page
    user = User.query.filter_by(username='newuser').first()
    assert user is not None
    assert user.check_password('password123')

def test_registration_existing_username(test_client, db_instance):
    # First, register a user
    register_user(test_client, 'existinguser', 'password123')
    # Attempt to register again with the same username
    response = register_user(test_client, 'existinguser', 'password456')
    assert response.status_code == 200 # Stays on registration page
    assert b"That username is taken." in response.data
    # Check that only one user 'existinguser' exists and has the original password
    users = User.query.filter_by(username='existinguser').all()
    assert len(users) == 1
    assert users[0].check_password('password123')

def test_login_page_loads(test_client):
    response = test_client.get(url_for('login'))
    assert response.status_code == 200
    assert b"Log In" in response.data

def test_successful_login_logout(test_client, db_instance):
    # Register user first
    register_user(test_client, 'loginuser', 'password123')
    
    # Login
    response = login_user(test_client, 'loginuser', 'password123')
    assert response.status_code == 200 # Redirects to index
    assert b"Login Successful!" in response.data
    assert b"Dashboard" in response.data # On the dashboard
    assert b"Logout (loginuser)" in response.data # Logout link visible

    # Logout
    response = logout_user(test_client)
    assert response.status_code == 200 # Redirects to login
    assert b"You have been logged out." in response.data
    assert b"Login" in response.data # On the login page

def test_login_incorrect_credentials(test_client, db_instance):
    register_user(test_client, 'correctuser', 'correctpass')
    
    # Try logging in with wrong password
    response = login_user(test_client, 'correctuser', 'wrongpass')
    assert response.status_code == 200 # Stays on login page
    assert b"Login Unsuccessful." in response.data
    assert b"Logout (correctuser)" not in response.data

    # Try logging in with non-existent user
    response = login_user(test_client, 'nonexistentuser', 'anypass')
    assert response.status_code == 200 # Stays on login page
    assert b"Login Unsuccessful." in response.data

def test_access_protected_route_unauthenticated(test_client):
    # Try accessing dashboard without logging in
    response = test_client.get(url_for('index'), follow_redirects=False) # Don't follow to see redirect
    assert response.status_code == 302 # Should redirect
    assert url_for('login') in response.location # Redirects to login

    response = test_client.get(url_for('index'), follow_redirects=True) # Follow redirect
    assert response.status_code == 200
    assert b"Please log in to access this page." in response.data # Flash message
    assert b"Log In" in response.data # On login page

def test_access_protected_route_authenticated(test_client, db_instance):
    register_user(test_client, 'authtestuser', 'password123')
    login_user(test_client, 'authtestuser', 'password123')

    response = test_client.get(url_for('index'))
    assert response.status_code == 200
    assert b"Dashboard" in response.data # Successfully on dashboard
    assert b"Logout (authtestuser)" in response.data
    assert b"Please log in to access this page." not in response.data
    assert b"Log In" not in response.data # Not on login page


# --- Check-in Flow Tests ---

def test_check_in_page_loads_authenticated(test_client, db_instance):
    register_user(test_client, 'checkinuser', 'password123')
    login_user(test_client, 'checkinuser', 'password123')

    # Create an available room
    room1 = Room(room_number='T101', room_type='Test Standard', rate_per_night=50.0)
    db_instance.session.add(room1)
    db_instance.session.commit()

    response = test_client.get(url_for('check_in'))
    assert response.status_code == 200
    assert b"Check-In Guest" in response.data
    assert b"T101 (Test Standard - $50.0)" in response.data # Check if room is in choices

def test_check_in_new_guest_successful(test_client, db_instance):
    register_user(test_client, 'checkinop', 'password123')
    login_user(test_client, 'checkinop', 'password123')

    room = Room(room_number='T102', room_type='Test Deluxe', rate_per_night=120.0)
    db_instance.session.add(room)
    db_instance.session.commit()

    check_in_data = {
        'guest_id': '0', # --- New Guest ---
        'new_guest_name': 'New Test Guest',
        'new_guest_email': 'new.guest@example.com',
        'new_guest_phone': '1234567890',
        'room_id': room.id,
        'check_in_date': '2024-01-10', # Assuming a fixed date for testability
        'check_out_date': '2024-01-12'
    }
    response = test_client.post(url_for('check_in'), data=check_in_data, follow_redirects=True)
    
    assert response.status_code == 200
    assert b"Dashboard" in response.data # Redirected to dashboard
    assert f"Check-in successful for room {room.room_number}.".encode('utf-8') in response.data # Flash message

    guest = Guest.query.filter_by(email='new.guest@example.com').first()
    assert guest is not None
    assert guest.name == 'New Test Guest'

    booking = Booking.query.filter_by(guest_id=guest.id, room_id=room.id).first()
    assert booking is not None
    assert booking.is_active is True
    # assert booking.check_in_date.strftime('%Y-%m-%d') == '2024-01-10' # Date conversion can be tricky

    updated_room = Room.query.get(room.id)
    assert updated_room.status == 'occupied'

def test_check_in_existing_guest_successful(test_client, db_instance):
    register_user(test_client, 'checkinexisting', 'password123')
    login_user(test_client, 'checkinexisting', 'password123')

    existing_guest = Guest(name='Existing Guest', email='existing.guest@example.com')
    room = Room(room_number='T103', room_type='Test Suite', rate_per_night=200.0)
    db_instance.session.add_all([existing_guest, room])
    db_instance.session.commit()

    check_in_data = {
        'guest_id': existing_guest.id,
        'room_id': room.id,
        'check_in_date': '2024-01-11',
        'check_out_date': '' # Optional
    }
    response = test_client.post(url_for('check_in'), data=check_in_data, follow_redirects=True)

    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert f"Check-in successful for room {room.room_number}.".encode('utf-8') in response.data

    # Verify no new guest was created with the existing guest's email
    guest_count = Guest.query.filter_by(email='existing.guest@example.com').count()
    assert guest_count == 1
    
    booking = Booking.query.filter_by(guest_id=existing_guest.id, room_id=room.id).first()
    assert booking is not None
    assert booking.is_active is True

    updated_room = Room.query.get(room.id)
    assert updated_room.status == 'occupied'

def test_check_in_invalid_data_new_guest_missing_name(test_client, db_instance):
    register_user(test_client, 'checkininvalid', 'password123')
    login_user(test_client, 'checkininvalid', 'password123')

    room = Room(room_number='T104', room_type='Test Invalid', rate_per_night=100.0)
    db_instance.session.add(room)
    db_instance.session.commit()

    initial_booking_count = Booking.query.count()
    initial_guest_count = Guest.query.count()

    check_in_data = {
        'guest_id': '0', # New Guest
        'new_guest_name': '', # Missing name
        'new_guest_email': 'invalid.guest@example.com',
        'room_id': room.id,
        'check_in_date': '2024-01-12'
    }
    response = test_client.post(url_for('check_in'), data=check_in_data, follow_redirects=True)
    
    assert response.status_code == 200 # Stays on check-in page
    assert b"Check-In Guest" in response.data # Still on check-in page
    assert b"Name is required for new guest." in response.data # Form error
    
    assert Booking.query.count() == initial_booking_count # No new booking
    assert Guest.query.count() == initial_guest_count # No new guest
    updated_room = Room.query.get(room.id)
    assert updated_room.status == 'available' # Room status unchanged


def test_check_in_room_not_available(test_client, db_instance):
    register_user(test_client, 'checkinnotavail', 'password123')
    login_user(test_client, 'checkinnotavail', 'password123')

    room = Room(room_number='T105', room_type='Test Occupied', rate_per_night=100.0, status='occupied')
    db_instance.session.add(room)
    db_instance.session.commit()
    
    initial_booking_count = Booking.query.count()

    check_in_data = {
        'guest_id': '0', 
        'new_guest_name': 'Any Guest',
        'new_guest_email': 'any.guest@example.com',
        'room_id': room.id,
        'check_in_date': '2024-01-13'
    }
    response = test_client.post(url_for('check_in'), data=check_in_data, follow_redirects=True)

    assert response.status_code == 200 # Stays on check-in page or redirects to it
    assert b"Selected room is not available." in response.data # Flash message
    assert Booking.query.count() == initial_booking_count # No new booking


# --- Check-out Flow Tests ---

def test_check_out_successful(test_client, db_instance):
    # Setup: Register user, create room, guest, and an active booking
    register_user(test_client, 'checkoutuser', 'password123')
    login_user(test_client, 'checkoutuser', 'password123')

    guest = Guest(name='Checkout Guest', email='checkout.guest@example.com')
    room = Room(room_number='T201', room_type='Checkout Standard', rate_per_night=75.0, status='occupied')
    db_instance.session.add_all([guest, room])
    db_instance.session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=datetime.utcnow() - timedelta(days=3), # Checked in 3 days ago
        is_active=True
    )
    db_instance.session.add(booking)
    db_instance.session.commit()

    initial_room_status = room.status

    # Perform check-out
    response = test_client.post(url_for('check_out', booking_id=booking.id), follow_redirects=True)

    assert response.status_code == 200
    assert b"Dashboard" in response.data # Redirected to dashboard
    
    # Check flash message for success and total amount
    # Total amount should be 3 days * $75 = $225
    expected_total_amount = 3 * 75.0
    assert f"Room {room.room_number} checked out successfully. Total: ${expected_total_amount:.2f}".encode('utf-8') in response.data

    # Verify booking status
    updated_booking = Booking.query.get(booking.id)
    assert updated_booking.is_active is False
    assert updated_booking.total_amount == expected_total_amount
    assert updated_booking.check_out_date is not None
    # Check if check_out_date is recent (within a few seconds of now)
    assert abs((datetime.utcnow() - updated_booking.check_out_date).total_seconds()) < 5 

    # Verify room status
    updated_room = Room.query.get(room.id)
    assert updated_room.status == 'needs_cleaning' # Or 'available' depending on config

def test_check_out_already_inactive_booking(test_client, db_instance):
    register_user(test_client, 'checkoutinactive', 'password123')
    login_user(test_client, 'checkoutinactive', 'password123')

    guest = Guest(name='Inactive Guest', email='inactive.guest@example.com')
    room = Room(room_number='T202', room_type='Inactive Room', rate_per_night=100.0, status='available') # Room might be available again
    db_instance.session.add_all([guest, room])
    db_instance.session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=datetime.utcnow() - timedelta(days=5),
        check_out_date=datetime.utcnow() - timedelta(days=2), # Already checked out
        total_amount=300.00,
        is_active=False
    )
    db_instance.session.add(booking)
    db_instance.session.commit()

    # Attempt to check-out the already inactive booking
    response = test_client.post(url_for('check_out', booking_id=booking.id), follow_redirects=True)

    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert f"Booking for room {room.room_number} is already checked out.".encode('utf-8') in response.data # Flash message

    # Ensure no changes occurred to booking or room
    final_booking = Booking.query.get(booking.id)
    assert final_booking.is_active is False
    assert final_booking.total_amount == 300.00 # Remains unchanged
    
    final_room = Room.query.get(room.id)
    assert final_room.status == 'available' # Remains unchanged (or whatever it was)


# --- Invoice Viewing and PDF Download Flow Tests ---

def test_view_invoice_html(test_client, db_instance):
    # Setup: User, completed booking, and invoice
    register_user(test_client, 'invoiceuser', 'password123')
    login_user(test_client, 'invoiceuser', 'password123')

    guest = Guest(name='Invoice View Guest', email='invoice.view@example.com')
    room = Room(room_number='T301', room_type='Invoice Suite', rate_per_night=300.0)
    db_instance.session.add_all([guest, room])
    db_instance.session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=datetime.utcnow() - timedelta(days=2),
        check_out_date=datetime.utcnow(),
        total_amount=600.00, # 2 nights * 300
        is_active=False
    )
    db_instance.session.add(booking)
    db_instance.session.commit()
    
    invoice = Invoice(booking_id=booking.id, issue_date=datetime.utcnow())
    db_instance.session.add(invoice)
    db_instance.session.commit()

    # Test GET /invoice/<booking_id>
    response = test_client.get(url_for('view_invoice', booking_id=booking.id))
    assert response.status_code == 200
    assert b"INVOICE" in response.data # General check for invoice page
    assert guest.name.encode('utf-8') in response.data
    assert room.room_number.encode('utf-8') in response.data
    assert ("%.2f" % booking.total_amount).encode('utf-8') in response.data
    assert b"Download PDF" in response.data # Check for PDF download button

def test_download_invoice_pdf(test_client, db_instance):
    # Setup: User, completed booking, and invoice (similar to above)
    register_user(test_client, 'pdfuser', 'password123')
    login_user(test_client, 'pdfuser', 'password123')

    guest = Guest(name='PDF Guest', email='pdf.guest@example.com')
    room = Room(room_number='T302', room_type='PDF Deluxe', rate_per_night=180.0)
    db_instance.session.add_all([guest, room])
    db_instance.session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=datetime.utcnow() - timedelta(days=1),
        check_out_date=datetime.utcnow(),
        total_amount=180.00, # 1 night * 180
        is_active=False
    )
    db_instance.session.add(booking)
    db_instance.session.commit()

    invoice = Invoice(booking_id=booking.id, issue_date=datetime.utcnow())
    db_instance.session.add(invoice)
    db_instance.session.commit()

    # Test GET /invoice/<booking_id>/pdf
    response = test_client.get(url_for('download_invoice_pdf', booking_id=booking.id))
    
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/pdf'
    assert 'inline; filename=invoice_' in response.headers['Content-Disposition']
    assert f'invoice_{booking.id}.pdf' in response.headers['Content-Disposition']
    
    # Check if PDF content is not empty or very small (basic check)
    assert len(response.data) > 1000 # Arbitrary small size check for PDF, WeasyPrint PDFs are usually larger

def test_view_invoice_auto_creates_invoice_if_missing(test_client, db_instance):
    # Setup: User, completed booking, but NO invoice yet
    register_user(test_client, 'autoinvoiceuser', 'password123')
    login_user(test_client, 'autoinvoiceuser', 'password123')

    guest = Guest(name='Auto Invoice Guest', email='autoinvoice.guest@example.com')
    room = Room(room_number='T303', room_type='Auto Suite', rate_per_night=250.0)
    db_instance.session.add_all([guest, room])
    db_instance.session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=datetime.utcnow() - timedelta(days=1),
        check_out_date=datetime.utcnow(),
        total_amount=250.00, 
        is_active=False
    )
    db_instance.session.add(booking)
    db_instance.session.commit()

    # Ensure no invoice exists yet
    assert Invoice.query.filter_by(booking_id=booking.id).first() is None
    
    response = test_client.get(url_for('view_invoice', booking_id=booking.id))
    assert response.status_code == 200
    
    # Check if invoice was created
    created_invoice = Invoice.query.filter_by(booking_id=booking.id).first()
    assert created_invoice is not None
    assert created_invoice.booking_id == booking.id
    
    assert b"INVOICE" in response.data
    assert ("#%d" % created_invoice.id).encode('utf-8') in response.data # Check if new invoice ID is on page
    assert ("%.2f" % booking.total_amount).encode('utf-8') in response.data

def test_view_invoice_calculates_total_if_missing(test_client, db_instance):
    # Setup: User, completed booking (is_active=False), NO total_amount, NO invoice
    register_user(test_client, 'calcuser', 'password123')
    login_user(test_client, 'calcuser', 'password123')

    guest = Guest(name='Calc Guest', email='calc.guest@example.com')
    room = Room(room_number='T304', room_type='Calc Standard', rate_per_night=100.0)
    db_instance.session.add_all([guest, room])
    db_instance.session.commit()

    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=datetime.utcnow() - timedelta(days=2), # 2 days
        check_out_date=datetime.utcnow(), 
        total_amount=None, # Total amount is not set
        is_active=False # Booking is completed
    )
    db_instance.session.add(booking)
    db_instance.session.commit()

    response = test_client.get(url_for('view_invoice', booking_id=booking.id))
    assert response.status_code == 200

    updated_booking = Booking.query.get(booking.id)
    assert updated_booking.total_amount == 200.00 # 2 days * 100.00
    
    assert b"INVOICE" in response.data
    assert b"200.00" in response.data # Check if calculated total is on page
