import pandas as pd
import streamlit as st
from licitacoes.services.persistence import PersistenceService
from licitacoes.edital.deterministic_parser import DeterministicParser
from pathlib import Path

def page_proposta():
    st.header("💰 Passo 2: Minha Proposta")

    tender_id = st.session_state.get("current_tender_id")
    if not tender_id:
        st.error("Nenhum edital selecionado. Volte ao Passo 1.")
        return

    # Load items from SQLite
    items = PersistenceService.get_tender_items(tender_id)
    if not items:
        st.warning("Nenhum item encontrado para esta licitação.")
        return

    # Prepare dataframe for editor
    # item_id is the unique key from edital
    data = []
    for it in items:
        # We'd normally fetch the proposal value from the proposals table
        # For now, we'll use a simplified view
        data.append({
            "Item": it['item_id'],
            "Especificações": it['description'],
            "Unid.": it['unit'],
            "Qtde": it['quantity'],
            "Preço Máx": f"R$ {it['ceiling_price']/100:.2f}",
            "Marca": "", # Placeholder
            "Meu Preço": 0.0
        })

    df = pd.DataFrame(data)
    edited_df = st.data_editor(df, num_rows="fixed", key="proposal_editor")

    # Calculate totals
    total_geral = 0
    for idx, row in edited_df.iterrows():
        # simplified calc for demonstration
        try:
            my_price = float(row["Meu Preço"])
            qty = items[idx]['quantity']
            total_geral += my_price * qty
        except: pass

    st.metric("Total Geral", f"R$ {total_geral:.2f}")
