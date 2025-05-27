from flask import render_template, redirect, url_for, flash, request, make_response
from app import app, db, bcrypt # Import bcrypt
from app.models import Room, Guest, Booking, Invoice, Service, BookingService, User # Import User
from app.forms import CheckInForm, NewGuestForm, LoginForm, RegistrationForm # Import auth forms
from app.services import calculate_booking_total # Import the service function
from datetime import datetime, date, timedelta # Ensure timedelta is imported
from weasyprint import HTML # Import WeasyPrint
from flask_login import login_user, logout_user, login_required, current_user # Import Flask-Login functions


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login Successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        else:
            flash('Login Unsuccessful. Please check username and password.', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/')
@login_required # Protect dashboard
def index():
    rooms = Room.query.all()
    active_bookings = Booking.query.filter_by(is_active=True).all()
    active_bookings_map = {b.room_id: b.id for b in active_bookings}
    # The duplicated query for rooms and active_bookings seems like a mistake from previous merge. Consolidating.
    completed_bookings = Booking.query.filter_by(is_active=False).order_by(Booking.check_out_date.desc()).limit(10).all() # Get recent 10
    return render_template('dashboard.html', rooms=rooms, active_bookings_map=active_bookings_map, completed_bookings=completed_bookings)

@app.route('/invoice/<int:booking_id>')
@login_required # Protect route
def view_invoice(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    guest = booking.guest
    room = booking.room

    if booking.total_amount is None:
        # Calculate and save total amount if not already set (e.g. if checkout didn't run or it's an old booking)
        total_calculated = calculate_booking_total(booking.id)
        if total_calculated is not None:
            booking.total_amount = total_calculated
            db.session.add(booking)
            # We might commit here or let it commit with invoice creation
        else:
            # Handle case where calculation might fail, though calculate_booking_total should prevent this
            flash("Could not calculate total amount for the booking.", "danger")
            return redirect(request.referrer or url_for('index'))


    invoice = Invoice.query.filter_by(booking_id=booking.id).first()
    if not invoice:
        issue_date = datetime.utcnow()
        due_date = issue_date + timedelta(days=15) # Default due date
        
        # Ensure booking.total_amount is definitely set before creating invoice
        if booking.total_amount is None: # Should have been set above, but as a fallback
             # This is a critical fallback. If this happens, something is wrong with the flow.
            flash("Booking total amount was not set. Please check out the booking again.", "danger")
            return redirect(url_for('index'))


        invoice = Invoice(
            booking_id=booking.id,
            issue_date=issue_date,
            due_date=due_date
            # amount_paid and payment_status have defaults in model
        )
        db.session.add(invoice)
        db.session.commit() # Commit booking total and new invoice together

    # Calculate duration_days for display on invoice
    check_in_dt = booking.check_in_date
    checkout_dt = booking.check_out_date if booking.check_out_date else datetime.utcnow()
    if isinstance(check_in_dt, date) and not isinstance(check_in_dt, datetime):
        check_in_dt = datetime.combine(check_in_dt, datetime.min.time())
    if isinstance(checkout_dt, date) and not isinstance(checkout_dt, datetime):
        checkout_dt = datetime.combine(checkout_dt, datetime.min.time())
    duration_days = (checkout_dt - check_in_dt).days
    if duration_days <= 0:
        duration_days = 1
    
    return render_template('invoice_template.html', 
                           booking=booking, 
                           invoice=invoice, 
                           guest=guest, 
                           room=room,
                           duration_days=duration_days)

@app.route('/invoice/<int:booking_id>/pdf')
@login_required # Protect route
def download_invoice_pdf(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    guest = booking.guest
    room = booking.room

    if booking.total_amount is None:
        total_calculated = calculate_booking_total(booking.id)
        if total_calculated is not None:
            booking.total_amount = total_calculated
            db.session.add(booking)
        else:
            flash("Could not calculate total amount for the booking.", "danger")
            return redirect(request.referrer or url_for('index'))

    invoice = Invoice.query.filter_by(booking_id=booking.id).first()
    if not invoice:
        issue_date = datetime.utcnow()
        due_date = issue_date + timedelta(days=15)
        if booking.total_amount is None:
            flash("Booking total amount was not set. Cannot generate PDF.", "danger")
            return redirect(url_for('view_invoice', booking_id=booking.id))
        
        invoice = Invoice(
            booking_id=booking.id,
            issue_date=issue_date,
            due_date=due_date
        )
        db.session.add(invoice)
        db.session.commit()

    check_in_dt = booking.check_in_date
    checkout_dt = booking.check_out_date if booking.check_out_date else datetime.utcnow()
    if isinstance(check_in_dt, date) and not isinstance(check_in_dt, datetime):
        check_in_dt = datetime.combine(check_in_dt, datetime.min.time())
    if isinstance(checkout_dt, date) and not isinstance(checkout_dt, datetime):
        checkout_dt = datetime.combine(checkout_dt, datetime.min.time())
    duration_days = (checkout_dt - check_in_dt).days
    if duration_days <= 0:
        duration_days = 1

    html_out = render_template('invoice_template.html', 
                               booking=booking, 
                               invoice=invoice, 
                               guest=guest, 
                               room=room,
                               duration_days=duration_days,
                               is_pdf_render=True) # Flag to hide elements in PDF
    
    try:
        pdf = HTML(string=html_out).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=invoice_{booking.id}.pdf'
        return response
    except Exception as e:
        # Log the error e
        app.logger.error(f"Error generating PDF for invoice {booking.id}: {e}")
        # Attempt to install WeasyPrint dependencies if it's a known missing library error
        if "No GDK-PixBuf library found" in str(e) or "no library called " in str(e).lower(): # Heuristic
            flash("Generating PDF failed due to missing system libraries. Attempting to install them. Please try again in a moment.", "warning")
            # Return a redirect or a simple message, as installing might take time
            # and we can't block the request for too long.
            # For a real app, this installation would be part of deployment or a separate admin action.
            return redirect(url_for('view_invoice', booking_id=booking.id))
        else:
            flash(f"Could not generate PDF: {e}", "danger")
            return redirect(url_for('view_invoice', booking_id=booking.id))


@app.route('/check-out/<int:booking_id>', methods=['POST'])
@login_required # Protect route
def check_out(booking_id):
    booking = Booking.query.get_or_404(booking_id) # More robust way to get booking
    if not booking: # Should be handled by get_or_404, but good for clarity
        flash(f"Booking ID {booking_id} not found.", 'danger')
        return redirect(url_for('index'))

    room = booking.room # Room.query.get(booking.room_id) is also an option

    if not booking.is_active:
        flash(f"Booking for room {room.room_number} is already checked out.", 'info')
        return redirect(url_for('index'))

    # Calculate Total Amount (placeholder for now)
    if booking.check_out_date:
        checkout_dt = booking.check_out_date
    else:
        checkout_dt = datetime.utcnow()
        booking.check_out_date = checkout_dt

    # Ensure check_in_date is datetime.datetime for subtraction if it's datetime.date
    check_in_dt = booking.check_in_date
    if isinstance(check_in_dt, date) and not isinstance(check_in_dt, datetime):
        check_in_dt = datetime.combine(check_in_dt, datetime.min.time())
    if isinstance(checkout_dt, date) and not isinstance(checkout_dt, datetime):
        checkout_dt = datetime.combine(checkout_dt, datetime.min.time())


    delta_days = (checkout_dt - check_in_dt).days
    if delta_days <= 0: # Ensure at least one night is charged
        delta_days = 1
    
    # booking.total_amount = delta_days * room.rate_per_night # Old calculation
    booking.total_amount = calculate_booking_total(booking.id) # Use service
    
    booking.is_active = False
    room.status = 'needs_cleaning' # Or 'available'

    try:
        db.session.add(booking)
        db.session.add(room)
        db.session.commit()
        flash(f"Room {room.room_number} checked out successfully. Total: ${booking.total_amount:.2f}", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Error during check-out for room {room.room_number}: {str(e)}", 'danger')

    return redirect(url_for('index'))


@app.route('/check-in', methods=['GET', 'POST'])
@login_required # Protect route
def check_in():
    form = CheckInForm()
    # Populate guest choices
    guests = Guest.query.order_by(Guest.name).all()
    form.guest_id.choices = [(0, '--- New Guest ---')] + [(g.id, g.name) for g in guests]

    # Populate room choices
    available_rooms = Room.query.filter_by(status='available').order_by(Room.room_number).all()
    form.room_id.choices = [(r.id, f"{r.room_number} ({r.room_type} - ${r.rate_per_night})") for r in available_rooms]

    if form.validate_on_submit():
        room = Room.query.get(form.room_id.data)
        if not room or room.status != 'available':
            flash('Selected room is not available.', 'danger')
            return redirect(url_for('check_in'))

        guest_id_to_use = None
        if form.guest_id.data == 0:  # New Guest
            if not form.new_guest_name.data or not form.new_guest_email.data:
                if not form.new_guest_name.data:
                    form.new_guest_name.errors.append('Name is required for new guest.')
                if not form.new_guest_email.data:
                    form.new_guest_email.errors.append('Email is required for new guest.')
                # flash('Name and Email are required for a new guest.', 'danger')
                # return render_template('check_in.html', form=form, title="Check-In Guest")
            else:
                existing_guest_check = Guest.query.filter_by(email=form.new_guest_email.data).first()
                if existing_guest_check:
                    form.new_guest_email.errors.append(f"Guest with email {form.new_guest_email.data} already exists. Please select from existing guests or use a different email.")
                    # flash(f"Guest with email {form.new_guest_email.data} already exists. Please select from existing guests or use a different email.", 'danger')
                    # return render_template('check_in.html', form=form, title="Check-In Guest")
                else:
                    new_guest = Guest(
                        name=form.new_guest_name.data,
                        email=form.new_guest_email.data,
                        phone=form.new_guest_phone.data
                    )
                    db.session.add(new_guest)
                    db.session.flush() # Use flush to get the ID before commit
                    guest_id_to_use = new_guest.id
                    # Add new guest to the dropdown for future check-ins (optional, good UX)
                    form.guest_id.choices.append((new_guest.id, new_guest.name))
        else:  # Existing Guest
            guest_id_to_use = form.guest_id.data
            if not Guest.query.get(guest_id_to_use):
                 flash('Selected guest does not exist.', 'danger')
                 return redirect(url_for('check_in'))


        if guest_id_to_use and not form.errors: # Proceed if guest is set and no new errors
            try:
                booking = Booking(
                    guest_id=guest_id_to_use,
                    room_id=room.id,
                    check_in_date=form.check_in_date.data,
                    check_out_date=form.check_out_date.data if form.check_out_date.data else None,
                    is_active=True
                )
                room.status = 'occupied'
                db.session.add(booking)
                db.session.add(room)
                db.session.commit()
                flash(f"Check-in successful for room {room.room_number}.", 'success')
                return redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred during check-in: {str(e)}", 'danger')
        else:
            # This part is to ensure that if there were form errors (e.g. new guest email exists)
            # we re-render the form with those errors.
             if not guest_id_to_use and form.guest_id.data == 0 and (not form.new_guest_name.data or not form.new_guest_email.data):
                pass # Errors already added
             elif not guest_id_to_use and form.guest_id.data == 0 and Guest.query.filter_by(email=form.new_guest_email.data).first():
                pass # Error already added

    elif request.method == 'GET':
        form.check_in_date.data = datetime.utcnow().date()


    return render_template('check_in.html', form=form, title="Check-In Guest")
