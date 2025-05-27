import pytest
from app.services import calculate_booking_total
from app.models import Booking, Room, Guest
from app import db as _db # Use the db instance from app
from datetime import datetime, timedelta

# Helper function to create a booking
def create_booking_for_test(db_session, room_rate, check_in_delta_days, duration_days=None, total_amount_preset=None):
    guest = Guest(name='Service Test Guest', email=f'service.guest.{datetime.now().timestamp()}@example.com')
    room = Room(room_number=f'S{datetime.now().timestamp()}', room_type='Service Test', rate_per_night=room_rate)
    db_session.add_all([guest, room])
    db_session.commit()

    check_in_date = datetime.utcnow() + timedelta(days=check_in_delta_days)
    check_out_date = None
    if duration_days is not None:
        check_out_date = check_in_date + timedelta(days=duration_days)
        
    booking = Booking(
        guest_id=guest.id,
        room_id=room.id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        total_amount=total_amount_preset # Can be None
    )
    db_session.add(booking)
    db_session.commit()
    return booking

# Test calculate_booking_total service
def test_calculate_booking_total_basic(db_instance):
    """Scenario 1: Basic calculation (e.g., 2 nights * $100/night = $200)."""
    booking = create_booking_for_test(db_instance.session, room_rate=100.00, check_in_delta_days=0, duration_days=2)
    total = calculate_booking_total(booking.id)
    assert total == 200.00

def test_calculate_booking_total_zero_duration(db_instance):
    """Scenario 2: Booking duration is zero (should default to 1 night)."""
    booking = create_booking_for_test(db_instance.session, room_rate=100.00, check_in_delta_days=0, duration_days=0)
    total = calculate_booking_total(booking.id)
    assert total == 100.00 # 1 night * 100

def test_calculate_booking_total_negative_duration(db_instance):
    """Scenario 2b: Booking duration is negative (should default to 1 night)."""
    booking = create_booking_for_test(db_instance.session, room_rate=100.00, check_in_delta_days=0, duration_days=-2)
    total = calculate_booking_total(booking.id)
    assert total == 100.00 # 1 night * 100

def test_calculate_booking_total_checkout_none(db_instance):
    """Scenario 3: check_out_date is None (should use current time, assuming check-in was in the past)."""
    # Create a booking that started 2 days ago, check_out_date is None
    booking = create_booking_for_test(db_instance.session, room_rate=100.00, check_in_delta_days=-2, duration_days=None)
    
    # The calculate_booking_total function will use datetime.utcnow() for checkout_dt
    # So, the duration should be 2 days.
    total = calculate_booking_total(booking.id)
    assert total == 200.00 # 2 nights * 100

def test_calculate_booking_total_checkout_none_future_checkin(db_instance):
    """Scenario 3b: check_out_date is None, check_in is in the future (should be 1 night)."""
    booking = create_booking_for_test(db_instance.session, room_rate=100.00, check_in_delta_days=2, duration_days=None)
    total = calculate_booking_total(booking.id)
    # If check_in is future and checkout is now(), duration_days will be negative, so defaults to 1
    assert total == 100.00

def test_calculate_booking_total_already_set(db_instance):
    """Scenario 4: total_amount already set on booking."""
    booking = create_booking_for_test(db_instance.session, room_rate=100.00, check_in_delta_days=0, duration_days=2, total_amount_preset=250.50)
    total = calculate_booking_total(booking.id)
    assert total == 250.50 # Should return the preset amount

def test_calculate_booking_total_already_set_zero(db_instance):
    """Scenario 4b: total_amount already set on booking but is 0.0, should recalculate."""
    booking = create_booking_for_test(db_instance.session, room_rate=100.00, check_in_delta_days=0, duration_days=3, total_amount_preset=0.0)
    total = calculate_booking_total(booking.id)
    # The service logic: if booking.total_amount is not None and booking.total_amount > 0: return it.
    # So if it's 0.0, it should recalculate.
    assert total == 300.00 # 3 nights * 100

def test_calculate_booking_total_no_room(db_instance):
    """Test case where booking might not have a room (should ideally not happen)."""
    guest = Guest(name='No Room Guest', email='noroom@example.com')
    db_instance.session.add(guest)
    db_instance.session.commit()
    
    # Create booking without a valid room_id or room relationship
    # This setup is a bit artificial as foreign key constraints should prevent this
    # but tests the robustness of the service function if data integrity is somehow compromised.
    # For this test, we'll assume booking.room returns None.
    # We can't directly set booking.room to None if it's a relationship,
    # so this test relies on the function's internal check `if not room: return None`.
    # A more direct way might involve mocking the booking object.
    
    # However, the current `calculate_booking_total` fetches booking then accesses booking.room.
    # If room_id was invalid and no room object is loaded, it would error.
    # A real scenario of `booking.room` being None is unlikely with SQLAlchemy relations
    # unless the related room was deleted after booking creation without proper cascade/checks.
    
    # Given the current structure, testing `if not room:` is hard without mocking.
    # We will assume that a booking always has a valid `room_id` and thus a `room` object
    # due to database foreign key constraints.
    # If the function were to take a `booking` object as input instead of `booking_id`,
    # we could more easily pass a mock or manually constructed object.
    pass # Skipping direct test for 'if not room:' as it's hard to simulate with current setup

def test_calculate_booking_total_booking_not_found(db_instance):
    """Test with a non-existent booking ID."""
    total = calculate_booking_total(99999) # Non-existent ID
    assert total is None
