import time
import requests
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(
    page_title="ScrapeBot",
    page_icon="",
    layout="wide",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { padding-top: 1rem; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 20px;
        font-weight: 500;
    }

    .chat-user {
        background: #534AB7;
        color: white;
        padding: 10px 16px;
        border-radius: 16px 16px 4px 16px;
        margin: 6px 0;
        margin-left: 20%;
        font-size: 14px;
    }

    .chat-bot {
        background: #F0F0F5;
        color: #1a1a1a;
        padding: 10px 16px;
        border-radius: 16px 16px 16px 4px;
        margin: 6px 0;
        margin-right: 20%;
        font-size: 14px;
    }

    .status-done {
        background: #EAF3DE;
        color: #3B6D11;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 500;
        font-size: 14px;
    }

    .status-running {
        background: #FAEEDA;
        color: #BA7517;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 500;
        font-size: 14px;
    }

    .status-failed {
        background: #FCEBEB;
        color: #A32D2D;
        padding: 8px 14px;
        border-radius: 8px;
        font-weight: 500;
        font-size: 14px;
    }

    .metric-card {
        background: #F7F7FB;
        padding: 20px;
        border-radius: 14px;
        text-align: center;
        border: 1px solid #E5E7EB;
    }

    .metric-number {
        font-size: 28px;
        font-weight: 700;
        color: #534AB7;
    }

    .metric-label {
        font-size: 14px;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("# ScrapeBot")
st.markdown("Scrape websites → build a knowledge base → chat with your data")
st.divider()

# ── Check backend connection ─────────────────────────────────────────────────
try:
    r = requests.get(f"{API}/health", timeout=3)

    if r.status_code == 200:
        st.success("Backend connected at localhost:8000")
    else:
        st.error("Backend returned an error. Make sure it's running.")
        st.stop()

except Exception:
    st.error("Cannot reach backend at localhost:8000. Run: `uvicorn app.main:app --reload --port 8000`")
    st.stop()

# ── Dashboard ────────────────────────────────────────────────────────────────
st.subheader("Dashboard")

try:
    ingested = requests.get(f"{API}/scrape/ingested", timeout=5).json()
    total_urls = len(ingested)
except Exception:
    ingested = []
    total_urls = 0

chat_count = len(st.session_state.get("messages", []))

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{total_urls}</div>
        <div class="metric-label">Ingested URLs</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{chat_count}</div>
        <div class="metric-label">Chat Messages</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    backend_status = "Online" if r.status_code == 200 else "Offline"

    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-number">{backend_status}</div>
        <div class="metric-label">Backend Status</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_scrape, tab_chat, tab_knowledge = st.tabs(
    ["Scrape URLs", "Chat", "Knowledge"]
)

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — SCRAPE
# ════════════════════════════════════════════════════════════════════════════
with tab_scrape:

    st.subheader("Scrape & Ingest Websites")

    st.markdown(
        "Enter one URL per line. The scraper follows internal links up to depth 2."
    )

    urls_input = st.text_area(
        "URLs",
        placeholder="https://en.wikipedia.org/wiki/Python_(programming_language)\nhttps://fastapi.tiangolo.com",
        height=120,
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([3, 1])

    with col2:
        force = st.checkbox("Re-scrape cached", value=False)

    with col1:
        scrape_btn = st.button(
            "Scrape & Ingest",
            type="primary",
            use_container_width=True
        )

    if scrape_btn:

        urls = [u.strip() for u in urls_input.strip().split("\n") if u.strip()]

        if not urls:
            st.warning("Please enter at least one URL.")

        else:
            with st.spinner("Starting scrape job..."):

                try:
                    r = requests.post(
                        f"{API}/scrape/start",
                        json={"urls": urls, "force": force},
                        timeout=10,
                    )

                    d = r.json()

                except Exception as e:
                    st.error(f"Failed to connect to backend: {e}")
                    d = None

            if d:

                if d.get("job_id"):

                    job_id = d["job_id"]

                    st.info(f"Job started! ID: `{job_id}`")

                    progress = st.progress(
                        0,
                        text="Scraping in progress…"
                    )

                    # Poll until done
                    for i in range(60):

                        time.sleep(3)

                        try:
                            sr = requests.get(
                                f"{API}/scrape/status/{job_id}",
                                timeout=5
                            )

                            sd = sr.json()

                        except Exception:
                            continue

                        progress.progress(
                            min((i + 1) / 60, 0.95),
                            text=f"Status: {sd.get('status', '...')}"
                        )

                        if sd["status"] == "done":

                            progress.progress(
                                1.0,
                                text="Done!"
                            )

                            st.markdown(
                                f'<div class="status-done">Scraping complete! {sd.get("ingest_result", "")}</div>',
                                unsafe_allow_html=True
                            )

                            break

                        elif sd["status"] == "failed":

                            progress.empty()

                            st.markdown(
                                f'<div class="status-failed">Failed: {sd.get("error", "Unknown error")[:300]}</div>',
                                unsafe_allow_html=True
                            )

                            break

                    else:
                        st.warning(
                            "Timed out waiting for scrape. Check status manually below."
                        )

                else:
                    st.markdown(
                        f'<div class="status-done">{d.get("message", "")}</div>',
                        unsafe_allow_html=True
                    )

    st.divider()

    # Ingested URLs list
    st.subheader("Ingested URLs")

    if st.button("Refresh List"):
        st.rerun()

    try:
        ingested = requests.get(
            f"{API}/scrape/ingested",
            timeout=5
        ).json()

        if ingested:

            for item in ingested:

                col_url, col_del = st.columns([5, 1])

                with col_url:
                    st.markdown(f"`{item['url']}`")

                with col_del:

                    if st.button(
                        "Delete",
                        key=f"del_{item['url']}"
                    ):

                        requests.delete(
                            f"{API}/scrape/ingested/{requests.utils.quote(item['url'], safe='')}",
                            timeout=5
                        )

                        st.rerun()

        else:
            st.markdown("*No URLs ingested yet.*")

    except Exception:
        st.error("Could not fetch ingested URLs.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — CHAT
# ════════════════════════════════════════════════════════════════════════════
with tab_chat:

    st.subheader("Chat with Your Data")

    # Init chat history
    if "messages" not in st.session_state:

        st.session_state.messages = [
            {
                "role": "bot",
                "content": "Hello! Scrape some URLs first, then ask me anything about that content."
            }
        ]

    language = "en"

    # Display chat history
    chat_container = st.container(height=380)

    with chat_container:

        for msg in st.session_state.messages:

            if msg["role"] == "user":

                st.markdown(
                    f'<div class="chat-user">{msg["content"]}</div>',
                    unsafe_allow_html=True
                )

            else:

                st.markdown(
                    f'<div class="chat-bot">{msg["content"]}</div>',
                    unsafe_allow_html=True
                )

                if msg.get("sources"):
                    st.caption(f"Sources: {', '.join(msg['sources'])}")

    # Input
    col_input, col_send = st.columns([5, 1])

    with col_input:
        user_input = st.chat_input(
            "Ask a question about the scraped content…"
        )

    if user_input:

        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        with st.spinner("Thinking…"):

            try:
                r = requests.post(
                    f"{API}/chat/ask",
                    json={
                        "query": user_input,
                        "language": language
                    },
                    timeout=30,
                )

                d = r.json()

                answer = d.get("answer", "No answer returned.")
                sources = d.get("sources", [])

            except Exception as e:

                answer = f"Error connecting to backend: {e}"
                sources = []

        st.session_state.messages.append({
            "role": "bot",
            "content": answer,
            "sources": sources,
        })

        st.rerun()

    if st.button("Clear Chat"):

        st.session_state.messages = [
            {
                "role": "bot",
                "content": "Chat cleared! Ask me anything about the scraped content."
            }
        ]

        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — KNOWLEDGE
# ════════════════════════════════════════════════════════════════════════════
with tab_knowledge:

    st.subheader("Knowledge Base Tools")

    col1, col2, col3 = st.columns(3)

    with col1:

        if st.button(
            "Generate Summary",
            use_container_width=True
        ):

            with st.spinner("Generating summary…"):

                try:
                    r = requests.get(
                        f"{API}/knowledge/summary",
                        timeout=60
                    )

                    st.session_state["summary"] = r.json().get(
                        "summary",
                        "No summary returned."
                    )

                except Exception as e:
                    st.session_state["summary"] = f"Error: {e}"

    with col2:

        if st.button(
            "Generate FAQs",
            use_container_width=True
        ):

            with st.spinner("Generating FAQs…"):

                try:
                    r = requests.get(
                        f"{API}/knowledge/faqs",
                        timeout=60
                    )

                    st.session_state["faqs"] = r.json().get(
                        "faqs",
                        []
                    )

                except Exception as e:

                    st.session_state["faqs"] = []
                    st.error(f"Error: {e}")

    with col3:

        if st.button(
            "Export Markdown",
            use_container_width=True
        ):

            with st.spinner("Preparing export…"):

                try:
                    r = requests.get(
                        f"{API}/knowledge/export/markdown",
                        timeout=60
                    )

                    st.download_button(
                        label="Download .md file",
                        data=r.text,
                        file_name="knowledge_summary.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )

                except Exception as e:
                    st.error(f"Export failed: {e}")

    st.divider()

    # Show summary
    if "summary" in st.session_state:

        st.markdown("### Summary")
        st.markdown(st.session_state["summary"])

        st.divider()

    # Show FAQs
    if "faqs" in st.session_state:

        faqs = st.session_state["faqs"]

        if faqs:

            st.markdown("### Frequently Asked Questions")

            for i, faq in enumerate(faqs):

                with st.expander(
                    f"Q{i+1}: {faq.get('question', '')}"
                ):

                    st.markdown(
                        faq.get("answer", "")
                    )

        else:
            st.info(
                "No FAQs generated. Make sure you have content ingested first."
            )