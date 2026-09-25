## Backend
создал папку altyn и внутри создал папку backend
Внутри altyn создал файлы:
.env
.gitignore
Внутри backend создал venv:
python -m venv venv
активируем venv:
venv\Scripts\activate
Внутри backend установим зависимости:pip install django djangorestframework django-cors-headers django-filter psycopg2 pillow djangorestframework-simplejwt PyJWT gunicorn python-decouple
Внутри backend создаем requirements.txt через команда
pip freeze > requirements.txt
внутри backend создаем Django проект:
django-admin startproject config .
внутри backend создаем приложение:
python manage.py startapp accounts

## Frontend

npm create vite@latest frontend
 y
React
JavaScript
ESLint
Yes