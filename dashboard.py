import streamlit as st

st.set_page_config(
    page_title="Energetický dashboard",
    page_icon="📊",
    layout="wide"
)

pg = st.navigation([
    st.Page("pages/1_Elektrina.py", title="Elektřina", icon="⚡"),
    st.Page("pages/2_Plyn.py", title="Plyn", icon="🔥"),
    st.Page("pages/3_SVR_SK.py", title="SVR (SK)", icon="⚖️"),
])
pg.run()
