import sys
import shutil
import re
import platform
import requests
from pathlib import Path

# Garante que o pacote 'licitacoes' seja encontrado (pasta do projeto = 2 níveis acima deste arquivo)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd

from licitacoes.config import BASE_DIR, DATA_DIR, settings
from licitacoes.services.company import CompanyService, CONFIG_PATH
from licitacoes.services import persistence as db
from licitacoes.services.money import format_brl
from licitacoes.llm.client import llm_client
from licitacoes.ui.proposta import render_edital_page, render_proposta_page

# --- Page Config ---
st.set_page_config(
    page_title="Analisador de Licitações",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS for Custom Styling ---
st.markdown("""
    <style>
    .main { font-size: 18px !important; }
    .stButton>button { width: 100%; min-height: 3em; font-size: 18px !important; font-weight: bold !important; }
    .stTextInput input, .stTextArea textarea, .stSelectbox div { font-size: 18px !important; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; font-weight: bold; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------- navegação
PAGES = {
    "setup": "⚙️ Configuração",
    "edital": "📄 1. Edital",
    "proposta": "💰 2. Minha proposta",
    "concorrentes": "👥 3. Concorrentes",
    "resultado": "🏁 4. Resultado",
    "comparativo": "📊 5. Comparativo",
}
ORDER = list(PAGES)

def go(page: str):
    st.session_state.page = page
    st.rerun()

def _empresa_configurada() -> bool:
    try:
        c = CompanyService.get_company_data()
        return bool(c.razao_social.strip()) and "EXEMPLO" not in c.razao_social.upper()
    except Exception:
        return False

if "page" not in st.session_state:
    st.session_state.page = "edital" if _empresa_configurada() else "setup"
page = st.session_state.page

# ---------------------------------------------------------------- utilidades
def _safe_name(name: str) -> str:
    n = re.sub(r"[^\w.\- ]", "_", str(name)).strip(" .")
    return n[:80] or "sem_nome"

def _tender():
    tid = st.session_state.get("tender_id") or st.session_state.get("current_tender_id")
    return db.get_tender(tid) if tid else None

@st.cache_data(ttl=20)
def _ollama_ok(url: str) -> bool:
    try:
        return requests.get(f"{url}/api/tags", timeout=1).ok
    except Exception:
        return False

def _cnpj_valido(cnpj: str) -> bool:
    try:
        from licitacoes.rules.cnpj_cpf import CNPJRule
        return bool(CNPJRule().is_valid(cnpj))
    except Exception:
        return True

# ---------------------------------------------------------------- barra lateral
with st.sidebar:
    st.title("⚖️ Analisador")
    cur = ORDER.index(page) if page in ORDER else -1
    for i, key in enumerate(ORDER):
        icon = "✔" if 0 <= cur and i < cur else ("🔵" if i == cur else "⚪")
        if st.button(f"{icon} {PAGES[key]}", key=f"nav_{key}"):
            go(key)
    st.divider()
    if st.button("📁 Minhas licitações", key="nav_history"):
        go("history")
    if st.button("🩺 Diagnóstico", key="nav_diag"):
        go("diagnostico")

# ---------------------------------------------------------------- cabeçalho
t_atual = _tender()
c1, c2, c3 = st.columns([3, 2, 1])
with c1:
    st.subheader("📌 " + (t_atual["name"] if t_atual else "Nenhuma licitação aberta"))
with c2:
    st.markdown("<div style='text-align:right; font-weight:bold;'>⏳ Prazo não identificado</div>",
                unsafe_allow_html=True)
with c3:
    ok = _ollama_ok(settings.ollama.url)
    st.markdown(f"<div style='text-align:right; color:{'green' if ok else 'red'};'>"
                f"{'🟢' if ok else '🔴'} Ollama</div>", unsafe_allow_html=True)
st.divider()

# ---------------------------------------------------------------- páginas
def page_setup():
    st.header("⚙️ Dados da minha empresa")
    st.write("Preencha uma vez. Esses dados entram sozinhos na proposta e nas declarações.")
    c = CompanyService.get_company_data()
    portes = ["ME", "EPP", "MEI"]
    with st.form("company_form"):
        a, b = st.columns(2)
        with a:
            razao = st.text_input("Razão social", value=c.razao_social)
            cnpj = st.text_input("CNPJ", value=c.cnpj)
            endereco = st.text_area("Endereço", value=c.endereco)
        with b:
            porte = st.selectbox("Porte da empresa", portes,
                                 index=portes.index(c.porte) if c.porte in portes else 0)
            email = st.text_input("E-mail", value=c.email)
            tel = st.text_input("Telefone", value=c.telefone)
            banco = st.text_input("Dados bancários (banco/agência/conta)", value=c.dados_bancarios)
        enviar = st.form_submit_button("SALVAR →", type="primary")
    if enviar:
        if not razao.strip():
            st.error("Informe a razão social.")
        elif not cnpj.strip():
            st.error("Informe o CNPJ.")
        elif not _cnpj_valido(cnpj):
            st.error("CNPJ inválido. Confira os números.")
        else:
            try:
                CompanyService.update_company_data({
                    "razao_social": razao.strip(), "cnpj": cnpj.strip(), "endereco": endereco.strip(),
                    "porte": porte, "email": email.strip(), "telefone": tel.strip(),
                    "dados_bancarios": banco.strip()})
            except Exception as exc:
                st.error(f"Não consegui salvar os dados ({type(exc).__name__}).")
                with st.expander("Ver detalhes"):
                    st.code(str(exc))
            else:
                st.success("Dados salvos.")
                go("edital")

def page_edital():
    render_edital_page(on_done=lambda: go("proposta"))
    if st.session_state.get("tender_id") or st.session_state.get("current_tender_id"):
        st.divider()
        if st.button("IR PARA A MINHA PROPOSTA →", type="primary", key="go_prop"):
            go("proposta")

def page_proposta():
    render_proposta_page()
    st.divider()
    if st.button("PRÓXIMO PASSO: CONCORRENTES →", type="primary"):
        go("concorrentes")

def page_concorrentes():
    st.header("👥 Passo 3: Concorrentes")
    tender_id = st.session_state.get("current_tender_id") or st.session_state.get("tender_id")
    if not tender_id:
        st.info("Abra ou envie um edital primeiro (Passo 1).")
        return

    with st.expander("➕ Adicionar Novo Concorrente", expanded=True):
        with st.form("add_competitor_form", clear_on_submit=True):
            name = st.text_input("Nome da Empresa")
            uploaded_files = st.file_uploader("Arquivos do concorrente", accept_multiple_files=True)
            submit = st.form_submit_button("SALVAR CONCORRENTE")
            if submit and name:
                from licitacoes.services.persistence import create_competitor, add_competitor_file
                from licitacoes.config import DATA_DIR
                comp_id = create_competitor(tender_id, name)
                if uploaded_files:
                    storage_path = DATA_DIR / "competitors" / str(tender_id) / str(comp_id)
                    storage_path.mkdir(parents=True, exist_ok=True)
                    for uploaded_file in uploaded_files:
                        file_path = storage_path / _safe_name(uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        add_competitor_file(comp_id, uploaded_file.name, str(file_path))
                st.success(f"Concorrente {name} adicionado com sucesso!")
                st.rerun()
            elif submit and not name:
                st.error("O nome da empresa é obrigatório.")

    st.divider()
    st.write("### Licitantes Adicionados")
    from licitacoes.services.persistence import list_competitors, delete_competitor
    competitors = list_competitors(tender_id)
    if not competitors:
        st.info("Nenhum concorrente adicionado ainda.")
    else:
        for comp in competitors:
            col1, col2 = st.columns([4, 1])
            with col1: st.write(f"**{comp['name']}**")
            with col2:
                if st.button("🗑️", key=f"del_comp_{comp['id']}"):
                    delete_competitor(comp['id'])
                    st.rerun()

    st.divider()
    if competitors:
        if st.button("PRÓXIMO PASSO: RESULTADO →", type="primary"):
            go("resultado")
    else:
        st.info("Adicione ao menos um concorrente para prosseguir para a análise de resultados.")

def page_resultado():
    st.header("🏁 Passo 4: Resultado")
    tender_id = st.session_state.get("current_tender_id") or st.session_state.get("tender_id")
    if not tender_id:
        st.info("Abra ou envie um edital primeiro (Passo 1).")
        return
    from licitacoes.services.persistence import list_competitors
    competitors = list_competitors(tender_id)
    if not competitors:
        st.info("Nenhum concorrente adicionado para análise.")
        return
    competitor_names = [comp["name"] for comp in competitors]
    concorrente_name = st.selectbox("Escolha o licitante para análise", ["Nenhum"] + competitor_names, key=f"sel_comp_{tender_id}")
    if concorrente_name != "Nenhum":
        comp_id = next(c["id"] for c in competitors if c["name"] == concorrente_name)
        with st.spinner(f"Analisando documentos e preços de {concorrente_name}..."):
            from licitacoes.services.competitor_analysis import CompetitorAnalysisService
            achados = CompetitorAnalysisService.analyze_competitor(comp_id, tender_id)
        if not achados:
            st.success(f"✅ {concorrente_name} parece estar em conformidade.")
        else:
            for achado in achados:
                if achado["type"] == "error": st.error(f"🔴 {achado['msg']}")
                else: st.warning(f"⚠️ {achado['msg']}")
            st.divider()
            st.button("Confirmar Achados")
            st.button("Descartar")
    st.divider()
    if st.button("PRÓXIMO PASSO: COMPARATIVO →", type="primary"):
        go("comparativo")

def page_comparativo():
    st.header("📊 Passo 5: Comparativo de Preços")
    tender_id = st.session_state.get("current_tender_id") or st.session_state.get("tender_id")
    if not tender_id:
        st.info("Abra ou envie um edital primeiro (Passo 1).")
        return
    from licitacoes.services.persistence import get_items, list_competitors, get_competitor_proposal
    from licitacoes.services.money import format_brl
    items = get_items(tender_id)
    competitors = list_competitors(tender_id)
    if not items:
        st.warning("Não há itens para comparar.")
        return
    if not competitors:
        st.info("Adicione concorrentes para ver o comparativo.")
        return
    comp_prices = {}
    for comp in competitors:
        props = get_competitor_proposal(comp["id"])
        comp_prices[comp["id"]] = {p["item_number"]: p["proposed_cents"] for p in props}
    table_data = []
    for it in items:
        row = {"Item": it["number"], "Descrição": it["description"][:50] + "..." if len(it["description"]) > 50 else it["description"], "Minha Empresa": it["proposed_cents"] or 0}
        all_prices = [it["proposed_cents"] or 0]
        for comp in competitors:
            price = comp_prices[comp["id"]].get(it["number"], 0)
            row[comp["name"]] = price
            all_prices.append(price)
        valid_prices = [p for p in all_prices if p > 0]
        if not valid_prices: winner = "N/A"
        else:
            min_price = min(valid_prices)
            if min_price == (it["proposed_cents"] or 0): winner = "🌟 Minha Empresa"
            else:
                winner = "Minha Empresa"
                for comp in competitors:
                    if comp_prices[comp["id"]].get(it["number"]) == min_price:
                        winner = f"🏆 {comp['name']}"
                        break
        row["Vencedor"] = winner
        table_data.append(row)
    df_comp = pd.DataFrame(table_data)
    display_df = df_comp.copy()
    for col in df_comp.columns:
        if col not in ["Item", "Descrição", "Vencedor"]:
            display_df[col] = display_df[col].apply(lambda x: format_brl(int(x)) if x else "—")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.info("💡 Os preços exibidos são aqueles extraídos automaticamente dos arquivos dos concorrentes.")

def page_history():
    st.header("📁 Minhas licitações")
    mostrar = st.checkbox("Mostrar arquivadas")
    lista = db.list_tenders(include_archived=mostrar)
    if not lista:
        st.info("Nenhuma licitação salva ainda. Envie um edital no Passo 1.")
        return
    for t in lista:
        n_itens = len(db.get_items(t["id"]))
        a, b, c, d = st.columns([5, 2, 1, 1])
        a.markdown(f"**{t['name']}**" + ("  _(arquivada)_" if t["archived"] else ""))
        b.caption(f"{n_itens} itens · {format_brl(t['estimated_total_cents'])} · atualizada em {t['updated_at'][:10]}")
        if c.button("Abrir", key=f"open_{t['id']}"):
            st.session_state["tender_id"] = t["id"]
            go("proposta")
        if t["archived"]:
            if d.button("Restaurar", key=f"unarch_{t['id']}"):
                db.archive_tender(t["id"], False)
                st.rerun()
        elif d.button("Arquivar", key=f"arch_{t['id']}"):
            db.archive_tender(t["id"], True)
            st.rerun()

def page_diagnostico():
    st.header("🩺 Diagnóstico")
    st.caption("Serve para conferir se tudo está sendo salvo no lugar certo.")
    cont = db.counts()
    st.subheader("Onde ficam os dados")
    st.code(f"Pasta do projeto : {BASE_DIR}\n"
            f"Pasta de dados   : {DATA_DIR}\n"
            f"config.yaml      : {CONFIG_PATH}  ({'existe' if Path(CONFIG_PATH).exists() else 'ainda não criado'})\n"
            f"Banco de dados   : {db.DEFAULT_DB}  ({'existe' if db.DEFAULT_DB.exists() else 'ainda não criado'})")
    st.subheader("O que está salvo")
    a, b, c = st.columns(3)
    a.metric("Licitações", cont["tender"])
    b.metric("Itens de edital", cont["item"])
    c.metric("Preços/marcas salvos", cont["proposal"])
    st.subheader("Programas auxiliares")
    ollama_ok = _ollama_ok(settings.ollama.url)
    st.write(f"{'🟢' if ollama_ok else '🔴'} Ollama em `{settings.ollama.url}`")
    st.write(f"{'🟢' if shutil.which('tesseract') else '🔴'} Tesseract (leitura de documentos escaneados)")
    st.caption(f"Python {platform.python_version()} · Streamlit {st.__version__}")

# --- Router ---
if st.session_state.page == "setup":
    page_setup()
elif st.session_state.page == "edital":
    page_edital()
elif st.session_state.page == "proposta":
    page_proposta()
elif st.session_state.page == "concorrentes":
    page_concorrentes()
elif st.session_state.page == "resultado":
    page_resultado()
elif st.session_state.page == "comparativo":
    page_comparativo()
elif st.session_state.page == "history":
    page_history()
elif st.session_state.page == "diagnostico":
    page_diagnostico()
else:
    st.write("Página não encontrada.")
