import streamlit as st
from pages import dashboard, search

st.set_page_config(page_title="GraphRAG", layout="wide")

st.title("GraphRAG")
tabs = st.tabs(["Dashboard", "Search"])

with tabs[0]:
    dashboard.show()

with tabs[1]:
    search.show()