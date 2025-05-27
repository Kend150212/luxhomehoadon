from datetime import datetime, date, timedelta
from app.models import Booking, Room # Assuming models are in app.models
from app import db # For potential db operations, if needed

def calculate_booking_total(booking_id):
    """
    Calculates the total amount for a booking.
    If booking.total_amount is already set and non-zero, it returns that.
    Otherwise, it calculates based on room rate and duration.
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return None  # Or raise an error

    # If total_amount is already calculated and stored (e.g., during check-out)
    if booking.total_amount is not None and booking.total_amount > 0:
        return booking.total_amount

    room = booking.room
    if not room:
        return None  # Or raise an error

    check_in_dt = booking.check_in_date
    checkout_dt = booking.check_out_date if booking.check_out_date else datetime.utcnow()

    # Convert date objects to datetime objects for consistent subtraction
    if isinstance(check_in_dt, date) and not isinstance(check_in_dt, datetime):
        check_in_dt = datetime.combine(check_in_dt, datetime.min.time())
    if isinstance(checkout_dt, date) and not isinstance(checkout_dt, datetime):
        checkout_dt = datetime.combine(checkout_dt, datetime.min.time())

    duration_days = (checkout_dt - check_in_dt).days
    if duration_days <= 0:
        duration_days = 1
    
    room_charge = duration_days * room.rate_per_night
    
    # Placeholder for service charges (to be expanded later)
    total_services_charge = 0.0 
    # Example:
    # for bs in booking.booking_services:
    #     total_services_charge += bs.service.price * bs.quantity
    
    total_amount = room_charge + total_services_charge
    
    # The problem description implies the calling route (check-out or invoice generation)
    # will be responsible for saving this to booking.total_amount.
    # If we want this function to always save it, uncomment below:
    # booking.total_amount = total_amount
    # db.session.add(booking)
    # db.session.commit()

    return total_amount
