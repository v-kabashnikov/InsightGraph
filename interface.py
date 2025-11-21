import streamlit as st
from graph_agent import create_agent_runner

# --- App Configuration ---
st.set_page_config(page_title="InsightGraph 2.0", layout="wide", page_icon="🧠")
st.title("🧠 InsightGraph: Agentic Explorer")

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

                    # Create placeholders
                    status_placeholder = st.empty()
                    history_placeholder = st.empty()
                    answer_placeholder = st.empty()

                    # Process agent events
                    for event in agent_runner(prompt):
                        event_type = event.get("type")

                        if event_type == "summary":
                            # Show meaningful summary
                            status_placeholder.markdown(f"_{event['content']}_")

                        elif event_type == "tool_call":
                            # Show humanized status based on tool
                            tool_name = event["name"]
                            tool_args = event["args"]

                            if tool_name == "get_schema":
                                status_placeholder.markdown("_Understanding your database structure..._")
                                # Store technical details for history
                                action_history.append({
                                    "type": "tool_call",
                                    "content": "🔍 **Getting database schema**"
                                })
                            elif tool_name == "run_query":
                                status_placeholder.markdown("_Analyzing your data..._")
                                query = tool_args.get("query", "")
                                # Store technical details for history
                                display_query = query[:200] + "..." if len(query) > 200 else query
                                action_history.append({
                                    "type": "tool_call",
                                    "content": f"⚡ **Executing Cypher query**\n```cypher\n{display_query}\n```"
                                })
                            else:
                                status_placeholder.markdown("_Working on it..._")
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