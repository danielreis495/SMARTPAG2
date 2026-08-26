import io
import json
from datetime import date, datetime
import pandas as pd
import streamlit as st

import pdf_processor

st.set_page_config(
    page_title="SmartPag - Distribuição & Conciliação",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

BANCOS_OPCOES = ["", "Itaú", "Santander", "Bradesco", "Caixa", "Banco do Brasil"]
CLASSIFICACOES = ["Fornecedores", "Concessionária", "Tributo", "Débito em Conta", "RH"]

# ==========================================
# FUNÇÕES AUXILIARES DE FORMATAÇÃO
# ==========================================
def formatar_moeda(valor: float) -> str:
    if valor is None:
        return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero(valor: float) -> str:
    if valor is None:
        return "0,00"
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ==========================================
# ESTADO DA SESSÃO (SESSION STATE)
# ==========================================
if "pagamentos" not in st.session_state:
    st.session_state.pagamentos = []

if "regras_banco" not in st.session_state:
    st.session_state.regras_banco = {
        "por_tipo": {},
        "por_beneficiario": {},
    }

if "banco_conciliacao" not in st.session_state:
    st.session_state.banco_conciliacao = []

if "responsavel" not in st.session_state:
    st.session_state.responsavel = ""


# ==========================================
# APLICAÇÃO DE REGRAS AUTOMÁTICAS
# ==========================================
def aplicar_regra_banco(tipo_doc: str, benef_cod: str) -> str:
    regras = st.session_state.regras_banco
    if benef_cod and benef_cod in regras.get("por_beneficiario", {}):
        return regras["por_beneficiario"][benef_cod]
    if tipo_doc:
        for tp in tipo_doc.split(", "):
            if tp in regras.get("por_tipo", {}):
                return regras["por_tipo"][tp]
    return ""


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.title("🏦 SmartPag")
    st.caption("Distribuição de Caixa & Conciliação Bancária")
    st.divider()

    aba_selecionada = st.radio(
        "Navegação",
        ["📦 Distribuição de Caixa", "📋 Resumo & Fitas", "🔄 Conciliação", "⚙️ Configurar Regras"],
        index=0,
    )

    st.divider()
    st.subheader("📅 Data do Lote")
    data_lote = st.date_input("Data de Pagamento", value=date.today())

    st.divider()
    st.subheader("👤 Usuário")
    st.session_state.responsavel = st.text_input(
        "Responsável",
        value=st.session_state.responsavel,
        placeholder="Seu nome...",
    )


# ==========================================
# ABA 1: DISTRIBUIÇÃO DE CAIXA
# ==========================================
if aba_selecionada == "📦 Distribuição de Caixa":
    st.header("📦 Importação e Distribuição de Pagamentos")

    col_up, col_acoes = st.columns([3, 2])
    with col_up:
        uploaded_files = st.file_uploader(
            "Importar Relatório JDE R5504110 (PDF)",
            type=["pdf"],
            accept_multiple_files=True,
            help="Selecione um ou múltiplos arquivos PDF do relatório JDE.",
        )

    with col_acoes:
        st.write("Ações Rápidas:")
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("🧹 Limpar Tabela", use_container_width=True):
                st.session_state.pagamentos = []
                st.rerun()
        with col_b2:
            if st.button("🤖 Reaplicar Regras", use_container_width=True):
                for p in st.session_state.pagamentos:
                    if not p["banco"]:
                        p["banco"] = aplicar_regra_banco(p["tipos_documento"], p["beneficiario_codigo"])
                st.success("Regras reaplicadas com sucesso!")
                st.rerun()

    # Processamento dos PDFs carregados
    if uploaded_files:
        if st.button("🚀 Processar PDF(s) Selecionados", type="primary"):
            novos_itens = 0
            for file in uploaded_files:
                try:
                    rows, groups, footer = pdf_processor.extract_payments(file)
                    lista = pdf_processor.montar_lista_pagamento(groups)
                    
                    for item in lista:
                        # Evita duplicatas exatas por código + valor + vouchers
                        ja_existe = any(
                            p["beneficiario_codigo"] == item["beneficiario_codigo"]
                            and abs(p["valor_a_pagar"] - item["valor_a_pagar"]) < 0.01
                            and p["vouchers"] == item["vouchers"]
                            for p in st.session_state.pagamentos
                        )
                        if not ja_existe:
                            # Aplica regras salvas
                            item["banco"] = aplicar_regra_banco(item["tipos_documento"], item["beneficiario_codigo"])
                            st.session_state.pagamentos.append(item)
                            novos_itens += 1
                except Exception as e:
                    st.error(f"Erro ao processar o arquivo {file.name}: {e}")

            st.success(f"Processamento concluído! {novos_itens} novo(s) pagamento(s) adicionado(s).")
            st.rerun()

    # Métricas gerais
    total_valor = sum(p["valor_a_pagar"] for p in st.session_state.pagamentos)
    total_qtd = len(st.session_state.pagamentos)
    sem_banco = sum(1 for p in st.session_state.pagamentos if not p["banco"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Valor Total na Tela", formatar_moeda(total_valor))
    m2.metric("Total de Pagamentos", total_qtd)
    m3.metric("Sem Banco Definido", sem_banco, delta=-sem_banco if sem_banco > 0 else 0, delta_color="inverse")
    m4.metric("Data do Lote", data_lote.strftime("%d/%m/%Y"))

    st.divider()

    if st.session_state.pagamentos:
        st.subheader("📋 Tabela de Pagamentos")

        # Filtros
        f1, f2, f3 = st.columns([2, 1, 1])
        with f1:
            busca = st.text_input("🔍 Buscar por Beneficiário, Código ou Voucher", placeholder="Digite para filtrar...")
        with f2:
            filtro_banco = st.selectbox("Filtrar por Banco", ["Todos"] + BANCOS_OPCOES[1:] + ["Sem Banco"])
        with f3:
            filtro_classif = st.selectbox("Filtrar por Classificação", ["Todas"] + CLASSIFICACOES)

        # Prepara DataFrame para edição interativa
        dados_tabela = []
        for idx, p in enumerate(st.session_state.pagamentos):
            # Aplica filtros
            if busca:
                b_str = f"{p['beneficiario_codigo']} {p['beneficiario_nome']} {p['vouchers']} {p['faturas']}".lower()
                if busca.lower() not in b_str:
                    continue
            if filtro_banco != "Todos":
                if filtro_banco == "Sem Banco" and p["banco"]:
                    continue
                if filtro_banco != "Sem Banco" and p["banco"] != filtro_banco:
                    continue
            if filtro_classif != "Todas" and p["classificacao"] != filtro_classif:
                continue

            dados_tabela.append({
                "ID": idx,
                "Cód. Benef.": p["beneficiario_codigo"],
                "Beneficiário": p["beneficiario_nome"],
                "Voucher": p["vouchers"],
                "Tipo": p["tipos_documento"],
                "Fatura": p["faturas"],
                "Vencimento": p["vencimentos"],
                "Valor (R$)": p["valor_a_pagar"],
                "Classificação": p["classificacao"],
                "Banco": p["banco"],
                "Observação": p["observacao"],
            })

        df = pd.DataFrame(dados_tabela)

        if not df.empty:
            edited_df = st.data_editor(
                df,
                column_config={
                    "ID": None,  # Oculta ID
                    "Valor (R$)": st.column_config.NumberColumn(
                        "Valor (R$)",
                        format="R$ %.2f",
                    ),
                    "Classificação": st.column_config.SelectboxColumn(
                        "Classificação",
                        options=CLASSIFICACOES,
                        required=True,
                    ),
                    "Banco": st.column_config.SelectboxColumn(
                        "Banco",
                        options=BANCOS_OPCOES,
                    ),
                    "Observação": st.column_config.TextColumn(
                        "Observação",
                        max_chars=200,
                    ),
                },
                disabled=["Cód. Benef.", "Beneficiário", "Voucher", "Tipo", "Fatura", "Vencimento", "Valor (R$)"],
                use_container_width=True,
                height=450,
                key="editor_pagamentos",
            )

            # Atualiza session_state com edições
            for _, row in edited_df.iterrows():
                real_idx = int(row["ID"])
                st.session_state.pagamentos[real_idx]["classificacao"] = row["Classificação"]
                st.session_state.pagamentos[real_idx]["banco"] = row["Banco"]
                st.session_state.pagamentos[real_idx]["observacao"] = row["Observação"]

            st.divider()

            # Botões de Exportação
            c_exp1, c_exp2, c_exp3 = st.columns(3)
            with c_exp1:
                # Exportar Excel
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
                    export_df = df.drop(columns=["ID"])
                    export_df.to_excel(writer, index=False, sheet_name="Pagamentos")
                st.download_button(
                    label="📊 Baixar Tabela em Excel (.xlsx)",
                    data=output_excel.getvalue(),
                    file_name=f"SmartPag_{data_lote.strftime('%Y-%m-%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

            with c_exp2:
                # Exportar JSON para Conciliação
                export_json_data = [
                    {
                        "beneficiario": p["beneficiario_nome"],
                        "beneficiario_codigo": p["beneficiario_codigo"],
                        "voucher": p["vouchers"],
                        "fatura": p["faturas"],
                        "vencimento": p["vencimentos"],
                        "valor": formatar_moeda(p["valor_a_pagar"]),
                        "valor_numerico": p["valor_a_pagar"],
                        "classificacao": p["classificacao"],
                        "banco": p["banco"],
                        "observacao": p["observacao"],
                        "data_pagamento": data_lote.strftime("%d/%m/%Y"),
                        "status": "Pendente",
                    }
                    for p in st.session_state.pagamentos
                    if p["banco"]
                ]
                json_str = json.dumps(export_json_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="💾 Exportar Banco para Rede (JSON)",
                    data=json_str,
                    file_name=f"SmartPag_Exportacao_{data_lote.strftime('%Y-%m-%d')}.json",
                    mime="application/json",
                    use_container_width=True,
                )

            with c_exp3:
                if st.button("💾 Salvar Banco & Enviar para Conciliação", type="primary", use_container_width=True):
                    com_banco = [p for p in st.session_state.pagamentos if p["banco"]]
                    if com_banco:
                        for p in com_banco:
                            st.session_state.banco_conciliacao.append({
                                "beneficiario": p["beneficiario_nome"],
                                "beneficiario_codigo": p["beneficiario_codigo"],
                                "voucher": p["vouchers"],
                                "fatura": p["faturas"],
                                "vencimento": p["vencimentos"],
                                "valor": formatar_moeda(p["valor_a_pagar"]),
                                "valor_numerico": p["valor_a_pagar"],
                                "classificacao": p["classificacao"],
                                "banco": p["banco"],
                                "observacao": p["observacao"],
                                "data_pagamento": data_lote.strftime("%d/%m/%Y"),
                                "status": "Pendente",
                                "responsavel_baixa": "",
                                "data_baixa": "",
                            })
                        st.session_state.pagamentos = [p for p in st.session_state.pagamentos if not p["banco"]]
                        st.success(f"{len(com_banco)} pagamentos enviados para a aba Conciliação!")
                        st.rerun()
                    else:
                        st.warning("Nenhum pagamento possui banco selecionado.")
        else:
            st.info("Nenhum pagamento corresponde aos filtros aplicados.")
    else:
        st.info("Nenhum relatório importado. Faça o upload do arquivo PDF do JDE acima para começar.")


# ==========================================
# ABA 2: RESUMO & FITAS DE CÁLCULO
# ==========================================
elif aba_selecionada == "📋 Resumo & Fitas":
    st.header("📋 Resumo por Banco & Fitas de Cálculo")
    st.caption(f"Lote referente a: {data_lote.strftime('%d/%m/%Y')}")

    bancos_ativos = [b for b in BANCOS_OPCOES if b]
    
    # Agrupamento de dados por Banco e Classificação
    resumo = {}
    for b in bancos_ativos:
        resumo[b] = {"total": 0.0, "qtd": 0, "classificacoes": {c: {"total": 0.0, "qtd": 0, "itens": []} for c in CLASSIFICACOES}}

    for p in st.session_state.pagamentos:
        banco = p["banco"]
        if banco in resumo:
            classif = p["classificacao"]
            val = p["valor_a_pagar"]
            resumo[banco]["total"] += val
            resumo[banco]["qtd"] += 1
            if classif in resumo[banco]["classificacoes"]:
                resumo[banco]["classificacoes"][classif]["total"] += val
                resumo[banco]["classificacoes"][classif]["qtd"] += 1
                resumo[banco]["classificacoes"][classif]["itens"].append(p)

    # Exibição dos cards/fitas em colunas
    cols = st.columns(len(bancos_ativos))
    for i, banco in enumerate(bancos_ativos):
        dados_banco = resumo[banco]
        with cols[i]:
            st.markdown(
                f"""
                <div style="background-color: #f8fafc; border: 2px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-bottom: 15px;">
                    <h4 style="text-align: center; margin: 0; color: #1e293b;">🏦 {banco.upper()}</h4>
                    <p style="text-align: center; font-size: 0.85em; color: #64748b; margin-top: 4px;">{dados_banco['qtd']} Pagamento(s)</p>
                    <hr style="margin: 8px 0;"/>
                    <h3 style="text-align: center; color: #0f172a; margin: 5px 0;">{formatar_moeda(dados_banco['total'])}</h3>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Detalhes por classificação (como solicitado no exemplo)
            if dados_banco["qtd"] > 0:
                with st.expander("Ver Detalhes / Fita", expanded=True):
                    for classif, c_info in dados_banco["classificacoes"].items():
                        if c_info["qtd"] > 0:
                            st.markdown(
                                f"**{classif}:** `{formatar_moeda(c_info['total'])}` &nbsp; *({c_info['qtd']})*"
                            )
                            for item in c_info["itens"]:
                                st.caption(f"↳ {item['beneficiario_nome']}: {formatar_moeda(item['valor_a_pagar'])}")
                            st.divider()

    st.divider()
    st.subheader("📄 Relatório Consolidado para Impressão")
    relatorio_linhas = []
    for banco in bancos_ativos:
        d = resumo[banco]
        if d["qtd"] > 0:
            for classif, c_info in d["classificacoes"].items():
                if c_info["qtd"] > 0:
                    relatorio_linhas.append({
                        "Banco": banco,
                        "Classificação": classif,
                        "Valor (R$)": c_info["total"],
                        "Quantidade": c_info["qtd"],
                    })

    if relatorio_linhas:
        df_rel = pd.DataFrame(relatorio_linhas)
        st.dataframe(
            df_rel,
            column_config={
                "Valor (R$)": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                "Quantidade": st.column_config.NumberColumn("Quantidade de Pagamentos"),
            },
            use_container_width=True,
        )
    else:
        st.info("Nenhum banco atribuído ainda para gerar o relatório consolidado.")


# ==========================================
# ABA 3: CONCILIAÇÃO DIÁRIA
# ==========================================
elif aba_selecionada == "🔄 Conciliação":
    st.header("🔄 Conciliação Diária de Pagamentos")

    col_up_c, col_down_c = st.columns([3, 2])
    with col_up_c:
        json_file = st.file_uploader(
            "📂 Carregar Arquivo JSON da Rede",
            type=["json"],
            help="Carregue o arquivo gerado pela aba de Distribuição para realizar as baixas.",
        )
        if json_file:
            try:
                dados_importados = json.load(json_file)
                st.session_state.banco_conciliacao = dados_importados
                st.success("Arquivo carregado com sucesso!")
            except Exception as e:
                st.error(f"Erro ao ler arquivo JSON: {e}")

    with col_down_c:
        if st.session_state.banco_conciliacao:
            json_exp = json.dumps(st.session_state.banco_conciliacao, indent=2, ensure_ascii=False)
            st.download_button(
                label="💾 Baixar Arquivo Atualizado",
                data=json_exp,
                file_name=f"SmartPag_Conciliado_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True,
            )

    if st.session_state.banco_conciliacao:
        st.subheader("📋 Itens em Conciliação")

        for idx, item in enumerate(st.session_state.banco_conciliacao):
            status = item.get("status", "Pendente")
            is_conciliado = status == "Conciliado"

            c_status, c_info, c_valor, c_acao = st.columns([1.5, 4, 2, 1.5])
            with c_status:
                if is_conciliado:
                    st.success(f"✅ Conciliado\n\nPor: {item.get('responsavel_baixa', '-')}")
                else:
                    st.warning("⏳ Pendente")

            with c_info:
                st.markdown(f"**{item.get('beneficiario', '-')}** ({item.get('banco', '-')})")
                st.caption(f"Voucher: {item.get('voucher', '-')} | Data Pag: {item.get('data_pagamento', '-')}")
                if item.get("observacao"):
                    st.caption(f"Obs: {item['observacao']}")

            with c_valor:
                st.markdown(f"### {item.get('valor', 'R$ 0,00')}")

            with c_acao:
                if not is_conciliado:
                    if st.button("✔️ Baixar", key=f"baixa_{idx}", use_container_width=True):
                        st.session_state.banco_conciliacao[idx]["status"] = "Conciliado"
                        st.session_state.banco_conciliacao[idx]["responsavel_baixa"] = (
                            st.session_state.responsavel or "Não informado"
                        )
                        st.session_state.banco_conciliacao[idx]["data_baixa"] = datetime.now().strftime(
                            "%d/%m/%Y %H:%M"
                        )
                        st.rerun()
                else:
                    if st.button("↩️ Desfazer", key=f"desfazer_{idx}", use_container_width=True):
                        st.session_state.banco_conciliacao[idx]["status"] = "Pendente"
                        st.session_state.banco_conciliacao[idx]["responsavel_baixa"] = ""
                        st.session_state.banco_conciliacao[idx]["data_baixa"] = ""
                        st.rerun()
            st.divider()
    else:
        st.info("Nenhum dado de conciliação carregado no momento.")


# ==========================================
# ABA 4: CONFIGURAÇÃO DE REGRAS
# ==========================================
elif aba_selecionada == "⚙️ Configurar Regras":
    st.header("⚙️ Regras de Atribuição Automática de Banco")
    st.write("Configure aqui os bancos padrão por Tipo de Documento ou por Código do Beneficiário.")

    tab_tp, tab_benef = st.tabs(["📄 Por Tipo de Documento", "🏭 Por Código de Beneficiário"])

    with tab_tp:
        st.subheader("Regras por Tipo de Documento")
        tipos_disponiveis = ["PP", "PD", "PH", "PI", "PS", "PV", "NO", "P4", "P5", "P8"]
        
        cols_tp = st.columns(2)
        for i, tp in enumerate(tipos_disponiveis):
            with cols_tp[i % 2]:
                val_atual = st.session_state.regras_banco.get("por_tipo", {}).get(tp, "")
                idx_banco = BANCOS_OPCOES.index(val_atual) if val_atual in BANCOS_OPCOES else 0
                novo_banco = st.selectbox(
                    f"Tipo **{tp}** vai para:",
                    options=BANCOS_OPCOES,
                    index=idx_banco,
                    key=f"regra_tp_{tp}",
                )
                if novo_banco:
                    st.session_state.regras_banco["por_tipo"][tp] = novo_banco
                elif tp in st.session_state.regras_banco["por_tipo"]:
                    del st.session_state.regras_banco["por_tipo"][tp]

    with tab_benef:
        st.subheader("Regras por Beneficiário Fixo")
        st.caption("O código do beneficiário tem prioridade sobre o tipo de documento.")

        c_add1, c_add2, c_add3 = st.columns([2, 2, 1])
        with c_add1:
            novo_cod = st.text_input("Código do Beneficiário", placeholder="Ex: 897962")
        with c_add2:
            novo_banco_b = st.selectbox("Banco Padrão", BANCOS_OPCOES, key="novo_banco_benef")
        with c_add3:
            st.write("&nbsp;")
            if st.button("➕ Adicionar", use_container_width=True):
                if novo_cod and novo_banco_b:
                    st.session_state.regras_banco["por_beneficiario"][novo_cod.strip()] = novo_banco_b
                    st.success(f"Regra salva para {novo_cod} -> {novo_banco_b}")
                    st.rerun()

        st.divider()
        st.write("Regras cadastradas:")
        for cod, banco in list(st.session_state.regras_banco.get("por_beneficiario", {}).items()):
            c_r1, c_r2, c_r3 = st.columns([3, 3, 1])
            c_r1.write(f"**Cód:** {cod}")
            c_r2.write(f"**Banco:** {banco}")
            if c_r3.button("🗑️", key=f"del_{cod}"):
                del st.session_state.regras_banco["por_beneficiario"][cod]
                st.rerun()
