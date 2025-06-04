import streamlit as st

def show():
    st.header("Search")

    col1, col2 = st.columns([4, 1])
    with col1:
        query = st.text_input("Search", placeholder="Enter CR/JIRA/Keyword")
    with col2:
        search_mode = st.selectbox("Search Scope", ["Global", "Team"])

    if query:
        st.subheader("AI Summary")
        st.info(f"This is an AI-generated summary for: {query}")

        st.subheader("Linked Content")
        sub_tabs = st.tabs(["All", "Confluence", "Outlook", "JIRA", "CRs"])
        for sub_tab in sub_tabs:
            with sub_tab:
                st.markdown(f"**Results from {sub_tab.label}**")
                st.write("...")

        st.subheader("Timeline")
        st.write("Interactive timeline would appear here.")

        st.subheader("Graph View")
        st.write("Graph visualization component goes here.")