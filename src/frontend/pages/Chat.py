"""Streamlit frontend for CoTrial RAG v2."""

import os
from typing import Any

import requests
import streamlit as st

# Page config
st.set_page_config(
    page_title="CoTrial RAG System",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items=None,
)

# API configuration
API_URL = os.getenv(
    "RAG_API_URL",
    "http://localhost:8000",
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
                timeout=35,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            if attempt < retry_count:
                st.info(f"⏳ Request timed out. Retrying... (attempt {attempt + 2}/{retry_count + 1})")
                time.sleep(2)
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
                    time.sleep(3)
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
        health_response = requests.get(
            f"{st.session_state.api_url}/health",
            timeout=10
        )
        if health_response.status_code == 200:
            status_response = requests.get(
                f"{st.session_state.api_url}/v1/status",
                timeout=35
            )
            return status_response.status_code == 200
        return False
    except Exception:
        return False


def display_citation(citation: dict[str, Any], index: int) -> None:
    """Display a citation in an expandable section with elegant styling."""
    corpus = citation.get('corpus', 'unknown').upper()
    score = citation.get('score', 0)
    
    corpus_colors = {
        'PDF': '#8B4513',
        'SAS': '#2C5F8D',
        'CONTEXT': '#6B4E9B',
    }
    color = corpus_colors.get(corpus, '#5A6C7D')
    
    # Use proper arrow icon instead of text
    with st.expander(
        f"Source {index + 1}: {corpus} (Relevance: {score:.3f})",
        expanded=False,
    ):
        st.markdown(
            f"""
            <div style="padding: 1.25rem 1.5rem; background: rgba(253, 250, 246, 0.95); border-left: 4px solid {color}; margin: 1rem 0; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);">
                <p style="color: #000000; line-height: 1.9; margin-bottom: 1rem; font-size: 1.1rem; font-weight: 400;">
                    {citation.get("snippet", "No snippet available")}
                </p>
                <p style="color: #000000; font-size: 0.95rem; margin: 0; font-weight: 400;">
                    <strong>Document ID:</strong> {citation.get('chunk_id', 'N/A')}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )


def main() -> None:
    """Main Streamlit app."""
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.switch_page("pages/login.py")
    
    initialize_session_state()

    # Enhanced formal and rich styling
    st.markdown(
        """
        <style>
        /* Elegant serif typography */
        * {
            font-family: "Baskerville", "Libre Baskerville", "Times New Roman", serif !important;
        }
        
        /* Rich gradient background - deep burgundy to warm cream */
        .stApp {
            background: linear-gradient(135deg, #8B4513 0%, #A0522D 50%, #CD853F 100%);
            background-attachment: fixed;
        }
        
        /* Sidebar - sophisticated dark wood panel aesthetic */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a1a 0%, #2d2d2d 100%) !important;
            border-right: 2px solid rgba(205, 133, 63, 0.3);
            box-shadow: 4px 0 20px rgba(0, 0, 0, 0.5);
        }
        
        [data-testid="stSidebar"] * {
            color: #F5E6D3 !important;
        }
        
        /* Main content container - premium parchment */
        .main {
            background: transparent;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* Center all content perfectly */
        .main .block-container {
            background: transparent;
            padding: 0 !important;
            margin: 0 auto !important;
            max-width: 900px !important;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            min-height: 100vh;
        }
        
        /* Chat messages container - centered with max width */
        [data-testid="stVerticalBlock"] {
            max-width: 900px !important;
            width: 100% !important;
            margin: 0 auto !important;
            padding: 2rem 3rem !important;
            padding-bottom: 8rem !important; /* Space for fixed input */
        }
        
        /* Remove greeting section - causing display issues */
        .greeting-section {
            display: none !important;
        }
        
        /* Chat messages - elegant cards with centered layout */
        .stChatMessage {
            background: rgba(253, 250, 246, 0.98) !important;
            border: 2px solid rgba(139, 69, 19, 0.2) !important;
            border-radius: 12px;
            padding: 2rem 2.5rem !important;
            margin: 1.5rem auto !important;
            max-width: 900px !important;
            width: 100% !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.12);
            backdrop-filter: blur(10px);
        }
        
        /* User messages - distinguished styling */
        .stChatMessage[data-testid="user"] {
            background: rgba(245, 238, 220, 0.98) !important;
            border-left: 4px solid #8B4513 !important;
        }
        
        /* Assistant messages */
        .stChatMessage[data-testid="assistant"] {
            background: rgba(255, 255, 255, 0.98) !important;
            border-left: 4px solid #CD853F !important;
        }
        
        /* Message text - clear and readable */
        .stChatMessage p,
        .stChatMessage div {
            color: #000000 !important;
            font-size: 1.1rem !important;
            line-height: 1.8 !important;
            font-weight: 400 !important;
        }
        
        /* Message avatars */
        .stChatMessage [data-testid="stChatAvatar"] {
            background: linear-gradient(135deg, #8B4513 0%, #A0522D 100%) !important;
            color: #F5E6D3 !important;
            font-weight: 600 !important;
        }
        
        /* Chat input - centered and elegant */
        [data-testid="stChatInput"] {
            position: fixed !important;
            bottom: 2rem !important;
            left: 50% !important;
            transform: translateX(-50%) !important;
            width: 800px !important;
            max-width: calc(100vw - 350px) !important;
            z-index: 1000 !important;
            margin-left: 125px !important; /* Account for sidebar */
        }
        
        /* Ensure input doesn't overlap with messages */
        [data-testid="stChatInputContainer"] {
            padding-bottom: 0 !important;
            max-width: 900px !important;
            margin: 0 auto !important;
        }
        
        .stChatInput {
            background: rgba(253, 250, 246, 0.98) !important;
            border: 2px solid rgba(139, 69, 19, 0.3) !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15) !important;
            backdrop-filter: blur(10px) !important;
        }
        
        .stChatInput input {
            background: transparent !important;
            border: none !important;
            font-size: 1.1rem !important;
            padding: 1.25rem 2rem !important;
            color: #000000 !important;
        }
        
        .stChatInput input::placeholder {
            color: #666666 !important;
            font-style: italic;
        }
        
        /* Buttons - luxurious gold accent */
        .stButton > button {
            background: linear-gradient(135deg, #8B4513 0%, #A0522D 100%) !important;
            color: #F5E6D3 !important;
            border: 2px solid rgba(205, 133, 63, 0.4) !important;
            border-radius: 10px !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            padding: 0.9rem 2rem !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(139, 69, 19, 0.3) !important;
            letter-spacing: 0.5px;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 25px rgba(139, 69, 19, 0.5) !important;
            border-color: rgba(205, 133, 63, 0.7) !important;
            background: linear-gradient(135deg, #A0522D 0%, #CD853F 100%) !important;
        }
        
        /* Sidebar branding */
        .sidebar-brand {
            background: linear-gradient(135deg, #8B4513 0%, #A0522D 100%);
            padding: 1.5rem;
            margin: -1rem -1rem 2rem -1rem;
            border-bottom: 2px solid rgba(205, 133, 63, 0.5);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        
        .sidebar-brand h2 {
            color: #F5E6D3 !important;
            font-size: 1.8rem !important;
            font-weight: 600 !important;
            margin: 0 !important;
            letter-spacing: 1px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        /* Expanders - refined styling */
        .streamlit-expanderHeader {
            background: linear-gradient(135deg, #F5E6D3 0%, #F8F4EE 100%) !important;
            border: 1px solid rgba(139, 69, 19, 0.2) !important;
            border-radius: 10px !important;
            padding: 1rem 1.5rem !important;
            font-weight: 600 !important;
            color: #000000 !important;
            font-size: 1.05rem !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }
        
        /* Hide ALL icon-related elements and text */
        .streamlit-expanderHeader [class*="icon"],
        .streamlit-expanderHeader [data-icon],
        .streamlit-expanderHeader .material-icons,
        .streamlit-expanderHeader [class*="material"],
        .streamlit-expanderHeader span[class*="icon"],
        .streamlit-expanderHeader svg,
        .streamlit-expanderHeader i {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
            height: 0 !important;
            font-size: 0 !important;
        }
        
        /* Hide pseudo-elements that might contain icon text */
        .streamlit-expanderHeader::after,
        .streamlit-expanderHeader::before {
            display: none !important;
            content: "" !important;
        }
        
        /* Hide any text containing icon names */
        .streamlit-expanderHeader *:not([class*="expander"]):not([class*="title"]) {
            font-family: "Baskerville", "Libre Baskerville", "Times New Roman", serif !important;
        }
        
        /* Specifically target and hide "keyboard_arrow_right" text */
        .streamlit-expanderHeader * {
            text-indent: 0 !important;
        }
        
        .streamlit-expanderContent {
            background: #FDFCFB !important;
            border: 1px solid rgba(139, 69, 19, 0.15) !important;
            border-top: none !important;
            padding: 1.5rem !important;
            border-radius: 0 0 10px 10px !important;
        }
        
        /* Expander content text */
        .streamlit-expanderContent p,
        .streamlit-expanderContent div {
            color: #000000 !important;
            font-size: 1.1rem !important;
            line-height: 1.9 !important;
        }
        
        /* Text styling - clear and readable */
        .stMarkdown {
            color: #000000 !important;
            line-height: 1.9 !important;
            font-size: 1.1rem !important;
            font-weight: 400 !important;
        }
        
        /* Message content spacing */
        .stChatMessage p {
            margin-bottom: 1.2rem;
            line-height: 1.9;
            color: #000000 !important;
            font-size: 1.1rem !important;
        }
        
        /* Lists in messages */
        .stChatMessage ul,
        .stChatMessage ol {
            color: #000000 !important;
            font-size: 1.1rem !important;
            line-height: 1.9 !important;
            margin: 1rem 0;
        }
        
        .stChatMessage li {
            margin-bottom: 0.75rem;
            color: #000000 !important;
        }
        
        /* Bold text in messages */
        .stChatMessage strong,
        .stChatMessage b {
            color: #000000 !important;
            font-weight: 700 !important;
        }
        
        /* Divider */
        hr {
            border: none;
            border-top: 2px solid rgba(139, 69, 19, 0.2);
            margin: 2rem 0;
        }
        
        /* Scrollbar - luxury gold */
        ::-webkit-scrollbar {
            width: 12px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(245, 238, 220, 0.5);
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #8B4513 0%, #CD853F 100%);
            border-radius: 6px;
            border: 2px solid rgba(245, 238, 220, 0.5);
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(180deg, #A0522D 0%, #DEB887 100%);
        }
        
        /* Alert boxes */
        .stInfo {
            background: rgba(245, 238, 220, 0.8) !important;
            border-left: 4px solid #8B4513 !important;
            color: #2C1810 !important;
            border-radius: 8px;
        }
        
        .stWarning {
            background: rgba(255, 248, 230, 0.9) !important;
            border-left: 4px solid #CD853F !important;
            color: #2C1810 !important;
            border-radius: 8px;
        }
        
        /* User profile */
        .user-profile {
            background: rgba(139, 69, 19, 0.2);
            padding: 1rem;
            border-radius: 10px;
            margin-top: 2rem;
            border: 1px solid rgba(205, 133, 63, 0.3);
        }
        
        .user-avatar {
            background: linear-gradient(135deg, #8B4513 0%, #CD853F 100%) !important;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
        }
        
        /* Hide Streamlit branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* Spacing adjustment for chat history */
        [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        </style>
        <script>
        // Remove icon text from expanders - runs after page loads
        function removeIconText() {
            var headers = document.querySelectorAll('.streamlit-expanderHeader');
            headers.forEach(function(header) {
                // Find and remove text nodes containing icon names
                var walker = document.createTreeWalker(
                    header,
                    NodeFilter.SHOW_TEXT,
                    null,
                    false
                );
                var textNodes = [];
                var node;
                while (node = walker.nextNode()) {
                    var text = node.textContent || '';
                    if (text.includes('keyboard_arrow_right') || 
                        (text.includes('arrow') && text.trim().length < 30 && text.trim().length > 0)) {
                        textNodes.push(node);
                    }
                }
                textNodes.forEach(function(textNode) {
                    textNode.textContent = '';
                });
                
                // Hide any icon elements
                var iconElements = header.querySelectorAll('[class*="icon"], [class*="material"], svg, i, [data-icon]');
                iconElements.forEach(function(el) {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.style.width = '0';
                    el.style.height = '0';
                });
            });
        }
        
        // Run on page load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() {
                removeIconText();
                setTimeout(removeIconText, 500);
            });
        } else {
            removeIconText();
            setTimeout(removeIconText, 500);
        }
        
        // Watch for new expanders added by Streamlit
        var observer = new MutationObserver(function(mutations) {
            removeIconText();
        });
        observer.observe(document.body, { 
            childList: true, 
            subtree: true 
        });
        </script>
        """,
        unsafe_allow_html=True,
    )

    # Sidebar
    with st.sidebar:
        st.markdown(
            """
            <div class="sidebar-brand">
                <h2>CoTrial RAG</h2>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: rgba(245, 230, 211, 0.8); font-style: italic;">
                    Professional Research Assistant
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        if st.button("✨ New Conversation", use_container_width=True, type="primary"):
            st.session_state.messages = []
            st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.messages:
            st.markdown(
                """
                <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid rgba(205, 133, 63, 0.3);">
                    <div style="color: #CD853F; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 1rem;">Recent Queries</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            recent_queries = [
                msg["content"][:50] + "..." if len(msg["content"]) > 50 else msg["content"]
                for msg in st.session_state.messages[-6:]
                if msg["role"] == "user"
            ]
            for query in recent_queries[-3:]:
                if st.button(query, key=f"recent_{query[:20]}", use_container_width=True):
                    st.session_state.messages.append({"role": "user", "content": query})
                    st.rerun()
        
        username = st.session_state.get("username", "User")
        initial = username[0].upper() if username else "U"
        
        st.markdown(
            f"""
            <div class="user-profile">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div class="user-avatar" style="width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: #F5E6D3; font-weight: 600; font-size: 1.1rem;">{initial}</div>
                    <div style="flex: 1;">
                        <p style="color: #F5E6D3; font-size: 1rem; font-weight: 600; margin: 0;">{username}</p>
                        <p style="color: rgba(245, 230, 211, 0.7); font-size: 0.85rem; margin: 0; font-style: italic;">Professional Account</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.switch_page("pages/login.py")

    # Main content - centered container
    with st.container():
        # Display chat history
        if st.session_state.messages:
            for message in st.session_state.messages:
                role = message["role"]
                content = message["content"]
                citations = message.get("citations", [])

                if role == "user":
                    with st.chat_message("user"):
                        st.markdown(f'<div style="color: #000000; font-size: 1.1rem; line-height: 1.9;">{content}</div>', unsafe_allow_html=True)
                else:
                    with st.chat_message("assistant"):
                        st.markdown(f'<div style="color: #000000; font-size: 1.1rem; line-height: 1.9;">{content}</div>', unsafe_allow_html=True)

                        if citations:
                            st.markdown(
                                """
                                <div style="margin-top: 2rem; padding-top: 2rem; border-top: 3px solid rgba(139, 69, 19, 0.3);">
                                    <h4 style="color: #000000; font-size: 1.3rem; font-weight: 700; margin-bottom: 1.5rem; letter-spacing: 0.3px;">
                                        Referenced Sources
                                    </h4>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            for idx, citation in enumerate(citations):
                                display_citation(citation, idx)
        else:
            # Show simple centered greeting when no messages
            st.markdown(
                """
                <div style="text-align: center; padding: 8rem 2rem; min-height: 50vh; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                    <h1 style="font-size: 3rem; font-weight: 700; color: #000000; margin: 0; letter-spacing: 0.5px;">How may I assist you today?</h1>
                    <p style="font-size: 1.4rem; color: #000000; margin-top: 1.5rem; font-style: italic; letter-spacing: 0.3px; font-weight: 400;">Ask me anything about your research data</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Chat input
    if prompt := st.chat_input("Type your question here..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(f'<div style="color: #000000; font-size: 1.1rem; line-height: 1.9;">{prompt}</div>', unsafe_allow_html=True)

        with st.chat_message("assistant"):
            with st.spinner("Researching..."):
                response = send_message(prompt)

            if response:
                answer = response.get("answer", "No answer provided.")
                citations = response.get("citations", [])

                st.markdown(f'<div style="color: #000000; font-size: 1.1rem; line-height: 1.9;">{answer}</div>', unsafe_allow_html=True)

                if citations:
                    st.markdown(
                        """
                        <div style="margin-top: 2rem; padding-top: 2rem; border-top: 3px solid rgba(139, 69, 19, 0.3);">
                            <h4 style="color: #000000; font-size: 1.3rem; font-weight: 700; margin-bottom: 1.5rem; letter-spacing: 0.3px;">
                                Referenced Sources
                            </h4>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    for idx, citation in enumerate(citations):
                        display_citation(citation, idx)

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
                    
                    The service may be initializing. Please wait a moment and try again.
                    """
                )


if __name__ == "__main__":
    main()
    