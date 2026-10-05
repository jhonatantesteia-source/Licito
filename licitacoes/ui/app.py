import sys
import os
from pathlib import Path

# Proteção extra para caminhos com espaço e execução via script
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))
sys.path.insert(0, str(root_path))

import streamlit as st
import pandas as pd
from pathlib import Path
from licitacoes.config import settings
from licitacoes.services.company import CompanyService
from licitacoes.llm.client import llm_client
from licitacoes.ui.proposta import render_edital_page, render_proposta_page
import requests

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
    .main {
        font-size: 18px !important;
    }
    .stButton>button {
        width: 100%;
        height: 3em;
        font-size: 20px !important;
        font-weight: bold !important;
    }
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        font-size: 18px !important;
    }
    .status-box {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        font-weight: bold;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- State Management ---
if "page" not in st.session_state:
    st.session_state.page = "setup"
if "current_tender" not in st.session_state:
    st.session_state.current_tender = None

# Mapping of numeric steps to page names for the progress bar
STEP_TO_PAGE = {
    0: "setup",
    1: "edital",
    2: "proposta",
    3: "concorrentes",
    4: "resultado",
    5: "comparativo"
}
PAGE_TO_STEP = {v: k for k, v in STEP_TO_PAGE.items()}

# --- Sidebar ---
with st.sidebar:
    st.title("⚖️ Analisador")

    # Progress indicators
    steps = {
        0: "⚙️ Configuração",
        1: "📄 Edital",
        2: "💰 Minha Proposta",
        3: "👥 Concorrentes",
        4: "🏁 Resultado",
        5: "📊 Comparativo"
    }

    current_step = PAGE_TO_STEP.get(st.session_state.page, 99)

    for s_id, s_name in steps.items():
        icon = "✔" if s_id < current_step else ("🔵" if s_id == current_step else "⚪")
        if st.button(f"{icon} {s_name}", key=f"step_{s_id}"):
            st.session_state.page = STEP_TO_PAGE[s_id]
            st.rerun()

    st.divider()
    if st.button("📁 Minhas Licitações"):
        st.session_state.page = "history"
        st.rerun()
    if st.button("⚙️ Configurações Gerais"):
        st.session_state.page = "setup"
        st.rerun()

# --- Header ---
col1, col2, col3 = st.columns([3, 2, 1])
with col1:
    tender_name = st.session_state.current_tender.get("name", "Nenhuma Licitação Selecionada") if st.session_state.current_tender else "Inicie a análise"
    st.subheader(f"📌 {tender_name}")
with col2:
    # Mock countdown for now
    st.markdown("<div style='text-align:right; color:red; font-weight:bold;'>⏳ Prazo: Calculando...</div>", unsafe_allow_html=True)
with col3:
    try:
        requests.get(f"{settings.ollama.url}/api/tags", timeout=1)
        st.markdown("<div style='text-align:right; color:green;'>🟢 Ollama</div>", unsafe_allow_html=True)
    except:
        st.markdown("<div style='text-align:right; color:red;'>🔴 Ollama</div>", unsafe_allow_html=True)

def _ir_para(page_name):
    st.session_state.page = page_name
    st.rerun()

def page_setup():
    st.header("⚙️ Configuração Inicial")
    st.write("Preencha os dados da sua empresa para que as propostas sejam geradas automaticamente.")

    with st.form("company_form"):
        c1, c2 = st.columns(2)
        with c1:
            razao = st.text_input("Razão Social", value=CompanyService.get_company_data().razao_social)
            cnpj = st.text_input("CNPJ", value=CompanyService.get_company_data().cnpj)
            endereco = st.text_area("Endereço", value=CompanyService.get_company_data().endereco)
        with c2:
            porte = st.selectbox("Porte da Empresa", ["ME", "EPP", "MEI"],
                               index=0 if CompanyService.get_company_data().porte == "ME" else 1 if CompanyService.get_company_data().porte == "EPP" else 2)
            email = st.text_input("E-mail", value=CompanyService.get_company_data().email)
            tel = st.text_input("Telefone", value=CompanyService.get_company_data().telefone)
            banco = st.text_input("Dados Bancários", value=CompanyService.get_company_data().dados_bancarios)

        if st.form_submit_button("SALVAR E COMEÇAR →"):
            CompanyService.update_company_data({
                "razao_social": razao,
                "cnpj": cnpj,
                "endereco": endereco,
                "porte": porte,
                "email": email,
                "telefone": tel,
                "dados_bancarios": banco
            })
            st.success("Dados salvos com sucesso!")
            st.session_state.page = "edital"
            st.rerun()

def page_edital():
    render_edital_page(on_done=lambda: _ir_para("proposta"))

def page_proposta():
    render_proposta_page()

    # Botão de navegação para a próxima tela
    st.divider()
    if st.button("PRÓXIMO PASSO: CONCORRENTES →", type="primary"):
        _ir_para("concorrentes")

def page_concorrentes():
    st.header("👥 Passo 3: Concorrentes")

    # Obter o ID da licitação atual
    tender_id = st.session_state.get("current_tender_id") or st.session_state.get("tender_id")
    if not tender_id:
        st.warning("Por favor, analise um edital primeiro.")
        return

    # --- Formulário para adicionar concorrente ---
    with st.expander("➕ Adicionar Novo Concorrente", expanded=True):
        with st.form("add_competitor_form", clear_on_submit=True):
            name = st.text_input("Nome da Empresa")
            uploaded_files = st.file_uploader("Arquivos do concorrente", accept_multiple_files=True)
            submit = st.form_submit_button("SALVAR CONCORRENTE")

            if submit and name:
                from licitacoes.services.persistence import create_competitor, add_competitor_file
                from licitacoes.config import DATA_DIR

                # 1. Salva o concorrente no banco
                comp_id = create_competitor(tender_id, name)

                # 2. Salva os arquivos no disco
                if uploaded_files:
                    storage_path = DATA_DIR / "competitors" / str(tender_id) / str(comp_id)
                    storage_path.mkdir(parents=True, exist_ok=True)

                    for uploaded_file in uploaded_files:
                        file_path = storage_path / uploaded_file.name
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getvalue())
                        # Registra o caminho no banco
                        add_competitor_file(comp_id, uploaded_file.name, str(file_path))

                st.success(f"Concorrente {name} adicionado com sucesso!")
                st.rerun()
            elif submit and not name:
                st.error("O nome da empresa é obrigatório.")

    st.divider()

    # --- Lista de Concorrentes Adicionados ---
    st.write("### Licitantes Adicionados")
    from licitacoes.services.persistence import list_competitors, delete_competitor
    competitors = list_competitors(tender_id)

    if not competitors:
        st.info("Nenhum concorrente adicionado ainda.")
    else:
        for comp in competitors:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{comp['name']}**")
            with col2:
                if st.button("🗑️", key=f"del_comp_{comp['id']}"):
                    delete_competitor(comp['id'])
                    st.rerun()

    # Botão de navegação para a próxima tela
    st.divider()
    if competitors:
        if st.button("PRÓXIMO PASSO: RESULTADO →", type="primary"):
            _ir_para("resultado")
    else:
        st.info("Adicione ao menos um concorrente para prosseguir para a análise de resultados.")

def page_resultado():
    st.header("🏁 Passo 4: Resultado")

    # Obter o ID da licitação atual
    tender_id = st.session_state.get("current_tender_id") or st.session_state.get("tender_id")
    if not tender_id:
        st.warning("Por favor, analise um edital primeiro.")
        return

    # Buscar concorrentes reais do banco
    from licitacoes.services.persistence import list_competitors
    competitors = list_competitors(tender_id)

    if not competitors:
        st.info("Nenhum concorrente adicionado para análise.")
        return

    # Criar lista de nomes para o selectbox
    competitor_names = [comp["name"] for comp in competitors]

    # Usando a chave do concorrente para evitar a persistência visual do erro
    concorrente_name = st.selectbox(
        "Escolha o licitante para análise",
        ["Nenhum"] + competitor_names,
        key=f"sel_comp_{tender_id}"
    )

    if concorrente_name != "Nenhum":
        # Identificar o ID do concorrente selecionado
        comp_id = next(c["id"] for c in competitors if c["name"] == concorrente_name)

        with st.spinner(f"Analisando documentos e preços de {concorrente_name}..."):
            from licitacoes.services.competitor_analysis import CompetitorAnalysisService
            achados = CompetitorAnalysisService.analyze_competitor(comp_id, tender_id)

        if not achados:
            st.success(f"✅ {concorrente_name} parece estar em conformidade.")
        else:
            for achado in achados:
                if achado["type"] == "error":
                    st.error(f"🔴 {achado['msg']}")
                else:
                    st.warning(f"⚠️ {achado['msg']}")

            st.divider()
            st.button("Confirmar Achados")
            st.button("Descartar")

    st.divider()
    if st.button("PRÓXIMO PASSO: COMPARATIVO →", type="primary"):
        _ir_para("comparativo")

def page_comparativo():
    st.header("📊 Passo 5: Comparativo de Preços")

    tender_id = st.session_state.get("current_tender_id") or st.session_state.get("tender_id")
    if not tender_id:
        st.warning("Por favor, analise um edital primeiro.")
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

    # Coletar preços reais dos concorrentes
    comp_prices = {}
    for comp in competitors:
        props = get_competitor_proposal(comp["id"])
        # Mapeia item_number -> proposed_cents
        comp_prices[comp["id"]] = {p["item_number"]: p["proposed_cents"] for p in props}

    # Preparar dados para a tabela
    table_data = []
    for it in items:
        row = {
            "Item": it["number"],
            "Descrição": it["description"][:50] + "..." if len(it["description"]) > 50 else it["description"],
            "Minha Empresa": it["proposed_cents"] or 0,
        }

        all_prices = [it["proposed_cents"] or 0]

        for comp in competitors:
            price = comp_prices[comp["id"]].get(it["number"], 0)
            row[comp["name"]] = price
            all_prices.append(price)

        # Identificar Vencedor (Menor Preço > 0)
        valid_prices = [p for p in all_prices if p > 0]
        if not valid_prices:
            winner = "N/A"
        else:
            min_price = min(valid_prices)
            if min_price == (it["proposed_cents"] or 0):
                winner = "🌟 Minha Empresa"
            else:
                winner = "Minha Empresa"
                for comp in competitors:
                    if comp_prices[comp["id"]].get(it["number"]) == min_price:
                        winner = f"🏆 {comp['name']}"
                        break

        row["Vencedor"] = winner
        table_data.append(row)

    df_comp = pd.DataFrame(table_data)

    # Formatação para exibição
    display_df = df_comp.copy()
    for col in df_comp.columns:
        if col not in ["Item", "Descrição", "Vencedor"]:
            display_df[col] = display_df[col].apply(lambda x: format_brl(int(x)) if x else "—")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    st.info("💡 Os preços exibidos são aqueles extraídos automaticamente dos arquivos dos concorrentes.")

def page_history():
    st.header("📁 Minhas Licitações")
    st.info("Aqui você encontrará todas as licitações analisadas e arquivadas.")

    # This will be fully implemented as part of Entrega 1 (Persistence)
    # For now, we provide a real functional shell instead of "Page under construction"
    tenders = [] # This will come from SQLite later
    if not tenders:
        st.write("Nenhuma licitação encontrada no banco de dados.")
    else:
        # Logic to list, open, and archive
        pass

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
else:
    st.write("Página não encontrada.")
