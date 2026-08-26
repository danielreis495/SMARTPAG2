"""pdf_processor.py - Extração do relatório JDE R5504110 (Requisito de Caixa).

Parsing baseado em posição (x0) das palavras extraídas pelo pdfplumber, não em
regex sobre texto corrido — o relatório R5504110 tem colunas de largura fixa,
mas o texto colado (sem espaço) entre código e nome do beneficiário, e quebras
de página no meio de um grupo, quebram qualquer abordagem baseada só em texto.

Validado contra um PDF real de 19 páginas / 295 pagamentos / 158 beneficiários:
- 158/158 grupos batendo exatamente com a linha "Total:" de cada beneficiário
- soma geral batendo exatamente com "Valor Total a ser processado"
"""

import re
from collections import defaultdict
from typing import Dict, List, Tuple, Union, BinaryIO

import pdfplumber

# Limites de coluna (x0, em pontos) calibrados contra o layout do R5504110.
# bucket(x0) devolve o índice da primeira posição em _BOUNDS que x0 < valor.
_BOUNDS = [186, 207, 237, 261, 279, 311, 370, 385, 426, 552, 744]
_COLS = [
    "benef_cod_nome", "tp", "voucher", "cia", "item", "dt_fatura",
    "valor_raw", "status", "forn_cod", "forn_nome", "fatura", "dt_venc",
]

_HEADER_PREFIXES = ("R5504110", "Relat", "Beneficiário")
_FOOTER_VALOR_LABEL = "Valor Total a ser processado"
_FOOTER_QTD_LABEL = "Número Total de Pagamentos"

_VALOR_RE = re.compile(r"-?[\d.]*,\d{2}-?")
_INT_RE = re.compile(r"\d+")


def _bucket(x0: float) -> int:
    x0 = round(x0)  # o x0 de uma mesma coluna pode oscilar em ~0.01pt entre
                     # linhas (arredondamento do PDF); sem isso, uma coluna
                     # cujo limite caia bem em cima de um valor inteiro (ex.
                     # 186.0 vs 185.999999997) pode ser classificada errado
    for i, b in enumerate(_BOUNDS):
        if x0 < b:
            return i
    return len(_BOUNDS)


def _parse_valor(s: str):
    """'1.234,56' -> 1234.56 | '1.234,56-' -> -1234.56 | inválido -> None"""
    s = s.strip()
    if not s:
        return None
    neg = s.endswith("-")
    s = s.rstrip("-").replace(".", "").replace(",", ".")
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def _split_beneficiario(raw: str) -> Tuple[str, str]:
    """'897962 ABRASIVOS AMARANTE LTDA' ou '897962ABRASIVOS...' -> (código, nome)"""
    m = re.match(r"^(\d+)\s*(.*)$", raw.strip())
    if m:
        return m.group(1), m.group(2).strip()
    return "", raw.strip()


def extract_payments(file_input: Union[str, BinaryIO]) -> Tuple[List[Dict], List[Dict], Dict]:
    """Extrai todas as linhas de detalhe do relatório R5504110.

    Suporta tanto caminho de arquivo (str) quanto buffer em memória (BytesIO/UploadedFile do Streamlit).

    Retorna:
        rows: lista de dicts, uma linha de detalhe por pagamento/retenção
        groups: lista de dicts por beneficiário, com total declarado x calculado
        footer: {"valor_total": float, "qtd_total": int} do rodapé do relatório
    """
    rows: List[Dict] = []
    groups: List[Dict] = []
    footer: Dict = {}

    current_group: List[Dict] = []
    pending_total_value = None

    with pdfplumber.open(file_input) as pdf:
        for page in pdf.pages:
            words = page.extract_words()
            lines = defaultdict(list)
            for w in words:
                lines[round(w["top"], 1)].append(w)

            tops = sorted(lines.keys())
            texts = [
                " ".join(w["text"] for w in sorted(lines[t], key=lambda w: w["x0"]))
                for t in tops
            ]

            for idx, top in enumerate(tops):
                ws = sorted(lines[top], key=lambda w: w["x0"])
                txt = texts[idx]
                next_txt = texts[idx + 1] if idx + 1 < len(texts) else ""

                # cabeçalho de página, repetido a cada página
                if txt.startswith(_HEADER_PREFIXES):
                    continue

                # rótulos do rodapé (o valor vem numa linha anterior)
                if txt.startswith(_FOOTER_VALOR_LABEL) or txt.startswith(_FOOTER_QTD_LABEL):
                    continue

                # valor do rodapé: linha anterior ao rótulo "Valor Total..."
                if next_txt.startswith(_FOOTER_VALOR_LABEL) and _VALOR_RE.fullmatch(txt.strip()):
                    footer["valor_total"] = _parse_valor(txt.strip())
                    continue
                if next_txt.startswith(_FOOTER_QTD_LABEL) and _INT_RE.fullmatch(txt.strip()):
                    footer["qtd_total"] = int(txt.strip())
                    continue

                # linha "fantasma" com só um número: às vezes é uma duplicata
                # visual do último valor do grupo, às vezes é o valor do
                # "Total:" que caiu sozinho numa linha por causa de quebra de
                # página. Guardamos como candidato; se o "Total:" seguinte já
                # tiver valor embutido, essa duplicata é simplesmente ignorada.
                if _VALOR_RE.fullmatch(txt.strip()) and len(ws) == 1:
                    pending_total_value = _parse_valor(txt.strip())
                    continue

                # fecha o grupo do beneficiário atual
                if txt.startswith("Total:"):
                    rest = txt.split("Total:", 1)[1].strip()
                    declared = _parse_valor(rest) if rest else None
                    if declared is None:
                        declared = pending_total_value if pending_total_value is not None else 0.0
                    pending_total_value = None

                    calculado = round(sum(r["valor"] for r in current_group), 2)
                    groups.append({
                        "beneficiario_codigo": current_group[0]["beneficiario_codigo"] if current_group else None,
                        "beneficiario_nome": current_group[0]["beneficiario_nome"] if current_group else None,
                        "total_declarado": declared,
                        "total_calculado": calculado,
                        "bate": abs(declared - calculado) < 0.005,
                        "linhas": current_group,
                    })
                    current_group = []
                    continue

                # linha de dado normal
                pending_total_value = None
                buckets = defaultdict(list)
                for w in ws:
                    buckets[_bucket(w["x0"])].append(w["text"])
                raw = {c: " ".join(buckets.get(i, [])) for i, c in enumerate(_COLS)}

                benef_cod, benef_nome = _split_beneficiario(raw["benef_cod_nome"])
                row = {
                    "beneficiario_codigo": benef_cod,
                    "beneficiario_nome": benef_nome,
                    "tipo_voucher": raw["tp"],
                    "voucher": raw["voucher"],
                    "cia": raw["cia"],
                    "item": raw["item"],
                    "dt_fatura": raw["dt_fatura"],
                    "valor": _parse_valor(raw["valor_raw"]) or 0.0,
                    "status": raw["status"],
                    "fornecedor_codigo": raw["forn_cod"],
                    "fornecedor_nome": raw["forn_nome"],
                    "fatura": raw["fatura"],
                    "dt_vencimento": raw["dt_venc"],
                }
                rows.append(row)
                current_group.append(row)

    return rows, groups, footer


def reconciliar(groups: List[Dict], footer: Dict) -> Dict:
    """Confere grupo a grupo contra o 'Total:' declarado e a soma geral contra o rodapé."""
    divergencias = [g for g in groups if not g["bate"]]
    soma_geral = round(sum(g["total_calculado"] for g in groups), 2)
    valor_rodape = footer.get("valor_total")
    bate_geral = valor_rodape is not None and abs(soma_geral - valor_rodape) < 0.01
    return {
        "divergencias": divergencias,
        "qtd_divergencias": len(divergencias),
        "soma_geral_calculada": soma_geral,
        "valor_total_rodape": valor_rodape,
        "qtd_total_rodape": footer.get("qtd_total"),
        "bate": bate_geral,
    }


def contar_pagamentos(rows: List[Dict]) -> Tuple[int, List[Dict]]:
    """Conta pagamentos "líquidos" no mesmo critério do rodapé do R5504110.

    Regra:
    - Vouchers do tipo PP costumam vir em pares +valor / -valor.
    - Um "pagamento" = um voucher distinto (tipo + número).
    """
    por_voucher_pp = defaultdict(list)
    for r in rows:
        if r["tipo_voucher"] == "PP":
            por_voucher_pp[r["voucher"]].append(r)

    linhas_validas = []
    for r in rows:
        if r["tipo_voucher"] != "PP":
            linhas_validas.append(r)
            continue
        grupo = por_voucher_pp[r["voucher"]]
        tem_positiva = any(g["valor"] > 0 for g in grupo)
        if tem_positiva and r["valor"] <= 0:
            continue
        linhas_validas.append(r)

    vouchers = set((r["tipo_voucher"], r["voucher"]) for r in linhas_validas)
    return len(vouchers), linhas_validas


def montar_lista_pagamento(groups: List[Dict]) -> List[Dict]:
    """Converte os `groups` (por beneficiário) na lista pronta para a tela de
    distribuição por banco: um valor líquido por beneficiário, já consolidando
    tributo/retenção e estorno, mais as faturas e vencimentos de referência.
    """
    pagamentos = []
    for g in groups:
        linhas = g["linhas"]
        faturas = sorted({l["fatura"] for l in linhas if l["fatura"]})
        vencimentos = sorted({l["dt_vencimento"] for l in linhas if l["dt_vencimento"]})
        fornecedores = {l["fornecedor_codigo"] for l in linhas if l["fornecedor_codigo"]}
        tipos_doc = sorted({l["tipo_voucher"] for l in linhas if l["tipo_voucher"]})
        vouchers = sorted({l["voucher"] for l in linhas if l["voucher"]})
        
        pagamentos.append({
            "beneficiario_codigo": g["beneficiario_codigo"],
            "beneficiario_nome": g["beneficiario_nome"],
            "vouchers": ", ".join(vouchers),
            "tipos_documento": ", ".join(tipos_doc),
            "valor_a_pagar": g["total_calculado"],
            "faturas": ", ".join(faturas),
            "vencimentos": ", ".join(vencimentos),
            "fornecedor_codigo_divergente": (
                sorted(fornecedores) if fornecedores - {g["beneficiario_codigo"]} else None
            ),
            "classificacao": "Fornecedores",
            "banco": "",
            "observacao": "",
            "linhas_originais": linhas,
        })
    return pagamentos
