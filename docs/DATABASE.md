# Configuração de Banco de Dados

## Produção (recomendado)
Por padrão, o projeto está configurado para PostgreSQL (django.db.backends.postgresql) em config/settings.py, lendo credenciais via variáveis de ambiente:
- POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT

Arquivo de exemplo: .env.example. Para produção, nunca commitar .env com segredos.

## Desenvolvimento (alternativa SQLite)
Caso PostgreSQL não esteja disponível no ambiente de desenvolvimento, criar um arquivo .env ou ajustar localmente com SQLite. Importante: manter configuração padrão do repositório como PostgreSQL.

Recomendação prática: usar SQLite para testes/dev rápido, PostgreSQL idêntico à produção. Nunca trocar silenciosamente o banco padrão no repositório.
