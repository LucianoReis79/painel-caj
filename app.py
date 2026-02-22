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

mapa_medicamentos = carregar_padronizacao()

# =========================================
# CARREGAR PACIENTES
# =========================================
@st.cache_data
def carregar_pacientes():

    pasta = r"C:\Users\lucia\Cia de Processamento de Dados do Estado da Bahia\Coordenação de Ação Judicial - Cadastro de pacientes"

    arquivos = [
        os.path.join(pasta, f)
        for f in os.listdir(pasta)
        if f.lower().endswith(".csv")
    ]

    dfs = []

    for arq in arquivos:
        df_temp = pd.read_csv(
            arq,
            sep=";",
            encoding="latin1",
            engine="python",
            on_bad_lines="skip"
        )
        dfs.append(df_temp)

    return pd.concat(dfs, ignore_index=True)

df = carregar_pacientes()

# =========================================
# LIMPEZA PACIENTES
# =========================================
df.columns = df.columns.str.strip()

for col in df.columns:
    df[col] = df[col].astype(str).str.strip()

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
    "ALIMENTO","DIETA","LEITE","MODULO","ESPESSANTE",
    "GLUTAMINA","FORMULA","SUPLEMENTO","FRESUBIN",
    "NOVAMIL","ISOSOURCE","PEPTAMEN","FORMULA INFANTIL",
    "NUTREN","MODULEN","NUTRISON"
]

padrao = "|".join(palavras_excluir)
df = df[~df["Medicamento"].str.contains(padrao, na=False)]

df["Quantidade Autorizada"] = pd.to_numeric(df["Quantidade Autorizada"], errors="coerce")
df["Frequência (em dias)"] = pd.to_numeric(df["Frequência (em dias)"], errors="coerce")

df["Consumo_Mensal_30d"] = (
    df["Quantidade Autorizada"] / df["Frequência (em dias)"]
) * 30

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

unidades = st.sidebar.multiselect(
    "Unidade Dispensadora",
    sorted(df["Unidade Dispensadora"].unique())
)

status = st.sidebar.multiselect(
    "Status",
    sorted(df["Status"].unique())
)

medicamentos = st.sidebar.multiselect(
    "Medicamento",
    sorted(df["Medicamento"].unique())
)

tipo_acao = st.sidebar.multiselect(
    "Tipo de Ação",
    sorted(df["Tipo Ação"].unique())
)

df_filtrado = df.copy()

if unidades:
    df_filtrado = df_filtrado[df_filtrado["Unidade Dispensadora"].isin(unidades)]

if status:
    df_filtrado = df_filtrado[df_filtrado["Status"].isin(status)]

if medicamentos:
    df_filtrado = df_filtrado[df_filtrado["Medicamento"].isin(medicamentos)]

if tipo_acao:
    df_filtrado = df_filtrado[df_filtrado["Tipo Ação"].isin(tipo_acao)]

# =========================================
# PÁGINA 1 - LISTA
# =========================================
if pagina == "Lista de Pacientes":

    st.title("Lista de Pacientes")

    unidade_exibida = ", ".join(unidades) if unidades else "Todas as Unidades"
    st.markdown("### Unidade Selecionada")
    st.info(unidade_exibida)

    col1, col2 = st.columns(2)
    col1.metric("Total Pacientes", df_filtrado["Interessado"].nunique())
    col2.metric("Total Medicamentos", df_filtrado["Medicamento"].nunique())

    st.dataframe(df_filtrado, use_container_width=True)

    csv = df_filtrado.to_csv(index=False, sep=";", encoding="latin1")
    st.download_button("Baixar Lista", csv,
                       "lista_pacientes.csv", "text/csv")

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
            Pacientes=("Interessado","nunique"),
            Quantidade=("Quantidade Autorizada","sum"),
            Consumo_Mensal=("Consumo_Mensal_30d","sum")
        )
        .reset_index()
    )

    col1,col2,col3 = st.columns(3)
    col1.metric("Total Pacientes", resumo["Pacientes"].sum())
    col2.metric("Total Quantidade", round(resumo["Quantidade"].sum(),2))
    col3.metric("Total Consumo 30d", round(resumo["Consumo_Mensal"].sum(),2))

    st.dataframe(resumo, use_container_width=True)

    csv = resumo.to_csv(index=False, sep=";", encoding="latin1")
    st.download_button("Baixar Resumo", csv,
                       "resumo_medicamentos.csv","text/csv")

# =========================================
# PÁGINA 3 - DISTRIBUIÇÕES
# =========================================
elif pagina == "Distribuições":

    st.title("Painel de Distribuições")

    @st.cache_data
    def carregar_distribuicoes():

        pasta = r"C:\Users\lucia\Cia de Processamento de Dados do Estado da Bahia\Coordenação de Ação Judicial - Distribuição"

        arquivos = [
            os.path.join(pasta,f)
            for f in os.listdir(pasta)
            if f.lower().endswith(".csv")
        ]

        dfs = []

        for arq in arquivos:
            df_temp = pd.read_csv(
                arq,
                sep=";",
                encoding="latin1",
                engine="python",
                on_bad_lines="skip"
            )
            dfs.append(df_temp)

        return pd.concat(dfs, ignore_index=True)

    df_d = carregar_distribuicoes()

    df_d.columns = df_d.columns.str.strip()

    for col in df_d.columns:
        df_d[col] = df_d[col].astype(str).str.strip()

    if "Medicamento" in df_d.columns:
        df_d["Medicamento"] = (
            df_d["Medicamento"]
            .str.upper()
            .replace(mapa_medicamentos)
        )

    df_d["Quantidade"] = pd.to_numeric(df_d["Quantidade"], errors="coerce")

    df_d["Valor Total R$"] = (
        df_d["Valor Total R$"]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df_d["Valor Total R$"] = pd.to_numeric(df_d["Valor Total R$"], errors="coerce")

    df_d["Data Distribuição"] = pd.to_datetime(
        df_d["Data Distribuição"], dayfirst=True, errors="coerce"
    )

    st.sidebar.subheader("Filtros Distribuição")

    unidades_dist = st.sidebar.multiselect(
        "Unidade Saúde Destino",
        sorted(df_d["Unidade Saúde Destino"].dropna().unique())
    )

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

    if len(periodo) == 2:
        df_d_filtrado = df_d_filtrado[
            (df_d_filtrado["Data Distribuição"] >= pd.to_datetime(periodo[0])) &
            (df_d_filtrado["Data Distribuição"] <= pd.to_datetime(periodo[1]))
        ]

    if "Unidade Saúde Origem" in df_d_filtrado.columns:
        df_d_filtrado = df_d_filtrado.drop(columns=["Unidade Saúde Origem"])

    total_valor = df_d_filtrado["Valor Total R$"].sum()
    total_distrib = df_d_filtrado["Nº Distribuição"].nunique()
    total_qtd = df_d_filtrado["Quantidade"].sum()

    col1,col2,col3 = st.columns(3)
    col1.metric("Valor Total Distribuído (R$)", round(total_valor,2))
    col2.metric("Número de Distribuições", total_distrib)
    col3.metric("Quantidade Total Distribuída", total_qtd)

    unidade_exibida = ", ".join(unidades_dist) if unidades_dist else "Todas as Unidades"
    st.markdown("### Unidade Selecionada")
    st.info(unidade_exibida)

    df_d_filtrado["Data Distribuição"] = df_d_filtrado["Data Distribuição"].dt.strftime("%d/%m/%Y")

    st.dataframe(df_d_filtrado, use_container_width=True, hide_index=True)

    csv = df_d_filtrado.to_csv(index=False, sep=";", encoding="latin1")
    st.download_button("Baixar Distribuições", csv,
                       "distribuicoes.csv","text/csv")
