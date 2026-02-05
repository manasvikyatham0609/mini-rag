import streamlit as st
import time
from ingest_data import *

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Mini RAG",
    page_icon="📄",
    layout="wide"
)

# ---------------- CSS ----------------
st.markdown("""
<style>
.stApp {
    background: #f5f7fa;
}

.stButton>button {
    border-radius: 8px;
    font-weight: 600;
}

.status-ok {
    color: #15803d;
    font-weight: bold;
}

.status-no {
    color: #b91c1c;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# ---------------- TITLE ----------------
st.title("📄 Mini RAG – AI Document Q&A")
st.caption("Upload documents, ask questions, and receive verified answers with citations.")

st.write("")

# =========================================================
# SECTION 1 — DOCUMENT INPUT
# =========================================================
st.subheader("Add Document")

col1, col2 = st.columns(2)

with col1:
    file = st.file_uploader("Upload PDF", type="pdf")

with col2:
    text_input = st.text_area("Or paste text here")

col3, col4 = st.columns(2)

with col3:
    if st.button("Sync Database"):
        if file or text_input:
            with st.spinner("Processing..."):
                content = extract_text_from_pdf(file) if file else text_input
                name = file.name if file else "Manual_Text"
                chunks = process_text(content)
                ingest_chunks(chunks, name)
                st.success(f"{len(chunks)} chunks indexed successfully.")
        else:
            st.error("Provide a PDF or paste text.")

with col4:
    if st.button("Clear Database"):
        clear_index()
        st.warning("Vector database cleared.")

st.divider()

# =========================================================
# SECTION 2 — QUERY + RESPONSE (NO SCROLL)
# =========================================================
st.subheader("Ask a Question")

query = st.text_input("Enter your question")

# Placeholder so response appears here
response_container = st.empty()

if query:
    start = time.time()

    with response_container.container():
        with st.spinner("Searching & Generating Answer..."):
            answer, tokens = get_answer_with_rerank(query)
        latency = round(time.time() - start, 2)

        st.subheader("Response")

        if "VERIFIED" in answer:
            st.markdown("<p class='status-ok'>STATUS: VERIFIED</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p class='status-no'>STATUS: NOT FOUND</p>", unsafe_allow_html=True)

        st.write(answer)

        col1, col2 = st.columns(2)
        col1.metric("Latency", f"{latency}s")
        col2.metric("Tokens Used", tokens)

else:
    response_container.info("Upload a document and ask a question to begin.")
