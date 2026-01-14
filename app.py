from typing import List
import streamlit as st
import os
import uuid

# check if it's linux so it works on Streamlit Cloud
if os.name == 'posix':
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from langchain.schema import AIMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import AzureChatOpenAI, ChatOpenAI

from src.core.config import get_settings
from src.core.local_rag import (
    load_doc_to_db,
    load_url_to_db,
    stream_llm_rag_response,
    stream_llm_response,
)
from src.core.openai_utils import get_list_of_models

settings = get_settings()

MODELS: List[str] = []
if settings.LYTIX_JUNIOR_FOUNDRY_KEY is not None:
    MODELS = [
        settings.LYTIX_JUNIOR_FOUNDRY_MODEL,
    ]

st.set_page_config(
    page_title="RAG LLM app?",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- Header ---
st.html("""<h2 style="text-align: center;">📚🔍 <i> Do your LLM even RAG bro? </i> 🤖💬</h2>""")


# --- Initial Setup ---
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "rag_sources" not in st.session_state:
    st.session_state.rag_sources = []

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there! How can I assist you today?"}
]


# --- Side Bar LLM API Tokens ---
with st.sidebar:
    if settings.LYTIX_JUNIOR_FOUNDRY_KEY.get_secret_value() is None:
        st.header("🔑 LLM API Keys")
        azure_openai_api_key = ""
        with st.popover("Set your key"):
            azure_openai_api_key = st.text_input(
                "Introduce your Azure OpenAI API Key (https://platform.openai.com/)",
                value=azure_openai_api_key,
                type="password",
                key="azure_openai_api_key",
            )
    else:
        azure_openai_api_key = settings.LYTIX_JUNIOR_FOUNDRY_KEY.get_secret_value()
st.session_state.az_openai_api_key = azure_openai_api_key

# --- Main Content ---
# Checking if the user has introduced the OpenAI API Key, if not, a warning is displayed
if settings.LYTIX_JUNIOR_FOUNDRY_KEY is None:
    st.write("#")
    st.warning("⬅️ Please introduce your Azure OpenAI API Key in the sidebar to use the app.")

else:
    # Sidebar
    with st.sidebar:
        st.divider()

        print(f"{len(MODELS)} models available: {MODELS}")
        st.selectbox(
            "🤖 Select a Model",
            options=MODELS,
            key="model",
        )

        cols0 = st.columns(2)
        with cols0[0]:
            is_vector_db_loaded = ("vector_db" in st.session_state and st.session_state.vector_db is not None)
            st.toggle(
                "Use RAG",
                value=is_vector_db_loaded,
                key="use_rag",
                disabled=not is_vector_db_loaded,
            )

        with cols0[1]:
            st.button("Clear Chat", on_click=lambda: st.session_state.messages.clear(), type="primary")

        st.header("RAG Sources:")

        # File upload input for RAG with documents
        st.file_uploader(
            "📄 Upload a document",
            type=["pdf", "txt", "docx", "md"],
            accept_multiple_files=True,
            on_change=load_doc_to_db,
            key="rag_docs",
        )

        # URL input for RAG with websites
        st.text_input(
            "🌐 Introduce a URL",
            placeholder="https://example.com",
            on_change=load_url_to_db,
            key="rag_url",
        )

        with st.expander(f"📚 Documents in DB ({0 if not is_vector_db_loaded else len(st.session_state.rag_sources)})"):
            st.write([] if not is_vector_db_loaded else list(st.session_state.rag_sources))

    # Main chat app
    url = settings.LYTIX_JUNIOR_FOUNDRY_URL
    key = settings.LYTIX_JUNIOR_FOUNDRY_KEY.get_secret_value()
    model = settings.LYTIX_JUNIOR_FOUNDRY_MODEL
    model_version = settings.LYTIX_JUNIOR_FOUNDRY_MODEL_VERSION
    print("\n\n")
    print(f"URL: {url}")
    print(f"MODEL-CONF: {model}")
    print(f"MODEL-SESS: {st.session_state.model}")
    print(f"MODEL VERSION: {model_version}")
    llm_stream = AzureChatOpenAI(
        azure_endpoint=url,
        openai_api_version=model_version,
        model_name=model,
        openai_api_key=key,
        openai_api_type="azure",
        temperature=0.3,
        streaming=True,
    )
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Your message"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            messages = [HumanMessage(content=m["content"]) if m["role"] == "user" else AIMessage(content=m["content"]) for m in st.session_state.messages]

            if not st.session_state.use_rag:
                st.write_stream(stream_llm_response(llm_stream, messages))
            else:
                st.write_stream(stream_llm_rag_response(llm_stream, messages))


with st.sidebar:
    st.divider()
    st.write("📋[GitHub Repo](https://github.com/RoBiApps007/azure_llm_app_demo)")

