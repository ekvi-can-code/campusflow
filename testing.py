import pytest
from app import app, db
from models import User, Room, Booking
from werkzeug.security import generate_password_hash

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SECRET_KEY'] = 'test_secret_key'

    with app.app_context():
        db.create_all()
        user = User(login='test_student', password=generate_password_hash('123'), role='student',
                    display_name='Test Student')
        user2 = User(login='test_student2', password=generate_password_hash('123'), role='student',
                     display_name='Test Student 2')
        admin = User(login='test_admin', password=generate_password_hash('admin'), role='admin',
                     display_name='Test Admin')
        db.session.add_all([user, user2, admin])

        room = Room(name='T-101', building='T', floor=1, capacity=20, equipment='projector')
        db.session.add(room)
        db.session.commit()

    with app.test_client() as test_client:
        yield test_client

    with app.app_context():
        db.drop_all()


def login(client, login_val, password):
    return client.post('/login', data={'login': login_val, 'password': password}, follow_redirects=True)


def test_booking_conflict(client):
    login(client, 'test_student', '123')
    client.post('/book', data={'room_id': 1, 'date': '2026-11-17', 'start_time': '10:00', 'end_time': '11:00'})
    response = client.post('/book',
                           data={'room_id': 1, 'date': '2026-11-17', 'start_time': '10:30', 'end_time': '11:30'},
                           follow_redirects=True)
    assert 'Слот уже занят' in response.data.decode('utf-8')


def test_booking_touching_boundaries(client):
    login(client, 'test_student', '123')
    client.post('/book', data={'room_id': 1, 'date': '2026-11-17', 'start_time': '10:00', 'end_time': '11:00'})
    response = client.post('/book',
                           data={'room_id': 1, 'date': '2026-11-17', 'start_time': '11:00', 'end_time': '12:00'},
                           follow_redirects=True)
    assert 'Бронь создана' in response.data.decode('utf-8')


def test_cancel_own_booking(client):
    login(client, 'test_student', '123')
    client.post('/book', data={'room_id': 1, 'date': '2026-11-17', 'start_time': '14:00', 'end_time': '15:00'})
    booking = Booking.query.filter_by(user_id=1).first()
    response = client.post(f'/cancel/{booking.id}', follow_redirects=True)
    assert 'Бронь отменена' in response.data.decode('utf-8')
    assert db.session.get(Booking, booking.id).status == 'cancelled'


def test_cancel_other_booking_forbidden(client):
    login(client, 'test_student', '123')
    client.post('/book', data={'room_id': 1, 'date': '2026-11-17', 'start_time': '16:00', 'end_time': '17:00'})
    booking = Booking.query.filter_by(user_id=1).first()

    client.get('/logout')
    login(client, 'test_student2', '123')

    response = client.post(f'/cancel/{booking.id}', follow_redirects=True)
    assert 'Нет прав' in response.data.decode('utf-8')
    assert db.session.get(Booking, booking.id).status == 'active'