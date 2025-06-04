import streamlit as st
import pandas as pd

def show():
    st.header("Team Dashboard")

    # Filters
    with st.sidebar:
        st.subheader("Filters")
        sprint = st.selectbox("Sprint", ["Sprint 1", "Sprint 2"])
        team = st.selectbox("Team", ["Team Alpha", "Team Beta"])
        task_view = st.radio("View", ["My Tasks", "Team Tasks"])

    # Sample data
    data = [
        {"ID": "CR-123", "Title": "Fix API", "Status": "In Review", "Owner": "Alice", "Scheduled Date": "2024-06-01"},
        {"ID": "CR-124", "Title": "Migrate DB", "Status": "Pending", "Owner": "Bob", "Scheduled Date": "2024-06-02"},
        {"ID": "CR-125", "Title": "Implement OAuth", "Status": "Approved", "Owner": "Charlie", "Scheduled Date": "2024-06-03"},
    ]

    # Display expandable tiles
    for cr in data:
        with st.expander(f"{cr['ID']} — {cr['Title']}", expanded=False):
            st.markdown(f"**Status:** {cr['Status']}")
            st.markdown(f"**Owner:** {cr['Owner']}")
            st.markdown(f"**Scheduled Date:** {cr['Scheduled Date']}")

            st.subheader("AI Summary")
            st.info(f"This is an AI-generated summary for {cr['ID']}.")

            st.subheader("Linked Content")
            sub_tabs = st.tabs(["Confluence", "Outlook", "JIRA", "CRs"])
            for tab in sub_tabs:
                with tab:
                    st.markdown(f"**Linked items from {tab.label}**")
                    st.write("...")

            st.subheader("Timeline")
            st.write("Timeline for this CR would appear here.")

            st.subheader("Graph View")
            st.write("Graph of linked entities.")