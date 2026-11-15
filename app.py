from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Room, Booking
from werkzeug.security import check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///campusflow.db'
app.config['SECRET_KEY'] = '678190'
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    rooms = Room.query.all()
    return render_template('index.html', rooms=rooms)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_val = request.form.get('login')
        password = request.form.get('password')
        user = User.query.filter_by(login=login_val).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/rooms')
def rooms():
    building = request.args.get('building')
    min_capacity = request.args.get('min_capacity', type=int)
    equipment_list = request.args.getlist('equipment_list')
    equipment = ','.join(equipment_list) if equipment_list else ''

    query = Room.query
    if building:
        query = query.filter_by(building=building)
    if min_capacity:
        query = query.filter(Room.capacity >= min_capacity)
    for eq in equipment_list:
        query = query.filter(Room.equipment.contains(eq))

    rooms_list = query.all()
    return render_template('rooms.html', rooms=rooms_list, building=building,
                           min_capacity=min_capacity, equipment=equipment)

@app.route('/room/<int:room_id>')
def room_detail(room_id):
    room = Room.query.get_or_404(room_id)
    date = request.args.get('date')
    from datetime import date as dt, timedelta
    if not date:
        date = (dt.today() + timedelta(days=1)).isoformat()

    bookings = Booking.query.filter_by(room_id=room_id, date=date, status='active').all()
    busy = []
    for b in bookings:
        busy.append({'start': b.start_time, 'end': b.end_time, 'user': b.user.display_name})

    slots = []
    hour = 8
    while hour < 20:
        start = f'{hour:02d}:00'
        end = f'{hour+1:02d}:00'
        is_busy = False
        for b in busy:
            if not (end <= b['start'] or start >= b['end']):
                is_busy = True
                break
        slots.append({'start': start, 'end': end, 'free': not is_busy})
        hour += 1

    return render_template('room_detail.html', room=room, date=date, slots=slots, busy=busy)

@app.route('/book', methods=['POST'])
@login_required
def book():
    if current_user.role == 'admin':
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'FORBIDDEN', 'message': 'Администраторы не могут создавать брони'}), 403
        flash('Администраторы не могут создавать брони')
        return redirect(
            url_for('room_detail', room_id=request.form.get('room_id', type=int), date=request.form.get('date')))

    room_id = request.form.get('room_id', type=int)
    date_val = request.form.get('date')
    start_time = request.form.get('start_time')
    end_time = request.form.get('end_time')

    if start_time >= end_time:
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'INVALID_TIME', 'message': 'Время начала должно быть раньше времени окончания'}), 400
        flash('Время начала должно быть раньше времени окончания')
        return redirect(url_for('room_detail', room_id=room_id, date=date_val))

    existing = Booking.query.filter_by(room_id=room_id, date=date_val, status='active').all()
    for b in existing:
        if not (end_time <= b.start_time or start_time >= b.end_time):
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': 'BOOKING_CONFLICT', 'message': 'Слот уже занят'}), 409
            flash('Слот уже занят')
            return redirect(url_for('room_detail', room_id=room_id, date=date_val))

    booking = Booking(
        room_id=room_id,
        user_id=current_user.id,
        date=date_val,
        start_time=start_time,
        end_time=end_time,
        status='active'
    )
    db.session.add(booking)
    db.session.commit()
    flash('Бронь создана')
    return redirect(url_for('my_bookings'))

@app.route('/my')
@login_required
def my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.date.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id and current_user.role != 'admin':
        flash('Нет прав')
        return redirect(url_for('my_bookings'))
    booking.status = 'cancelled'
    db.session.commit()
    flash('Бронь отменена')
    return redirect(url_for('my_bookings'))

@app.route('/admin')
@login_required
def admin():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))
    bookings = Booking.query.all()
    rooms = Room.query.all()
    return render_template('admin.html', bookings=bookings, rooms=rooms)

@app.route('/admin/stats')
@login_required
def admin_stats():
    if current_user.role != 'admin':
        flash('Доступ запрещен')
        return redirect(url_for('index'))

    from sqlalchemy import func
    by_building = db.session.query(
        Room.building, func.count(Booking.id)
    ).join(Booking).filter(Booking.status == 'active').group_by(Room.building).all()

    by_date = db.session.query(
        Booking.date, func.count(Booking.id)
    ).filter(Booking.status == 'active').group_by(Booking.date).order_by(Booking.date).all()

    total_rooms = Room.query.count()
    total_bookings = Booking.query.filter_by(status='active').count()

    return render_template('admin_stats.html',
                           by_building=by_building,
                           by_date=by_date,
                           total_rooms=total_rooms,
                           total_bookings=total_bookings)

@app.route('/admin/room', methods=['POST'])
@login_required
def admin_add_room():
    if current_user.role != 'admin':
        return '403', 403
    name = request.form.get('name')
    building = request.form.get('building')
    floor = request.form.get('floor', type=int)
    capacity = request.form.get('capacity', type=int)
    equipment = request.form.get('equipment', '')
    room = Room(name=name, building=building, floor=floor, capacity=capacity, equipment=equipment)
    db.session.add(room)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/room/<int:room_id>/delete', methods=['POST'])
@login_required
def admin_delete_room(room_id):
    if current_user.role != 'admin':
        return '403', 403
    room = Room.query.get_or_404(room_id)
    db.session.delete(room)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/api/rooms')
def api_rooms():
    building = request.args.get('building')
    min_capacity = request.args.get('min_capacity', type=int)
    equipment = request.args.get('equipment')
    query = Room.query
    if building:
        query = query.filter_by(building=building)
    if min_capacity:
        query = query.filter(Room.capacity >= min_capacity)
    if equipment:
        query = query.filter(Room.equipment.contains(equipment))
    rooms_list = query.all()
    return jsonify([{'id': r.id, 'name': r.name, 'building': r.building,
                     'floor': r.floor, 'capacity': r.capacity, 'equipment': r.equipment}
                    for r in rooms_list])

@app.route('/api/rooms/<int:room_id>/free-slots')
def api_free_slots(room_id):
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'date required'}), 400
    bookings = Booking.query.filter_by(room_id=room_id, date=date, status='active').all()
    busy = [{'start': b.start_time, 'end': b.end_time} for b in bookings]
    slots = []
    hour = 8
    while hour < 20:
        start = f'{hour:02d}:00'
        end = f'{hour+1:02d}:00'
        is_busy = False
        for b in busy:
            if not (end <= b['start'] or start >= b['end']):
                is_busy = True
                break
        if not is_busy:
            slots.append({'start': start, 'end': end})
        hour += 1
    return jsonify({'room_id': room_id, 'date': date, 'free_slots': slots})

@app.route('/api/bookings', methods=['POST'])
@login_required
def api_create_booking():
    if current_user.role == 'admin':
        return jsonify({'error': 'FORBIDDEN', 'message': 'Администраторы не могут создавать брони'}), 403

    data = request.get_json()
    room_id = data.get('room_id')
    date = data.get('date')
    start_time = data.get('start_time')
    end_time = data.get('end_time')

    existing = Booking.query.filter_by(room_id=room_id, date=date, status='active').all()
    for b in existing:
        if not (end_time <= b.start_time or start_time >= b.end_time):
            return jsonify({'error': 'BOOKING_CONFLICT', 'message': 'Слот уже занят'}), 409

    booking = Booking(room_id=room_id, user_id=current_user.id, date=date,
                      start_time=start_time, end_time=end_time, status='active')
    db.session.add(booking)
    db.session.commit()
    return jsonify({'id': booking.id, 'status': 'created'}), 201

@app.route('/api/bookings/my')
@login_required
def api_my_bookings():
    bookings = Booking.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'id': b.id, 'room_id': b.room_id, 'room': b.room.name,
                     'date': b.date, 'start': b.start_time, 'end': b.end_time,
                     'status': b.status} for b in bookings])

@app.route('/api/bookings/<int:booking_id>', methods=['DELETE'])
@login_required
def api_cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        return jsonify({'error': 'FORBIDDEN'}), 403
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'status': 'cancelled'}), 200

@app.route('/api/admin/bookings')
@login_required
def api_admin_bookings():
    if current_user.role != 'admin':
        return jsonify({'error': 'FORBIDDEN'}), 403
    bookings = Booking.query.all()
    return jsonify([{'id': b.id, 'room_id': b.room_id, 'user': b.user.display_name,
                     'date': b.date, 'start': b.start_time, 'end': b.end_time,
                     'status': b.status} for b in bookings])

@app.route('/api/admin/bookings/<int:booking_id>', methods=['DELETE'])
@login_required
def api_admin_cancel(booking_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'FORBIDDEN'}), 403
    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'status': 'cancelled'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)