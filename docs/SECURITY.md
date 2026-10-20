# Security

Controles: env secrets, password validators, CSRF, secure cookies em prod. Riscos conhecidos: compras/pagamentos desativados; sem rate limiting ainda.

## Etapa E - Controles adicionados
- Login obrigatorio nas acoes privadas de carrinho, checkout, pedidos e pagamento simulado.
- Autorizacao por comprador (Order filtrado por buyer) e por loja (SellerOrder filtrado por store do usuario logado).
- Vendedor nao consulta pedidos de outros vendedores nem altera pedidos de terceiros.
- Protecao CSRF em todas as acoes de mutacao (POST).
- Validacao server-side de todos os valores recebidos (preco, quantidade, estoque, ids de produto/loja).
- Prevencao de acesso indevido por alteracao de IDs na URL (get_object_or_404 com filtro de ownership).
- Operacoes de finalizacao dentro de transacoes atomicas (transaction.atomic).
- Bloqueio de linhas com select_for_update() nos produtos durante o checkout.
- Idempotencia via idempotency_key para evitar pedidos duplicados e baixa dupla de estoque.
- Status terminal de pagamento impede reprocessamento.
- Nao armazenar dados financeiros reais (pagamento simulado).
