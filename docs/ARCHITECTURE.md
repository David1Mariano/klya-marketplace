# Architecture

Monolito modular Django. Apps: core, accounts, sellers, catalog, cart, orders, commissions, payments. Config em config/. Templates em templates/, static em static/.

# Security

Segredos via env. DEBUG controla cookies seguros. ORM para queries. Validação server-side.

# Roadmap

A: inspecao/planejamento (feito). B: fundacao (feito). C: contas/vendedores. D: catalogo. E: pedidos (feito).

# Decisions

Django 6.1.2 / Python 3.14 / PostgreSQL 17. Monolito modular. psycopg3.

\n## Etapa C - Autenticação e Lojas (implementado)
- Cadastro, login, logout com auth nativo.
- Perfil com solicitação de loja.
- Fluxo de aprovação/rejeição por admin.
- Proteções servidor (decorators, ownership).


\n## Etapa D - Catálogo e Produtos (implementado)
- Catálogo público mostra apenas produtos publicados de lojas aprovadas.
- Busca/filtro por categoria, detalhes de produto.
- Gerenciamento de produtos por vendedores com loja aprovada (criar/editar, draft/publicado).
- Proteções: não expor produtos de outros, não mostrar produtos não publicados ou de lojas não aprovadas.


\n## Etapa E - Carrinho, Pedidos, Estoque e Comissões (implementado)

### Carrinho
- Persistência na sessão do Django (request.session), vinculada ao usuário logado.
- Aceita apenas produtos publicados, ativos e de lojas aprovadas.
- Preço e estoque sempre revalidados no servidor; nunca confia em valores do navegador.
- Proteção CSRF e login obrigatório nas ações privadas.

### Pedidos
- Order (pedido principal): comprador, status, total, idempotency_key, datas.
- SellerOrder (pedido por vendedor): loja, status individual, subtotal, vinculado ao Order.
- OrderItem: produto, nome/sku registrados na compra, preço unitário, quantidade, subtotal.
- Status: pending, paid (simulado), cancelled, failed. Transições explícitas, não arbitrárias.
- Divisão por vendedor: um Order principal + N SellerOrders (um por loja) + itens no SellerOrder correto.
- Totais coerentes: soma dos subtotais dos SellerOrders = total do Order.

### Estoque
- Transação atômica (transaction.atomic) na finalização.
- select_for_update() nos produtos para bloqueio de linha (quando suportado pelo banco).
- Revalidação de estoque e disponibilidade dentro da transação após o bloqueio.
- Não permite estoque negativo; baixa feita uma única vez no momento da finalização.
- Idempotência via idempotency_key: segunda requisição com mesmo carrinho retorna o pedido existente.
- Carrinho limpo apenas após sucesso total (rollback automático em caso de erro).

### Comissões
- CommissionConfig: taxa configurável (provisória, desenvolvimento), única ativa por vez.
- Commission: registrada por SellerOrder no momento da compra (taxa, bruto, comissão, líquido copiados).
- Vendedores não alteram suas próprias comissões.

### Pagamento simulado
- Payment: pendente, aprovado (simulado), cancelado, falha simulada.
- Nenhum dado real de cartão coletado ou armazenado.
- Não é transação financeira real.
- Idempotência: status terminal impede reprocessamento.
- Apenas o comprador do pedido pode alterar seu pagamento.

