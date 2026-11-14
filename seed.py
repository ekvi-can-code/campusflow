from app import app, db
from models import User, Room, Booking
from werkzeug.security import generate_password_hash


def seed():
    with app.app_context():
        db.create_all()

        if User.query.first():
            return

        users = [
            User(login='student1', password=generate_password_hash('123'), role='student', display_name='Иван Иванов'),
            User(login='student2', password=generate_password_hash('123'), role='student', display_name='Петр Петров'),
            User(login='admin', password=generate_password_hash('admin'), role='admin', display_name='Администратор'),
        ]
        db.session.add_all(users)
        db.session.commit()

        rooms = [
            Room(name='A-101', building='A', floor=1, capacity=20, equipment='projector,board'),
            Room(name='A-102', building='A', floor=1, capacity=15, equipment='board'),
            Room(name='A-201', building='A', floor=2, capacity=30, equipment='projector,computers'),
            Room(name='A-202', building='A', floor=2, capacity=25, equipment='projector'),
            Room(name='B-101', building='B', floor=1, capacity=40, equipment='projector,board,computers'),
            Room(name='B-102', building='B', floor=1, capacity=20, equipment='projector'),
            Room(name='B-201', building='B', floor=2, capacity=15, equipment='board'),
            Room(name='B-202', building='B', floor=2, capacity=30, equipment='projector,board'),
            Room(name='C-101', building='C', floor=1, capacity=50, equipment='projector,computers,board'),
            Room(name='C-102', building='C', floor=1, capacity=25, equipment='projector'),
        ]
        db.session.add_all(rooms)
        db.session.commit()

        from datetime import date, timedelta
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        bookings = [
            Booking(room_id=1, user_id=1, date=tomorrow, start_time='10:00', end_time='11:00', status='active'),
            Booking(room_id=2, user_id=2, date=tomorrow, start_time='12:00', end_time='13:00', status='active'),
            Booking(room_id=5, user_id=1, date=tomorrow, start_time='14:00', end_time='15:00', status='active'),
        ]
        db.session.add_all(bookings)
        db.session.commit()
        print('Seed done')


if __name__ == '__main__':
    seed()