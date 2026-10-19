# KLYA Marketplace

Fundacao tecnica inicial (Etapas A e B).

## Requisitos
- Python 3.14
- PostgreSQL 17
- pip

## Instalacao
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```
Configure variaveis de ambiente (ou use defaults dev). Crie banco `klya`:
```
psql -U postgres -c "CREATE DATABASE klya;"
```
Migracoes:
```
python manage.py migrate
```
Servidor:
```
python manage.py runserver
```
Testes:
```
python manage.py test
```
Admin:
```
python manage.py createsuperuser
```
