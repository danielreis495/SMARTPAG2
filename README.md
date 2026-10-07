# SmartPag — distribuição e conciliação de pagamentos

Aplicação Streamlit com interface no navegador para o relatório JDE R5504110.

## Executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

`app.py` serve `index.html`. A interface lê o PDF com PDF.js, confere os valores e permite distribuir os pagamentos entre bancos. `pdf_processor.py` é um leitor Python independente, mantido para conferência; ele não é chamado pela interface. As bibliotecas da interface são carregadas de CDNs e exigem acesso à internet no carregamento inicial.

## Conferência e importação

- Todas as linhas são somadas em centavos e comparadas com o `Total:` de cada beneficiário e com o total geral do PDF.
- Todos os arquivos selecionados são validados antes da inclusão na tabela. Uma divergência cancela a importação do lote.
- A identificação inclui beneficiário, tipo, voucher, companhia, item, fatura, vencimento e valor original. Itens diferentes com o mesmo valor são preservados; reimportações idênticas não são duplicadas.
- A quantidade de itens na tabela é diferente da quantidade de pagamentos indicada pelo JDE: vários itens podem compor o mesmo pagamento.
- Para editar valores, use o formato brasileiro `1.500,00`; valores inválidos não são aceitos.

## Dados e conciliação

O rascunho, as regras de banco e as baixas da conciliação são salvos no navegador. Eles não são compartilhados automaticamente entre computadores e podem ser perdidos se o armazenamento do navegador for apagado. Exporte os arquivos JSON para guardar cópias e compartilhar pela rede.

A exportação do lote mantém a tabela e inclui identificação JDE, agrupamento, valor original e ajuste. Limpe a tabela somente depois de confirmar que o arquivo foi salvo. A conciliação valida o JSON importado e recupera as baixas salvas ao recarregar a página. Exporte o JSON atualizado para transmitir essas baixas a outro usuário.

**Rascunhos anteriores à correção de outubro/2026:** exporte Excel e JSON para preservar a distribuição, limpe a tabela e reimporte os PDFs. A importação sobre linhas antigas é bloqueada porque elas não registram companhia/item e podem conter itens descartados pela identificação antiga.

## Filtros e agrupamento

Os cards e fitas exibem o lote completo. Excel e relatório por banco respeitam as linhas visíveis nos filtros. Grupos são contados uma única vez; o total permanece correto mesmo antes de selecionar um banco. A consolidação automática separa beneficiário, tipo de documento, voucher e companhia.

## Verificação

```bash
node --test tests/*.test.cjs
```

Os testes cobrem identificação dos itens, centavos, valores inválidos, edição repetida, grupos sem banco, validação da conciliação, escape de HTML e conferência do PDF com total divergente ou ausente.

## Publicação no Streamlit

Selecione o repositório `danielreis495/SMARTPAG2`, branch `main`, arquivo principal `app.py`. O repositório não registra o endereço da implantação ativa; confira a versão publicada no painel do Streamlit após atualizar a branch.
