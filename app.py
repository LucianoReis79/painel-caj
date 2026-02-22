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
# FUNÇÃO LEITURA SEGURA CSV
# =========================================
def ler_csv_seguro(caminho):
    for encoding in ["cp1252", "utf-8", "utf-8-sig", "latin1"]:
        try:
            return pd.read_csv(
                caminho,
                sep=";",
                encoding=encoding,
                engine="python",
                on_bad_lines="skip"
            )
        except Exception:
            continue
    raise ValueError(f"Não foi possível ler o arquivo: {caminho}")

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
            df_temp = ler_csv_seguro(arq)
            dfs.append(df_temp)
        except Exception as e:
            st.error(f"Erro ao ler {arq}: {e}")
            st.stop()

    df_final = pd.concat(dfs, ignore_index=True)
    df_final = corrigir_acentos(df_final)

    return df_final

df = carregar_pacientes()

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
    df["Quantidade Autorizada"] = pd.to_numeric(df["Quantidade Autorizada"], errors="coerce")

if "Frequência (em dias)" in df.columns:
    df["Frequência (em dias)"] = pd.to_numeric(df["Frequência (em dias)"], errors="coerce")

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
# DISTRIBUIÇÕES
# =========================================
if pagina == "Distribuições":

    st.title("Painel de Distribuições")

    @st.cache_data
    def carregar_distribuicoes():

        pasta = "Distribuicao"

        arquivos = [
            os.path.join(pasta, f)
            for f in os.listdir(pasta)
            if f.lower().endswith(".csv")
        ]

        dfs = []

        for arq in arquivos:
            df_temp = ler_csv_seguro(arq)
            dfs.append(df_temp)

        df_final = pd.concat(dfs, ignore_index=True)
        df_final = corrigir_acentos(df_final)

        return df_final

    df_d = carregar_distribuicoes()

    df_d.columns = df_d.columns.str.strip()

    for col in df_d.select_dtypes(include="object").columns:
        df_d[col] = df_d[col].str.strip()

    st.dataframe(df_d, use_container_width=True)
