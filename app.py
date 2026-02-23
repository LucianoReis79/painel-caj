import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")

# =========================================
# BOTÃO ATUALIZAR
# =========================================
if st.button("Atualizar Dados"):
    st.cache_data.clear()
    st.rerun()

# =========================================
# CARREGAR DICIONÁRIO (XLSX)
# =========================================
@st.cache_data
def carregar_padronizacao():
    df_map = pd.read_excel("Tabela_Dicionario.xlsx")
    df_map.columns = df_map.columns.str.strip()

    col_antigo = df_map.columns[0]
    col_novo = df_map.columns[1]

    df_map[col_antigo] = df_map[col_antigo].astype(str).str.strip().str.upper()
    df_map[col_novo] = df_map[col_novo].astype(str).str.strip().str.upper()

    return dict(zip(df_map[col_antigo], df_map[col_novo]))

# mapa_medicamentos = carregar_padronizacao()
try:
    mapa_medicamentos = carregar_padronizacao()
except Exception as e:
    st.error(f"Erro no dicionário: {e}")
    mapa_medicamentos = {}

# =========================================
# FUNÇÃO LEITURA SEGURA CSV
# =========================================

# Escolher colunas carregada

COLUNAS_PACIENTES = [
    "Número do processo ",
    "Data Entrada ",
    "Interessado ",
    "Medicamento ",
    "Unidade Dispensadora ",
    "Status ",
    "Tipo Ação ",
    "Quantidade Autorizada ",
    "Frequência (em dias) ,
    "Período de tratamento (em meses) ",
    "Data Primeiro Atendimento "
]


def ler_csv_seguro(caminho, colunas=None):
    try:
        return pd.read_csv(
            caminho,
            sep=";",
            encoding="utf-8",
            engine="python",
            on_bad_lines="skip",
            usecols=colunas
        )
    except:
        return pd.read_csv(
            caminho,
            sep=";",
            encoding="latin1",
            engine="python",
            on_bad_lines="skip",
            usecols=colunas
        )
        
# =========================================
# CORRIGIR ACENTOS
# =========================================
def corrigir_acentos(df):
    substituicoes = {
        "Ã§": "ç",
        "Ã£": "ã",
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã": "à",
        "Âº": "º",
        "Âª": "ª",
        "NÂº": "Nº"
    }

    for col in df.select_dtypes(include="object").columns:
        for errado, correto in substituicoes.items():
            df[col] = df[col].str.replace(errado, correto, regex=False)

    return df

# =========================================
# CARREGAR PACIENTES
# =========================================
@st.cache_data
def carregar_pacientes():

    pasta = "Cadastro_de_pacientes"

    if not os.path.exists(pasta):
        st.error(f"Pasta '{pasta}' não encontrada no projeto.")
        st.stop()

    arquivos = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if f.lower().endswith(".csv")
    ]

    if not arquivos:
        st.error("Nenhum arquivo CSV encontrado na pasta.")
        st.stop()

    dfs = []

    for arq in arquivos:
        try:
            df_temp = ler_csv_seguro(arq, COLUNAS_PACIENTES)
            dfs.append(df_temp)
        except Exception as e:
            st.error(f"Erro ao ler {arq}: {e}")
            st.stop()

    df_final = pd.concat(dfs, ignore_index=True)
    # df_final = corrigir_acentos(df_final)

    return df_final


# df = carregar_pacientes()
try:
    df = carregar_pacientes()
except Exception as e:
    st.error(f"Erro nos pacientes: {e}")
    st.stop()

# =========================================
# LIMPEZA PACIENTES
# =========================================
df.columns = df.columns.str.strip()

for col in df.select_dtypes(include="object").columns:
    df[col] = df[col].str.strip()

if "Interessado" in df.columns:
    df = df[
        (df["Interessado"] != "") &
        (df["Interessado"].str.lower() != "nan") &
        (df["Interessado"].str.lower() != "none")
    ]

if "Medicamento" in df.columns:
    df["Medicamento"] = (
        df["Medicamento"]
        .str.upper()
        .replace(mapa_medicamentos)
    )

palavras_excluir = [
    "ALIMENTO", "DIETA", "LEITE", "MODULO", "ESPESSANTE",
    "GLUTAMINA", "FORMULA", "SUPLEMENTO", "FRESUBIN",
    "NOVAMIL", "ISOSOURCE", "PEPTAMEN", "FORMULA INFANTIL",
    "NUTREN", "MODULEN", "NUTRISON"
]

padrao = "|".join(palavras_excluir)

if "Medicamento" in df.columns:
    df = df[~df["Medicamento"].str.contains(padrao, na=False)]

mapa_colunas = {
    "Frequencia (em dias)": "Frequência (em dias)",
    "Frequência(em dias)": "Frequência (em dias)",
    "QuantidadeAutorizada": "Quantidade Autorizada"
}

df.rename(columns=mapa_colunas, inplace=True)

if "Quantidade Autorizada" in df.columns:
    df["Quantidade Autorizada"] = pd.to_numeric(
        df["Quantidade Autorizada"], errors="coerce"
    )

if "Frequência (em dias)" in df.columns:
    df["Frequência (em dias)"] = pd.to_numeric(
        df["Frequência (em dias)"], errors="coerce"
    )

if (
    "Quantidade Autorizada" in df.columns and
    "Frequência (em dias)" in df.columns
):
    df["Consumo_Mensal_30d"] = (
        df["Quantidade Autorizada"] /
        df["Frequência (em dias)"]
    ) * 30
else:
    df["Consumo_Mensal_30d"] = 0

# =========================================
# NAVEGAÇÃO
# =========================================
pagina = st.sidebar.radio(
    "Navegação",
    ["Lista de Pacientes", "Resumo por Medicamento", "Distribuições"]
)

# =========================================
# FILTROS GLOBAIS
# =========================================
st.sidebar.header("Filtros")

unidades = []
status = []
medicamentos = []
tipo_acao = []

if "Unidade Dispensadora" in df.columns:
    unidades = st.sidebar.multiselect(
        "Unidade Dispensadora",
        sorted(df["Unidade Dispensadora"].dropna().unique())
    )

if "Status" in df.columns:
    status = st.sidebar.multiselect(
        "Status",
        sorted(df["Status"].dropna().unique())
    )

if "Medicamento" in df.columns:
    medicamentos = st.sidebar.multiselect(
        "Medicamento",
        sorted(df["Medicamento"].dropna().unique())
    )

if "Tipo Ação" in df.columns:
    tipo_acao = st.sidebar.multiselect(
        "Tipo de Ação",
        sorted(df["Tipo Ação"].dropna().unique())
    )

df_filtrado = df.copy()

if unidades and "Unidade Dispensadora" in df.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Unidade Dispensadora"].isin(unidades)
    ]

if status and "Status" in df.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Status"].isin(status)
    ]

if medicamentos and "Medicamento" in df.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Medicamento"].isin(medicamentos)
    ]

if tipo_acao and "Tipo Ação" in df.columns:
    df_filtrado = df_filtrado[
        df_filtrado["Tipo Ação"].isin(tipo_acao)
    ]

# =========================================
# PÁGINA 1 - LISTA
# =========================================
if pagina == "Lista de Pacientes":

    st.title("Lista de Pacientes")

    unidade_exibida = ", ".join(unidades) if unidades else "Todas as Unidades"
    st.markdown("### Unidade Selecionada")
    st.info(unidade_exibida)

    col1, col2 = st.columns(2)

    col1.metric(
        "Total Pacientes",
        f"{df_filtrado['Interessado'].nunique():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col2.metric(
        "Total Medicamentos",
        f"{df_filtrado['Medicamento'].nunique():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    st.dataframe(df_filtrado, use_container_width=True)

    csv = df_filtrado.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "Baixar Lista",
        csv,
        "lista_pacientes.csv",
        "text/csv"
    )

# =========================================
# PÁGINA 2 - RESUMO
# =========================================
elif pagina == "Resumo por Medicamento":

    st.title("Resumo por Medicamento")

    unidade_exibida = ", ".join(unidades) if unidades else "Todas as Unidades"
    st.markdown("### Unidade Selecionada")
    st.info(unidade_exibida)

    df_resumo = df_filtrado[df_filtrado["Status"].str.upper() == "ATIVO"]

    resumo = (
        df_resumo
        .groupby("Medicamento")
        .agg(
            Pacientes=("Interessado", "nunique"),
            Quantidade=("Quantidade Autorizada", "sum"),
            Consumo_Mensal=("Consumo_Mensal_30d", "sum")
        )
        .reset_index()
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Total Pacientes",
        f"{resumo['Pacientes'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col2.metric(
        "Total Quantidade",
        f"{resumo['Quantidade'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col3.metric(
        "Total Consumo 30d",
        f"{resumo['Consumo_Mensal'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    st.dataframe(resumo, use_container_width=True)

    csv = resumo.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "Baixar Resumo",
        csv,
        "resumo_medicamentos.csv",
        "text/csv"
    )

# =========================================
# PÁGINA 3 - DISTRIBUIÇÕES
# =========================================
elif pagina == "Distribuições":

    st.title("Painel de Distribuições")

    @st.cache_data
    def carregar_distribuicoes():

        pasta = "Distribuicao"

        if not os.path.exists(pasta):
            st.error(f"Pasta '{pasta}' não encontrada no projeto.")
            st.stop()

        arquivos = [
            os.path.join(pasta, f)
            for f in os.listdir(pasta)
            if f.lower().endswith(".csv")
        ]

        if not arquivos:
            st.error("Nenhum arquivo CSV encontrado na pasta Distribuicao.")
            st.stop()

        dfs = []

        for arq in arquivos:
            try:
                df_temp = ler_csv_seguro(arq)
                dfs.append(df_temp)
            except Exception as e:
                st.error(f"Erro ao ler {arq}: {e}")
                st.stop()

        df_final = pd.concat(dfs, ignore_index=True)
        #df_final = corrigir_acentos(df_final)

        return df_final

    df_d = carregar_distribuicoes()

    df_d.columns = df_d.columns.str.strip()

    for col in df_d.select_dtypes(include="object").columns:
        df_d[col] = df_d[col].str.strip()

    if "Medicamento" in df_d.columns:
        df_d["Medicamento"] = (
            df_d["Medicamento"]
            .str.upper()
            .replace(mapa_medicamentos)
        )

    if "Quantidade" in df_d.columns:
        df_d["Quantidade"] = pd.to_numeric(df_d["Quantidade"], errors="coerce")

    if "Valor Total R$" in df_d.columns:
        df_d["Valor Total R$"] = (
            df_d["Valor Total R$"]
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df_d["Valor Total R$"] = pd.to_numeric(df_d["Valor Total R$"], errors="coerce")

    if "Data Distribuição" in df_d.columns:
        df_d["Data Distribuição"] = pd.to_datetime(
            df_d["Data Distribuição"],
            dayfirst=True,
            errors="coerce"
        )

    st.sidebar.subheader("Filtros Distribuição")

    unidades_dist = []
    medicamentos_dist = []

    if "Unidade Saúde Destino" in df_d.columns:
        unidades_dist = st.sidebar.multiselect(
            "Unidade Saúde Destino",
            sorted(df_d["Unidade Saúde Destino"].dropna().unique())
        )

    if "Medicamento" in df_d.columns:
        medicamentos_dist = st.sidebar.multiselect(
            "Medicamento (Distribuição)",
            sorted(df_d["Medicamento"].dropna().unique())
        )

    periodo = st.sidebar.date_input("Período", [])

    df_d_filtrado = df_d.copy()

    if unidades_dist:
        df_d_filtrado = df_d_filtrado[
            df_d_filtrado["Unidade Saúde Destino"].isin(unidades_dist)
        ]

    if medicamentos_dist:
        df_d_filtrado = df_d_filtrado[
            df_d_filtrado["Medicamento"].isin(medicamentos_dist)
        ]

    if len(periodo) == 2 and "Data Distribuição" in df_d_filtrado.columns:
        df_d_filtrado = df_d_filtrado[
            (df_d_filtrado["Data Distribuição"] >= pd.to_datetime(periodo[0])) &
            (df_d_filtrado["Data Distribuição"] <= pd.to_datetime(periodo[1]))
        ]

    if "Unidade Saúde Origem" in df_d_filtrado.columns:
        df_d_filtrado = df_d_filtrado.drop(columns=["Unidade Saúde Origem"])

    total_valor = df_d_filtrado["Valor Total R$"].sum() if "Valor Total R$" in df_d_filtrado.columns else 0
    total_distrib = df_d_filtrado["Nº Distribuição"].nunique() if "Nº Distribuição" in df_d_filtrado.columns else 0
    total_qtd = df_d_filtrado["Quantidade"].sum() if "Quantidade" in df_d_filtrado.columns else 0

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Valor Total Distribuído (R$)",
        f"{total_valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col2.metric(
        "Número de Distribuições",
        f"{total_distrib:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    col3.metric(
        "Quantidade Total Distribuída",
        f"{total_qtd:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )

    unidade_exibida = ", ".join(unidades_dist) if unidades_dist else "Todas as Unidades"
    st.markdown("### Unidade Selecionada")
    st.info(unidade_exibida)

    if "Data Distribuição" in df_d_filtrado.columns:
        df_d_filtrado["Data Distribuição"] = df_d_filtrado["Data Distribuição"].dt.strftime("%d/%m/%Y")

    st.dataframe(df_d_filtrado, use_container_width=True, hide_index=True)

    csv = df_d_filtrado.to_csv(index=False, sep=";", encoding="latin1")
    st.download_button(
        "Baixar Distribuições",
        csv,
        "distribuicoes.csv",
        "text/csv"
    )