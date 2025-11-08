"""Streamlit frontend for CoTrial RAG v2."""

import os
from typing import Any

import requests
import streamlit as st

# Page config
st.set_page_config(
    page_title="CoTrial RAG Chat",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# API configuration
API_URL = os.getenv(
    "RAG_API_URL",
    "https://otjzog1ts9.execute-api.us-east-2.amazonaws.com/Prod",
)


def initialize_session_state() -> None:
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "api_url" not in st.session_state:
        st.session_state.api_url = API_URL


def send_message(query: str, retry_count: int = 2) -> dict[str, Any] | None:
    """Send a message to the RAG API with retry logic."""
    import time
    
    for attempt in range(retry_count + 1):
        try:
            response = requests.post(
                f"{st.session_state.api_url}/v1/chat",
                json={"query": query, "top_k": 5},
                timeout=35,  # Slightly longer than API Gateway timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            if attempt < retry_count:
                st.info(f"⏳ Request timed out. Retrying... (attempt {attempt + 2}/{retry_count + 1})")
                time.sleep(2)  # Wait before retry
                continue
            else:
                st.warning(
                    "⚠️ **Request timed out** - The API is warming up. "
                    "This usually happens on the first request after inactivity. "
                    "Please try again in a few seconds - subsequent requests should be faster."
                )
                return None
        except requests.exceptions.RequestException as e:
            error_str = str(e)
            if "504" in error_str or "Gateway Timeout" in error_str:
                if attempt < retry_count:
                    st.info(f"⏳ Gateway timeout. Retrying... (attempt {attempt + 2}/{retry_count + 1})")
                    time.sleep(3)  # Wait longer for gateway timeout
                    continue
                else:
                    st.warning(
                        "⚠️ **Gateway Timeout** - The Lambda is warming up. "
                        "Please wait 10-15 seconds and try again. "
                        "The next request should work! You can also use the '🔥 Warm Up API' button in the sidebar."
                    )
                    return None
            else:
                st.error(f"Error: {error_str}")
                if hasattr(e, "response") and e.response is not None:
                    try:
                        error_detail = e.response.json()
                        st.error(f"Details: {error_detail}")
                    except Exception:
                        st.error(f"Status: {e.response.status_code}")
                return None
    return None


def warm_up_api() -> bool:
    """Warm up the API by making a health check request."""
    try:
        # First, try health endpoint (fast)
        health_response = requests.get(
            f"{st.session_state.api_url}/health",
            timeout=10
        )
        if health_response.status_code == 200:
            # Then try status endpoint to trigger initialization
            status_response = requests.get(
                f"{st.session_state.api_url}/v1/status",
                timeout=35
            )
            return status_response.status_code == 200
        return False
    except Exception:
        return False


def display_citation(citation: dict[str, Any], index: int) -> None:
    """Display a citation in an expandable section."""
    with st.expander(
        f"📄 Source {index + 1}: {citation.get('corpus', 'unknown').upper()} "
        f"(Score: {citation.get('score', 0):.3f})",
        expanded=False,
    ):
        st.text(citation.get("snippet", "No snippet available"))
        st.caption(f"Chunk ID: {citation.get('chunk_id', 'N/A')}")


def main() -> None:
    """Main Streamlit app."""
    initialize_session_state()

    # Custom CSS for ChatGPT-like styling
    st.markdown(
        """
        <style>
        .main {
            padding-top: 2rem;
        }
        .stTextInput > div > div > input {
            font-size: 16px;
            padding: 12px;
        }
        .stButton > button {
            width: 100%;
            font-size: 16px;
            padding: 12px;
        }
        .message {
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 8px;
        }
        .user-message {
            background-color: #f0f0f0;
        }
        .assistant-message {
            background-color: #e8f4f8;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Title
    st.title("💬 CoTrial RAG Chat")
    st.caption("Ask questions about clinical trial data and documents")

    # Sidebar for API URL configuration (optional)
    with st.sidebar:
        st.header("⚙️ Configuration")
        api_url_input = st.text_input(
            "API URL",
            value=st.session_state.api_url,
            help="API endpoint URL",
        )
        if api_url_input != st.session_state.api_url:
            st.session_state.api_url = api_url_input
            st.session_state.messages = []  # Clear messages on URL change
            st.rerun()

        st.markdown("---")
        
        if st.button("🔥 Warm Up API", help="Pre-warm the Lambda to avoid timeouts on first request"):
            with st.spinner("Warming up the API (this may take 30 seconds)..."):
                if warm_up_api():
                    st.success("✅ API warmed up! Try your query now.")
                else:
                    st.warning(
                        "⚠️ Warm-up in progress... "
                        "The API may still be initializing. "
                        "Try your query in 10-15 seconds."
                    )

        if st.button("Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

    # Display chat history
    for message in st.session_state.messages:
        role = message["role"]
        content = message["content"]
        citations = message.get("citations", [])

        if role == "user":
            with st.chat_message("user"):
                st.write(content)
        else:  # assistant
            with st.chat_message("assistant"):
                st.write(content)

                # Display citations if available
                if citations:
                    st.markdown("---")
                    st.markdown("**Sources:**")
                    for idx, citation in enumerate(citations):
                        display_citation(citation, idx)

    # Chat input
    if prompt := st.chat_input("Ask a question about the clinical trial data..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Display user message
        with st.chat_message("user"):
            st.write(prompt)

        # Get response from API
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = send_message(prompt)

            if response:
                answer = response.get("answer", "No answer provided.")
                citations = response.get("citations", [])

                # Display answer
                st.write(answer)

                # Display citations
                if citations:
                    st.markdown("---")
                    st.markdown("**Sources:**")
                    for idx, citation in enumerate(citations):
                        display_citation(citation, idx)

                # Add assistant message to history
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "citations": citations,
                    }
                )
            else:
                st.warning(
                    """
                    ⚠️ **Request failed or timed out**
                    
                    **What's happening:**
                    - The Lambda may be cold (first request after inactivity)
                    - It's downloading indices from S3 (takes ~30 seconds)
                    - API Gateway has a 29-second timeout limit
                    
                    **What to do:**
                    1. Wait 10-15 seconds
                    2. Click the "🔥 Warm Up API" button in the sidebar
                    3. Try your query again - it should work on the second attempt!
                    
                    Subsequent requests should be much faster once the Lambda is warm.
                    """
                )


if __name__ == "__main__":
    main()

