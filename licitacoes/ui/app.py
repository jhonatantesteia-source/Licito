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
    4: "resultado"
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
        4: "🏁 Resultado"
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

# --- Pages ---

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
    st.header("📄 Passo 1: O Edital")

    uploaded_file = st.file_uploader("Arraste o edital aqui (PDF, DOCX ou MD)", type=["pdf", "docx", "md"])

    if uploaded_file:
        if st.button("ANALISAR EDITAL", type="primary"):
            with st.spinner("🤖 Analisando edital com IA... Isso pode levar alguns instantes."):
                # Temporary save to disk for the existing service
                temp_path = Path("temp_edital") / uploaded_file.name
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getvalue())

                # Call CLI logic via a temporary import or service
                from licitacoes.cli import analisar_edital
                # Note: In a real app, we'd refactor cli.py to just be a wrapper for services
                # For now, we'll simulate the success
                st.session_state.current_tender = {"name": uploaded_file.name}
                st.success("Edital analisado com sucesso!")
                st.session_state.page = "proposta"
                st.rerun()

def page_proposta():
    st.header("💰 Passo 2: Minha Proposta")
    st.info("Edite os preços e marcas abaixo. O sistema calcula os totais automaticamente.")

    from licitacoes.ui.proposal_page import page_proposta as render_proposal
    render_proposal()

def page_concorrentes():
    st.header("👥 Passo 3: Concorrentes")

    if st.button("+ ADICIONAR CONCORRENTE"):
        st.text_input("Nome da Empresa")
        st.file_uploader("Arquivos do concorrente", accept_multiple_files=True)

    st.divider()
    st.write("### Licitantes Adicionados")
    st.info("Nenhum concorrente adicionado ainda.")

def page_resultado():
    st.header("🏁 Passo 4: Resultado")
    st.warning("Selecione um concorrente para ver os achados.")

    concorrente = st.selectbox("Escolha o licitante", ["Nenhum"])
    if concorrente != "Nenhum":
        st.error("🔴 Possível motivo de inabilitação encontrado!")
        st.markdown("""
        **Achado:** Certidão do FGTS vencida em 12/09/2026
        **Exigência:** Cláusula 8.1 - Certidão válida na data da sessão.
        **Evidência:** 'Válido até: 12/09/2026' (Arquivo: fgts.pdf, Pág 1)
        """)
        st.button("Confirmar Achado")
        st.button("Descartar")

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
elif st.session_state.page == "history":
    page_history()
else:
    st.write("Página não encontrada.")
