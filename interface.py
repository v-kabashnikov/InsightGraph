import streamlit as st
from streamlit_lottie import st_lottie
from streamlit_agraph import agraph, Config
from langchain_neo4j import Neo4jGraph

# Import our custom modules
import config
import visualization
import brain

# 1. Setup
config.setup_page()

# Initialize Session State for Schema
if "schema_data" not in st.session_state:
    st.session_state.schema_data = {"nodes": [], "edges": []}

# Load Animation
lottie_graph = config.load_lottieurl(config.LOTTIE_URL)

st.title("InsightGraph")

# ==========================================
# 2. SIDEBAR
# ==========================================
with st.sidebar:
    st.header("🔌 Connection")
    neo4j_url = st.text_input("Neo4j URI", value="neo4j+s://f99fdccf.databases.neo4j.io")
    neo4j_user = st.text_input("Username", value="neo4j")
    neo4j_password = st.text_input("Password", type="password", value="") 
    st.divider()
    gemini_key = st.text_input("Google API Key", type="password", value="")
    model_name = st.text_input("Model Name", value="gemini-2.5-flash")
    
    if st.button("Reload Schema Map"):
        st.session_state.schema_data = {"nodes": [], "edges": []}
        st.rerun()

# ==========================================
# 3. FETCH SCHEMA (INITIAL STATE)
# ==========================================
if neo4j_password and not st.session_state.schema_data["nodes"]:
    try:
        with st.spinner("Fetching Data Structure..."):
            schema_graph = Neo4jGraph(url=neo4j_url, username=neo4j_user, password=neo4j_password)
            
            # Safer Query: Checks for labels existence
            schema_query = """
            MATCH (a)-[r]->(b)
            WITH labels(a) AS a_labels, type(r) AS r_type, labels(b) AS b_labels
            WHERE size(a_labels) > 0 AND size(b_labels) > 0
            RETURN a_labels[0] AS source_label, r_type AS relationship_type, b_labels[0] AS target_label
            LIMIT 100
            """
            
            with schema_graph._driver.session() as session:
                result = session.run(schema_query)
                
                schema_nodes = {} 
                schema_edges = []
                from streamlit_agraph import Node, Edge 

                for record in result:
                    src = record['source_label']
                    rel = record['relationship_type']
                    tgt = record['target_label']
                    
                    if src not in schema_nodes:
                        schema_nodes[src] = Node(id=src, label=src, size=25, color="#4ECDC4")
                    
                    if tgt not in schema_nodes:
                        schema_nodes[tgt] = Node(id=tgt, label=tgt, size=25, color="#FF6B6B")
                        
                    schema_edges.append(Edge(source=src, target=tgt, label=rel))
            
            if schema_nodes:
                st.session_state.schema_data = {"nodes": list(schema_nodes.values()), "edges": schema_edges}
            else:
                st.toast("Connected, but no relationships found in DB.", icon="⚠️")

    except Exception as e:
        st.sidebar.error(f"Schema fetch failed: {e}")

# ==========================================
# 4. DASHBOARD LAYOUT
# ==========================================
col_chat, col_graph = st.columns([3, 2], gap="medium")

# --- RIGHT COLUMN: STATIC SCHEMA VIEW ---
with col_graph:
    with st.expander("Schema", expanded=True):
        nodes = st.session_state.schema_data.get("nodes", [])
        edges = st.session_state.schema_data.get("edges", [])
        
        if nodes:
            st.caption(f"({len(nodes)} Entity Types)")
            
            # FIX: CLEANEST POSSIBLE CONFIGURATION
            # 1. Remove options that cause "Unknown option" errors (highlightColor, collapsible, etc.)
            # 2. Explicitly set groups={} to fix the "Invalid type: null" error.
            config_obj = Config(
                width="100%", 
                height=600, 
                directed=True, 
                physics=True, 
                hierarchical=False,
                groups={} # <--- CRITICAL FIX for null error
            )
            
            try:
                agraph(nodes=nodes, edges=edges, config=config_obj)
            except Exception as e:
                st.error(f"Graph render error: {e}")
        else:
            st.info("Connect to Neo4j to see the schema.")
            if lottie_graph:
                st_lottie(lottie_graph, height=200, key="idle")

# --- LEFT COLUMN: CHAT INTERFACE ---
with col_chat:
    if neo4j_password and gemini_key:
        try:
            graph, chain = brain.get_graph_chain(neo4j_url, neo4j_user, neo4j_password, gemini_key, model_name)

            if "messages" not in st.session_state: st.session_state.messages = []
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    if "cypher" in msg:
                        with st.expander("Logic"): st.code(msg["cypher"], language="cypher")

            if prompt := st.chat_input("Ex: Show me the network for Hogewoning"):
                clean_prompt = prompt.strip()
                st.session_state.messages.append({"role": "user", "content": clean_prompt})
                with st.chat_message("user"): st.markdown(clean_prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            response = chain.invoke(clean_prompt)
                            result_text = response['result']
                            generated_cypher = response['intermediate_steps'][0]['query']
                            
                            st.markdown(result_text)
                            st.session_state.messages.append({
                                "role": "assistant", 
                                "content": result_text, 
                                "cypher": generated_cypher
                            })
                            
                        except Exception as e:
                            st.error(f"Error: {e}")

        except Exception as e:
            st.error(f"Connection Failed: {e}")
    else:
        st.warning("👈 Enter credentials to start.")