# 🏦 SmartPag - Sistema de Distribuição & Conciliação Bancária

Aplicação web desenvolvida em **Python** e **Streamlit** para processamento, distribuição por bancos e conciliação de pagamentos a partir do relatório **JDE R5504110 (Requisito de Caixa)**.

---

## 🚀 Como executar localmente

1. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Inicie o aplicativo:**
   ```bash
   streamlit run app.py
   ```

---

## ☁️ Como publicar no Streamlit Community Cloud

1. Crie um repositório no **GitHub** (ex: `smartpag`).
2. Faça o upload dos seguintes arquivos:
   - `app.py`
   - `pdf_processor.py`
   - `requirements.txt`
   - `.gitignore`
   - `README.md`
3. Acesse **[share.streamlit.io](https://share.streamlit.io/)** e faça login com sua conta do GitHub.
4. Clique em **"New app"**:
   - **Repository:** Selecione seu repositório do GitHub.
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Clique em **"Deploy!"** e compartilhe o link gerado com as pessoas do seu setor.

---

## ✨ Funcionalidades

- **Importação de múltiplos PDFs do JDE (R5504110)** com extração de alta precisão baseada em coordenadas via `pdfplumber`.
- **Validação de Reconciliação** com conferência contra o rodapé do relatório.
- **Distribuição de Bancos e Classificações** com edição em tabela interativa.
- **Regras Automáticas de Bancos** por tipo de documento (`PP, PD, PH, PI, PS, PV, NO, P4, P5, P8`) e código de beneficiário.
- **Fitas de Cálculo e Resumo por Banco** (Itaú, Santander, Bradesco, Caixa, Banco do Brasil) com totais e contagens.
- **Exportação para Excel (.xlsx)** e **JSON** para histórico e conciliação.
- **Aba de Conciliação Diária** com controle de baixa e registro do responsável.
