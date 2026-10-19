# Architecture

Monolito modular Django. Apps: core, accounts, sellers, catalog, cart, orders, commissions, payments. Config em config/. Templates em templates/, static em static/.

# Security

Segredos via env. DEBUG controla cookies seguros. ORM para queries. Validação server-side.

# Roadmap

A: inspecao/planejamento (feito). B: fundacao (feito). C: contas/vendedores. D: catalogo. E: pedidos.

# Decisions

Django 6.1.2 / Python 3.14 / PostgreSQL 17. Monolito modular. psycopg3.

\n## Etapa C - Autenticação e Lojas (implementado)
- Cadastro, login, logout com auth nativo.
- Perfil com solicitação de loja.
- Fluxo de aprovação/rejeição por admin.
- Proteções servidor (decorators, ownership).

