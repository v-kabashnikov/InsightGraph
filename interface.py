import streamlit as st
import time
from graph_agent import create_agent_runner

# --- App Configuration ---
st.set_page_config(
    page_title="InsightGraph 2.0",
    layout="wide",
    page_icon="🧠",
    initial_sidebar_state="expanded"
)

# --- Brand Colors ---
# Primary: #1c1053 (dark purple - main accent color)
# Background: #0d0829 (darker purple for UI elements)
# Light Gray: #f5f5f5
# White: #FFFFFF
# Black Background: #000000

# --- Custom CSS for Brand Styling ---
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background-color: #000000;
        color: #f5f5f5;
    }

    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background-color: #000000;
    }

    /* Title styling */
    h1 {
        color: #1c1053 !important;
        font-weight: 700 !important;
        margin-bottom: 1.5rem !important;
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #0d0829 !important;
    }

    [data-testid="stSidebar"] .stMarkdown {
        color: #f5f5f5 !important;
    }

    [data-testid="stSidebar"] h2 {
        color: #1c1053 !important;
    }

    /* Input fields */
    .stTextInput > div > div > input {
        background-color: #0d0829 !important;
        color: #f5f5f5 !important;
        border: 1px solid #1c1053 !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #1c1053 !important;
        box-shadow: 0 0 0 1px #1c1053 !important;
    }

    /* Chat input */
    .stChatInput > div > div > input {
        background-color: #0d0829 !important;
        color: #f5f5f5 !important;
        border: 1px solid #1c1053 !important;
    }

    /* Chat messages */
    .stChatMessage {
        background-color: #0d0829 !important;
        border: 1px solid #1c1053 !important;
        border-radius: 8px !important;
    }

    [data-testid="stChatMessageContent"] {
        color: #f5f5f5 !important;
    }

    /* Info/Success/Error boxes */
    .stAlert {
        background-color: #0d0829 !important;
        color: #f5f5f5 !important;
        border-left: 4px solid #1c1053 !important;
    }

    /* Markdown text */
    .stMarkdown {
        color: #f5f5f5 !important;
    }

    /* Code blocks */
    code {
        background-color: #0d0829 !important;
        color: #1c1053 !important;
        border: 1px solid #1c1053 !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
    }

    pre {
        background-color: #0d0829 !important;
        border: 1px solid #1c1053 !important;
        border-radius: 8px !important;
    }

    pre code {
        color: #f5f5f5 !important;
        border: none !important;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #0d0829 !important;
        color: #1c1053 !important;
        border: 1px solid #1c1053 !important;
        border-radius: 8px !important;
    }

    .streamlit-expanderHeader:hover {
        background-color: #150d3d !important;
    }

    .streamlit-expanderContent {
        background-color: #0d0829 !important;
        border: 1px solid #1c1053 !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }

    /* Divider */
    hr {
        border-color: #1c1053 !important;
        opacity: 0.3 !important;
    }

    /* Status text (italic) */
    em {
        color: #1c1053 !important;
        font-style: italic !important;
    }

    /* Links */
    a {
        color: #1c1053 !important;
    }

    a:hover {
        color: #2d1a73 !important;
    }

    /* Success message styling */
    .stSuccess {
        background-color: #0d0829 !important;
        color: #f5f5f5 !important;
        border-left: 4px solid #1c1053 !important;
    }

    /* Warning message styling */
    .stWarning {
        background-color: #0d0829 !important;
        color: #f5f5f5 !important;
        border-left: 4px solid #1c1053 !important;
    }

    /* Error message styling */
    .stError {
        background-color: #0d0829 !important;
        color: #f5f5f5 !important;
        border-left: 4px solid #1c1053 !important;
    }

    /* Info message styling */
    .stInfo {
        background-color: #0d0829 !important;
        color: #f5f5f5 !important;
        border-left: 4px solid #1c1053 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 InsightGraph: Agentic Explorer")

# --- Shipping Jokes ---
SHIPPING_JOKES = [
    "Why did the shipping container go to therapy? It had too much baggage! 📦",
    "What do you call a carrier that never delivers on time? A 'ship' happens company! 🚢",
    "Why don't ports ever get lonely? They're always bustling with activity! ⚓",
    "What's a logistics manager's favorite music? Heavy shipping! 🎵",
    "Why did the cargo ship break up with the tugboat? It needed more space! 💔",
    "What do you call a shipment that's always late? Fashionably delayed! ⏰",
    "Why are shipping manifests always so organized? They have excellent containerization! 📋",
    "What's a freight forwarder's favorite movie? The Ship-ment! 🎬",
    "Why did the package become a comedian? It had great delivery! 🎤",
    "What do you call a vessel with a sense of humor? A cargo-mic! 😄"
]

# --- Sidebar for Credentials ---
with st.sidebar:
    st.header("🔌 Connection Credentials")
    st.markdown("Provide your database and API credentials to activate the agent.")
    
    neo4j_uri = st.text_input("Neo4j URI", value="neo4j+s://ee558c73.databases.neo4j.io")
    neo4j_user = st.text_input("Neo4j Username", value="neo4j")
    neo4j_password = st.text_input("Neo4j Password", type="password", value="")
    gemini_key = st.text_input("Google Gemini API Key", type="password")
    
    st.divider()
    if neo4j_password and gemini_key:
        st.success("Credentials provided!")
    else:
        st.warning("Missing one or more credentials.")

# --- Caching the Agent ---
# Use Streamlit's cache to create the agent only once
@st.cache_resource
def get_agent_runner(_neo4j_uri, _neo4j_user, _neo4j_password, _gemini_key):
    """Creates and caches the agent runner and its database tools instance."""
    agent_runner, db_tools = create_agent_runner(
        _neo4j_uri, _neo4j_user, _neo4j_password, _gemini_key
    )
    return agent_runner, db_tools

# --- Main Chat Interface ---
if neo4j_password and gemini_key:
    # Create the agent runner using the credentials
    try:
        agent_runner, db_tools = get_agent_runner(neo4j_uri, neo4j_user, neo4j_password, gemini_key)

        st.markdown("""
        Ask complex, multi-step questions about your shipping logistics data.
        *Example: "Which customer has the most negative shipments, and what are the top 3 issues associated with them?"*
        """)

        # Initialize chat history
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display chat history on rerun
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input box
        if prompt := st.chat_input("Ask a question about your graph..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    # Track all actions and final answer
                    action_history = []
                    final_answer = ""

                    # Joke cycling setup
                    joke_index = 0
                    last_joke_time = time.time()
                    start_time = time.time()

                    # Create placeholders
                    status_placeholder = st.empty()
                    history_placeholder = st.empty()
                    answer_placeholder = st.empty()

                    # Process agent events
                    for event in agent_runner(prompt):
                        event_type = event.get("type")

                        # Check if 10 seconds have passed since last joke change
                        current_time = time.time()
                        if current_time - last_joke_time >= 10:
                            joke_index = (joke_index + 1) % len(SHIPPING_JOKES)
                            last_joke_time = current_time

                        if event_type == "summary":
                            # Show status with joke
                            status_msg = event['content']
                            joke = SHIPPING_JOKES[joke_index]
                            status_placeholder.markdown(f"_{status_msg}_\n\n💡 {joke}")

                        elif event_type == "tool_call":
                            # Show humanized status based on tool
                            tool_name = event["name"]
                            tool_args = event["args"]
                            joke = SHIPPING_JOKES[joke_index]

                            if tool_name == "get_schema":
                                status_placeholder.markdown(f"_Understanding your database structure..._\n\n💡 {joke}")
                                # Store technical details for history
                                action_history.append({
                                    "type": "tool_call",
                                    "content": "🔍 **Getting database schema**"
                                })
                            elif tool_name == "run_query":
                                status_placeholder.markdown(f"_Analyzing your data..._\n\n💡 {joke}")
                                query = tool_args.get("query", "")
                                # Store technical details for history
                                display_query = query[:200] + "..." if len(query) > 200 else query
                                action_history.append({
                                    "type": "tool_call",
                                    "content": f"⚡ **Executing Cypher query**\n```cypher\n{display_query}\n```"
                                })
                            else:
                                status_placeholder.markdown(f"_Working on it..._\n\n💡 {joke}")
                                action_history.append({
                                    "type": "tool_call",
                                    "content": f"🔧 **Calling tool: {tool_name}**\n```json\n{tool_args}\n```"
                                })

                        elif event_type == "tool_result":
                            # Store technical results for history only
                            tool_name = event["name"]
                            result = event["result"]
                            is_error = event.get("error", False)

                            display_result = result[:500] + "..." if len(result) > 500 else result

                            if is_error:
                                result_msg = f"❌ **Error from {tool_name}**\n```\n{display_result}\n```"
                            else:
                                result_msg = f"✅ **Result from {tool_name}**\n```\n{display_result}\n```"

                            action_history.append({"type": "tool_result", "content": result_msg})

                        elif event_type == "final_answer":
                            # Clear status and show final answer
                            status_placeholder.empty()
                            final_answer = event["content"]

                            # Show expandable history if there are actions
                            if action_history:
                                with history_placeholder.expander("View reasoning steps", expanded=False):
                                    for i, action in enumerate(action_history, 1):
                                        st.markdown(f"**Step {i}**")
                                        st.markdown(action["content"])
                                        if i < len(action_history):
                                            st.divider()

                            # Display final answer
                            answer_placeholder.markdown(final_answer)

                    # Save to chat history
                    st.session_state.messages.append({"role": "assistant", "content": final_answer})

                except Exception as e:
                    st.error(f"An error occurred while running the agent: {e}")
    
    except Exception as e:
        st.error(f"Failed to initialize the agent. Please check your credentials. Error: {e}")

else:
    st.info("Please provide all credentials in the sidebar to begin.")

# Optional: Add a cleanup hook for the database connection if needed,
# but for local dev, letting it timeout is usually fine.