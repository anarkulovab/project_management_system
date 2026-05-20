FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD python manage.py migrate --noinput && python fill_db.py && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2