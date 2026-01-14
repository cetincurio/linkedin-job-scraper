"""Streamlit dashboard for job analytics visualization."""

from __future__ import annotations


def run_dashboard() -> None:
    """Run the Streamlit dashboard."""
    try:
        import streamlit as st
    except ImportError as e:
        msg = "streamlit not installed. Run: uv sync --extra ml"
        raise ImportError(msg) from e

    from linkedin_scraper.config import get_settings
    from linkedin_scraper.ml.export import JobDataExporter
    from linkedin_scraper.ml.vectorstore import JobVectorStore

    st.set_page_config(
        page_title="LinkedIn Job Analytics",
        page_icon="💼",
        layout="wide",
    )

    st.title("💼 LinkedIn Job Analytics Dashboard")

    settings = get_settings()

    # Initialize components
    @st.cache_resource
    def get_exporter():
        return JobDataExporter(settings)

    @st.cache_resource
    def get_vectorstore():
        return JobVectorStore(settings)

    exporter = get_exporter()
    vectorstore = get_vectorstore()

    # Sidebar
    st.sidebar.header("🔧 Actions")

    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_resource.clear()
        st.rerun()

    if st.sidebar.button("📥 Index Jobs"):
        with st.spinner("Indexing jobs..."):
            count = vectorstore.index_jobs()
            st.sidebar.success(f"Indexed {count} new jobs")

    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔍 Search", "📈 Analytics", "📁 Export"])

    with tab1:
        st.header("Dataset Overview")

        try:
            stats = exporter.get_stats()
            vs_stats = vectorstore.get_stats()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Jobs", stats.get("total_jobs", 0))
            col2.metric("Companies", stats.get("unique_companies", 0))
            col3.metric("Locations", stats.get("unique_locations", 0))
            col4.metric("Indexed", vs_stats.get("total_documents", 0))

            # Top skills
            st.subheader("🛠️ Top Skills")
            top_skills = stats.get("top_skills", [])
            if top_skills:
                import polars as pl

                skills_df = pl.DataFrame(
                    {
                        "Skill": [s[0] for s in top_skills],
                        "Count": [s[1] for s in top_skills],
                    }
                )
                st.bar_chart(skills_df.to_pandas().set_index("Skill"))
            else:
                st.info("No skills data available. Export and index jobs first.")

        except Exception as e:
            st.error(f"Error loading stats: {e}")

    with tab2:
        st.header("Semantic Job Search")

        query = st.text_input(
            "🔍 Search Query",
            placeholder="e.g., 'Python machine learning engineer with AWS experience'",
        )
        n_results = st.slider("Number of results", 1, 20, 10)

        if query:
            with st.spinner("Searching..."):
                try:
                    results = vectorstore.search(query, n_results=n_results)
                    if results:
                        for i, r in enumerate(results, 1):
                            with st.expander(
                                f"{i}. {r['metadata'].get('title', 'Unknown')} "
                                f"@ {r['metadata'].get('company_name', 'Unknown')} "
                                f"(Score: {r['score']:.2f})"
                            ):
                                st.write(f"**Job ID:** {r['job_id']}")
                                st.write(f"**Location:** {r['metadata'].get('location', 'N/A')}")
                                st.write(f"**Skills:** {r['metadata'].get('skills', 'N/A')}")
                    else:
                        st.warning("No results found. Try indexing jobs first.")
                except Exception as e:
                    st.error(f"Search error: {e}")

    with tab3:
        st.header("Job Market Analytics")

        try:
            df = exporter.to_polars()
            if df.is_empty():
                st.info("No job data available. Scrape some jobs first.")
            else:
                import polars as pl

                # Company distribution
                st.subheader("🏢 Top Companies")
                company_counts = (
                    df.group_by("company_name").len().sort("len", descending=True).head(10)
                )
                st.bar_chart(company_counts.to_pandas().set_index("company_name"))

                # Location distribution
                st.subheader("📍 Top Locations")
                location_counts = (
                    df.group_by("location").len().sort("len", descending=True).head(10)
                )
                st.bar_chart(location_counts.to_pandas().set_index("location"))

                # Job data table
                st.subheader("📋 Job Data")
                display_cols = ["job_id", "title", "company_name", "location", "skills"]
                st.dataframe(
                    df.select([c for c in display_cols if c in df.columns]).to_pandas(),
                    use_container_width=True,
                )

        except Exception as e:
            st.error(f"Analytics error: {e}")

    with tab4:
        st.header("Export Data")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📄 Export to Parquet")
            if st.button("Export Parquet"):
                with st.spinner("Exporting..."):
                    try:
                        path = exporter.export_parquet()
                        st.success(f"Exported to: {path}")
                    except Exception as e:
                        st.error(f"Export error: {e}")

        with col2:
            st.subheader("📄 Export to JSONL")
            if st.button("Export JSONL"):
                with st.spinner("Exporting..."):
                    try:
                        path = exporter.export_jsonl()
                        st.success(f"Exported to: {path}")
                    except Exception as e:
                        st.error(f"Export error: {e}")

        st.subheader("📄 Export Training Data")
        if st.button("Export for Training"):
            with st.spinner("Exporting..."):
                try:
                    path = vectorstore.export_for_training()
                    st.success(f"Exported to: {path}")
                except Exception as e:
                    st.error(f"Export error: {e}")


if __name__ == "__main__":
    run_dashboard()
