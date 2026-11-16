# CampusFlow 

ENG: Website for booking audiences and looking for free time slots.

RUS: Сервис бронирования аудиторий и поиска свободных слотов.

## Features / Возможности

ENG:
- View all rooms with filters
- See free time slots for any date, book a slot if available
- Own bookings management (create, cancel)
- Admin panel with stats and CSV slots export
- REST API + simple web UI

RUS:
- Просмотр всех аудиторий с фильтрацией
- Просмотр свободных окон для бронирования в любую дату, бронирование по возможности
- Редактирование своих бронирований (создание, отмена)
- Админ-панель со статистикой и экспортом CSV таблицы броней
- REST API + простой веб-интерфейс

## Installation and launch / Установка и запуск

ENG: Use *seed.py* for making template data in database (for testing)

RUS: Используйте *seed.py* для создания данных-заглушек в базе данных (для тестирования)
```bash
git clone https://github.com/ekvi-can-code/campusflow
cd campusflow
pip install -r requirements.txt
python seed.py
python app.py
```

#### Template data from *seed.py*: / Данные из *seed.py*:
| LOGIN | PASSWORD |
| --- | --- |
| `student1` | `123` |
| `student2` | `123` |
| `admin` | `admin` |

## Testing via PyTest / Тестирование через PyTest
```bash
pytest testing.py -v
```

## Requirements / Требования
- Python 3.10+