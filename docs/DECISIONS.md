# Decisions

Django 6.1.2 / Python 3.14 / PostgreSQL 17. Monolito modular. psycopg3. Defaults dev password postgres.

\n## Decisões Etapa E
- Carrinho persistido na sessão do Django (request.session).
- User padrão do Django; sem modelo customizado.
- Status de pedido: pending, paid (simulado), cancelled, failed.
- Comissão da KLYA: taxa configurável via CommissionConfig (provisória, 5% dev).
- Pagamento simulado sem dados reais de cartão.
- Idempotência via idempotency_key no pedido.
- Estoque descontado dentro de transaction.atomic com select_for_update().

