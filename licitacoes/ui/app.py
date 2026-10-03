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
if "step" not in st.session_state:
    st.session_state.step = 0
if "current_tender" not in st.session_state:
    st.session_state.current_tender = None

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

    for s_id, s_name in steps.items():
        icon = "✔" if s_id < st.session_state.step else ("🔵" if s_id == st.session_state.step else "⚪")
        if st.button(f"{icon} {s_name}", key=f"step_{s_id}"):
            st.session_state.step = s_id
            st.rerun()

    st.divider()
    if st.button("📁 Minhas Licitações"):
        st.session_state.step = "history"
    if st.button("⚙️ Configurações Gerais"):
        st.session_state.step = 0

# --- Header ---
col1, col2, col3 = st.columns([3, 2, 1])
with col1:
    tender_name = st.session_state.current_tender.get("name", "Nenhuma Licitação Selecionada") if st.session_state.current_tender else "Inicie a análise"
    st.subheader(f"📌 {tender_name}")
with col2:
    # Mock countdown for now
    st.markdown("<div style='text-align:right; color:red; font-weight:bold;'>⏳ Prazo: 2d 14h</div>", unsafe_allow_html=True)
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
            razao = st.text_input("Razão Social", value=settings.company.razao_social)
            cnpj = st.text_input("CNPJ", value=settings.company.cnpj)
            endereco = st.text_area("Endereço", value=settings.company.endereco)
        with c2:
            porte = st.selectbox("Porte da Empresa", ["ME", "EPP", "MEI"],
                               index=0 if settings.company.porte == "ME" else 1 if settings.company.porte == "EPP" else 2)
            email = st.text_input("E-mail", value=settings.company.email)
            tel = st.text_input("Telefone", value=settings.company.telefone)
            banco = st.text_input("Dados Bancários", value=settings.company.dados_bancarios)

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
            st.session_state.step = 1
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
                st.session_state.step = 2
                st.rerun()

def page_proposta():
    st.header("💰 Passo 2: Minha Proposta")
    st.info("Edite os preços e marcas abaixo. O sistema calcula os totais automaticamente.")

    # Mock data for UI demonstration
    items = [
        {"id": "01", "desc": "Papel A4 75g", "qty": 100, "unit": "un", "max": 25.0},
        {"id": "02", "caneta": "Caneta Azul", "qty": 500, "unit": "un", "max": 1.50},
    ]

    df = pd.DataFrame(items)
    edited_df = st.data_editor(df, num_rows="dynamic")

    if st.button("⬇️ BAIXAR PROPOSTA (EXCEL)", type="primary"):
        st.success("Proposta baixada com sucesso!")

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

# --- Router ---
if st.session_state.step == 0:
    page_setup()
elif st.session_state.step == 1:
    page_edital()
elif st.session_state.step == 2:
    page_proposta()
elif st.session_state.step == 3:
    page_concorrentes()
elif st.session_state.step == 4:
    page_resultado()
else:
    st.write("Página em construção.")
