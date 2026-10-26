# 🇨🇴 Observatorio de Actividad Económica y Social por Departamentos

Esta aplicación web interactiva permite visualizar, analizar y comparar indicadores económicos y sociales clave de Colombia a nivel departamental.

## 📌 Características
- **Datos reales y actualizados:** Conexión directa mediante API con datos del portal oficial `datos.gov.co` (SODA), Ministerio de Defensa y DNP.
- **Gráficos interactivos:** Visualizaciones dinámicas de tendencias históricas y rankings comparativos hechos con Plotly.
- **Filtros personalizados:** Permite filtrar por departamentos, tipo de indicador y rango de años.
- **Optimización de rendimiento:** Uso de caché inteligente (`st.cache_data`) para cargas ultra rápidas sin sobrecargar las fuentes públicas.

## 🚀 Despliegue
La aplicación está desarrollada con Python y construida para ser desplegada en **Streamlit Cloud**.

### Requisitos locales (si deseas ejecutarlo en tu equipo):
```bash
pip install -r requirements.txt
streamlit run app.py
```