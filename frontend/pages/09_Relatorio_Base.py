import sys
import streamlit as st
from datetime import date, timedelta

# Configuração de importação
sys.path.insert(0, "../")

from api.client.relatorio_base_client import download_relatorio_base
from api.client.base import ApiError

st.set_page_config(page_title="Relatório Base", layout="centered")

st.title("📊 Relatório Base")

# Seção de filtros
with st.container():
    col1, col2 = st.columns(2)

    with col1:
        data_ini = st.date_input(
            "De",
            value=date.today().replace(day=1),
            help="Data inicial do período",
            format="DD/MM/YYYY",
        )

    with col2:
        data_fim = st.date_input(
            "Até",
            value=date.today(),
            help="Data final do período",
            format="DD/MM/YYYY",
        )

# Validação de datas
if data_ini > data_fim:
    st.error("⚠️ A data inicial não pode ser posterior à data final.")
    st.stop()

# Botão para gerar relatório
if st.button("🔄 Gerar Relatório", use_container_width=True):
    try:
        with st.spinner("Gerando relatório..."):
            xlsx_bytes = download_relatorio_base(str(data_ini), str(data_fim))

        # Se vazio, mostra aviso
        if xlsx_bytes is None:
            st.warning("⚠️ Nenhum dado encontrado para o período selecionado.")
        else:
            # Mostra botão de download
            st.download_button(
                label="⬇️ Baixar Relatório (XLSX)",
                data=xlsx_bytes,
                file_name=f"relatorio_base_{data_ini}_{data_fim}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
            st.success("✅ Relatório gerado com sucesso!")

    except ApiError as e:
        st.error(f"❌ Erro ao gerar relatório: {e.detail}")
    except Exception as e:
        st.error(f"❌ Erro inesperado: {str(e)}")
