# GABARITO – o que o programa deve (e não deve) encontrar
Sessão de abertura considerada: 05/10/2026. Total teto do edital: R$ 26.752,96.

## Alfa Alimentos – ESPERADO: 🟢 nenhum achado crítico
- Todos os documentos presentes e válidos; CNPJ 12.345.678/0001-95 igual em todos; ME; declaração assinada e com processo correto.
- Proposta: todos os preços abaixo do teto, contas certas (total R$ 24.880,64).
- **A CNDT é um PDF só de imagem (`scan_0012.pdf`)**: o programa deve usar OCR, reconhecer que é CNDT e ler a validade 23/03/2027. É aceitável um achado de **baixa gravidade** do tipo "documento lido por OCR – confira".
- Se aparecer achado crítico aqui, é **falso positivo** (bug).

## Beta Distribuidora – ESPERADO: 🔴 vários achados
| # | Achado esperado | Onde | Gravidade |
|---|---|---|---|
| 1 | Certidão municipal **ausente** | pasta sem o documento | Alta/Crítica |
| 2 | **CRF-FGTS vencida** (validade 12/09/2026) | `doc_03.pdf` | Crítica |
| 3 | **Certidão federal POSITIVA** (há débitos) | `CND_federal.pdf` | Crítica |
| 4 | **Certidão de falência** emitida 10/06/2026 (mais de 90 dias antes da sessão) | `certidao_falencia.pdf` | Alta |
| 5 | **Porte "DEMAIS"** no cartão CNPJ, mas a licitação é exclusiva ME/EPP/MEI e a declaração marca "SIM, ME/EPP" (contradição) | `cartao_cnpj.pdf` x `declaracao_anexo3.pdf` | Crítica |
| 6 | **Objeto social incompatível** (construção civil/engenharia) com fornecimento de alimentos *(análise por IA – máx. gravidade média, com trecho literal)* | `contrato_social.pdf` | Média |
| 7 | **Declaração com nº errado** (Processo 165/2026, Dispensa 045/2026) e **sem assinatura** | `declaracao_anexo3.pdf` | Alta |
| 8 | **Preço acima do teto**: item 16 = R$ 8,50 (teto R$ 7,71) | `proposta_precos.pdf` | Crítica |
| 9 | **Item 19 (salsicha) ausente** na proposta | `proposta_precos.pdf` | Alta |
| 10 | **Erro aritmético** no item 3 (total com R$ 10,00 a mais) e **total geral errado** (R$ 120,00 a menos que a soma) | `proposta_precos.pdf` | Alta |
| 11 | **CNPJ da proposta diferente** do resto dos documentos e **com dígito verificador inválido** (98.765.432/0001-89 x 98.765.432/0001-98) | `proposta_precos.pdf` | Crítica |
| 12 | Proposta **sem assinatura** | `proposta_precos.pdf` | Média |
Não devem gerar achado: certidão estadual, CNDT, endereço/telefone do cartão CNPJ.

## Gama Atacado – ESPERADO: 🟢 sem problema de habilitação, **🟡 alerta de possível vínculo**
- Documentos e proposta corretos (total R$ 25.679,35).
- **Mesmo endereço, mesmo telefone e mesmo sócio/CPF** da Beta Distribuidora → alerta de **possível vínculo entre concorrentes** (texto cauteloso, nunca "conluio").

## Quadro de preços esperado
Menor total entre as propostas sem achado crítico: **Alfa Alimentos** (R$ 24.880,64). A Beta Distribuidora tem total menor, mas só ganharia se os achados críticos fossem descartados.

## Critério de sucesso do teste
- Todos os 12 achados da Beta Distribuidora aparecem, com página e trecho destacado.
- Nenhum achado crítico na Alfa Alimentos e na Gama Atacado.
- O alerta de vínculo aparece entre Beta Distribuidora e Gama Atacado.
- O programa **não** afirma "desclassificada": só "possível motivo".
