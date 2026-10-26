import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import unicodedata
import warnings
import streamlit as st

warnings.filterwarnings("ignore")

# Configuración de la página en Streamlit
st.set_page_config(
    page_title="Observatorio Departamental",
    page_icon="🇨🇴",
    layout="wide"
)

# ============================================================
# NORMALIZACIÓN ROBUSTA (mayúsculas + sin tildes)
# ============================================================
def quitar_tildes(texto):
    if pd.isna(texto) or texto is None:
        return ""
    t = str(texto).strip().lower()
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = t.replace(",", "").replace(".", " ").replace("  ", " ").strip()
    return t

DEPARTAMENTOS_CANONICOS = {
    "amazonas": "Amazonas",
    "antioquia": "Antioquia",
    "arauca": "Arauca",
    "atlantico": "Atlántico",
    "bogota": "Bogotá D.C.",
    "bogota d c": "Bogotá D.C.",
    "bogota dc": "Bogotá D.C.",
    "bogota d c ": "Bogotá D.C.",
    "bolivar": "Bolívar",
    "boyaca": "Boyacá",
    "caldas": "Caldas",
    "caqueta": "Caquetá",
    "casanare": "Casanare",
    "cauca": "Cauca",
    "cesar": "Cesar",
    "choco": "Chocó",
    "cordoba": "Córdoba",
    "cundinamarca": "Cundinamarca",
    "guainia": "Guainía",
    "guaviare": "Guaviare",
    "huila": "Huila",
    "la guajira": "La Guajira",
    "magdalena": "Magdalena",
    "meta": "Meta",
    "narino": "Nariño",
    "norte de santander": "Norte de Santander",
    "putumayo": "Putumayo",
    "quindio": "Quindío",
    "risaralda": "Risaralda",
    "san andres": "San Andrés y Providencia",
    "san andres y providencia": "San Andrés y Providencia",
    "archipielago de san andres": "San Andrés y Providencia",
    "santander": "Santander",
    "sucre": "Sucre",
    "tolima": "Tolima",
    "valle": "Valle del Cauca",
    "valle del cauca": "Valle del Cauca",
    "vaupes": "Vaupés",
    "vichada": "Vichada",
}

def normalizar_departamento(nombre):
    clave = quitar_tildes(nombre)
    return DEPARTAMENTOS_CANONICOS.get(clave, str(nombre).strip().title() if nombre else None)

# ============================================================
# CARGA DE DATOS (Con Caché para optimizar Streamlit Cloud)
# ============================================================
@st.cache_data(ttl=86400)
def cargar_pib():
    try:
        url = "https://www.datos.gov.co/resource/kgyi-qc7j.json?$limit=50000&$order=a_o DESC"
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        df = pd.DataFrame(r.json())

        df["anio"] = pd.to_numeric(df["a_o"], errors="coerce")
        df["valor"] = pd.to_numeric(df["valor_miles_de_millones_de"], errors="coerce")
        df["departamento"] = df["departamento"].apply(normalizar_departamento)

        df = df[df["tipo_de_precios"].str.contains("constantes", case=False, na=False)]

        agg = (
            df.groupby(["departamento", "anio"], as_index=False)["valor"]
            .sum()
            .dropna()
        )
        agg["indicador"] = "PIB (miles de millones, constantes 2015)"
        agg["fuente"] = "datos.gov.co/kgyi-qc7j"
        return agg
    except Exception as e:
        st.error(f"Error cargando PIB: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def cargar_homicidios():
    try:
        url = "https://www.datos.gov.co/resource/m8fd-ahd9.json?$limit=150000"
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        df = pd.DataFrame(r.json())

        df["fecha"] = pd.to_datetime(df["fecha_hecho"], errors="coerce")
        df["anio"] = df["fecha"].dt.year
        df["departamento"] = df["departamento"].apply(normalizar_departamento)
        df["cantidad"] = pd.to_numeric(df.get("cantidad"), errors="coerce").fillna(1)

        agg = (
            df.groupby(["departamento", "anio"], as_index=False)["cantidad"]
            .sum()
            .rename(columns={"cantidad": "valor"})
            .dropna()
        )
        agg["indicador"] = "Homicidios (víctimas)"
        agg["fuente"] = "MinDefensa/m8fd-ahd9"
        return agg
    except Exception as e:
        st.error(f"Error cargando Homicidios: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def cargar_dnp():
    try:
        url = "https://www.datos.gov.co/resource/wc86-9j4a.json?$limit=80000"
        r = requests.get(url, timeout=90)
        r.raise_for_status()
        df = pd.DataFrame(r.json())

        df["departamento"] = df["departamento"].apply(normalizar_departamento)
        df["anio"] = pd.to_numeric(df.get("vigencia"), errors="coerce")
        valor_col = next((c for c in ["valorpagado", "valorobligado", "valorcomprometido"] if c in df.columns), None)
        if not valor_col:
            return pd.DataFrame()
        df["valor"] = pd.to_numeric(df[valor_col], errors="coerce")

        agg = df.groupby(["departamento", "anio"], as_index=False)["valor"].sum().dropna()
        agg["indicador"] = "Recursos públicos DNP (COP)"
        agg["fuente"] = "DNP/wc86-9j4a"
        return agg
    except Exception as e:
        st.error(f"Error cargando DNP: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def construir_maestro():
    partes = []
    for fn in [cargar_pib, cargar_homicidios, cargar_dnp]:
        d = fn()
        if not d.empty:
            partes.append(d)
    if not partes:
        return pd.DataFrame(columns=["departamento", "anio", "valor", "indicador", "fuente"])
    maestro = pd.concat(partes, ignore_index=True)
    maestro["anio"] = maestro["anio"].astype(int)
    return maestro.sort_values(["indicador", "departamento", "anio"]).reset_index(drop=True)

# Mensaje mientras descarga de las APIs de datos.gov.co
with st.spinner("Descargando e integrando datos oficiales de Colombia..."):
    DF = construir_maestro()

# ============================================================
# FUNCIONES DE ANÁLISIS Y FILTRADO
# ============================================================
def filtrar(df, deptos, indicador, anio_min, anio_max):
    d = df.copy()
    if deptos and "Todos" not in deptos:
        d = d[d["departamento"].isin(deptos)]
    if indicador and indicador != "Todos":
        d = d[d["indicador"] == indicador]
    d = d[(d["anio"] >= anio_min) & (d["anio"] <= anio_max)]
    return d

def stats(df, deptos, indicador, anio_min, anio_max):
    if df.empty:
        return None
    d = filtrar(df, deptos, indicador, anio_min, anio_max)
    if d.empty:
        return None
    res = d.groupby("indicador")["valor"].agg(
        media="mean", mediana="median", std="std", min="min", max="max", n="count"
    ).round(2).reset_index()
    return res

def tendencia(df, deptos, indicador, anio_min, anio_max):
    d = filtrar(df, deptos, indicador, anio_min, anio_max)
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sin datos disponibles", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    fig = px.line(d, x="anio", y="valor", color="departamento", markers=True,
                  title=f"Tendencia – {indicador}", template="plotly_white")
    fig.update_layout(hovermode="x unified")
    return fig

def barras(df, indicador, anio):
    d = df[(df["indicador"] == indicador) & (df["anio"] == anio)]
    if d.empty:
        fig = go.Figure()
        fig.add_annotation(text="Sin datos disponibles para este año e indicador", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig
    d = d.nlargest(15, "valor")
    fig = px.bar(d, x="valor", y="departamento", orientation="h",
                 title=f"Top 15 – {indicador} ({anio})", template="plotly_white",
                 color="valor", color_continuous_scale="Blues")
    fig.update_layout(yaxis={"categoryorder": "total ascending"})
    return fig

# ============================================================
# ESTRUCTURA DE LA INTERFAZ USUARIO
# ============================================================
st.title("🇨🇴 Observatorio de Actividad Económica y Social")
st.caption("Fuentes oficiales: datos.gov.co (SODA), Ministerio de Defensa, DNP.")

if DF.empty:
    st.error("No se pudieron obtener los datos desde los servidores gubernamentales.")
else:
    lista_deptos = sorted(DF["departamento"].dropna().unique())
    lista_inds = sorted(DF["indicador"].unique())
    amin = int(DF["anio"].min())
    amax = int(DF["anio"].max())

    # Controles en el menú lateral
    st.sidebar.header("Filtros de Búsqueda")
    
    depto_sel = st.sidebar.multiselect(
        "Departamento(s)",
        options=["Todos"] + lista_deptos,
        default=["Nariño"] if "Nariño" in lista_deptos else ["Todos"]
    )
    
    ind_sel = st.sidebar.selectbox("Indicador", options=lista_inds, index=0)
    
    s_min, s_max = st.sidebar.slider(
        "Rango de Años para Tendencias",
        min_value=amin,
        max_value=amax,
        value=(amin, amax)
    )
    
    s_mapa = st.sidebar.slider(
        "Año específico para Barras Comparativas",
        min_value=amin,
        max_value=amax,
        value=amax
    )

    # Panel de Resultados
    df_stats = stats(DF, depto_sel, ind_sel, s_min, s_max)
    
    if df_stats is not None:
        st.subheader("Estadísticas Descriptivas")
        st.dataframe(df_stats, use_container_width=True)
    else:
        st.warning("No se encontraron registros con los filtros seleccionados.")

    # Pestañas con los gráficos
    tab1, tab2, tab3 = st.tabs(["📉 Tendencias Históricas", "📊 Top 15 Comparativo", "📋 Tabla de Datos"])

    with tab1:
        fig_t = tendencia(DF, depto_sel, ind_sel, s_min, s_max)
        st.plotly_chart(fig_t, use_container_width=True)

    with tab2:
        fig_b = barras(DF, ind_sel, s_mapa)
        st.plotly_chart(fig_b, use_container_width=True)

    with tab3:
        tabla_df = filtrar(DF, depto_sel, ind_sel, s_min, s_max)
        st.dataframe(tabla_df, use_container_width=True)