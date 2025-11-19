import streamlit as st
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI
# FIX: Import from 'langchain_core' instead of 'langchain'
from langchain_core.prompts import PromptTemplate

# ==========================================
# 1. APP CONFIGURATION
# ==========================================
st.set_page_config(page_title="InsightGraph Explorer", layout="wide", page_icon="🚢")

st.title("🚢 InsightGraph: Supply Chain AI")
st.markdown("""
Ask questions about **Shipments**, **Exceptions** (Rolling), **Customer Sentiment**, and **Operational Issues**.
*Tip: Ask questions one at a time for the best results.*
""")

# ==========================================
# 2. SIDEBAR & CONNECTION SETTINGS
# ==========================================
with st.sidebar:
    st.header("🔌 Connection")
    
    # Pre-filled with your AuraDB details
    neo4j_url = st.text_input("Neo4j URI", value="neo4j+s://f99fdccf.databases.neo4j.io")
    neo4j_user = st.text_input("Username", value="neo4j")
    
    # Password hidden but ready for you to paste
    neo4j_password = st.text_input("Password", type="password", value="") 
    
    st.divider()
    
    gemini_key = st.text_input("Google API Key", type="password")
    
    # Using your specific model
    model_name = st.text_input("Model Name", value="gemini-2.5-flash")
    
    st.caption("Status: Waiting for credentials...")

# ==========================================
# 3. THE BRAIN: CUSTOM PROMPT (Business Logic)
# ==========================================
# FIX: Literal curly braces for Cypher are escaped as {{ }} 
# Real variables like {schema} and {question} remain single { }
CYPHER_GENERATION_TEMPLATE = """
Task: Generate Cypher statement to query a graph database.
Instructions:
1. Use only the provided relationship types and properties in the schema.
2. Do not use any other relationship types or properties that are not provided.
3. MAPPING RULES (Crucial):
   - If user asks about "Rolling", "Rolled", or "Delay", use: WHERE e.type = 'rolling_at_origin'
   - If user asks about "Sentiment", look for (:SentimentScore {{label: 'Negative'/'Positive'}})
   - If user asks about "Issues", look for (:Issue) connected via [:HAS_ISSUE] to a Shipment.
   - If user asks "What are they saying" or "Summarize", return the `content` property of the `Chat` node.

4. Fuzzy Matching: For Customer/Port names, always use `toLower(c.name) CONTAINS toLower('partial_name')`.

Schema:
{schema}

Examples:
# Q: Which ports have the highest number of rolling exceptions?
MATCH (p:Port)<-[:OCCURS_AT]-(e:Exception)
WHERE e.type = 'rolling_at_origin'
RETURN p.name, count(e) AS Count ORDER BY Count DESC LIMIT 5

# Q: What are the most common operational issues for Negative sentiment?
MATCH (ss:SentimentScore {{label: 'Negative'}})<-[:HAS_SENTIMENT]-(s:Shipment)-[:HAS_ISSUE]->(i:Issue)
RETURN i.name AS Issue, count(s) AS Frequency ORDER BY Frequency DESC LIMIT 5

# Q: Summarize complaints from Hogewoning
MATCH (c:Customer)-[:BOOKS]->(s:Shipment)-[:DISCUSSED_IN]->(ch:Chat)
WHERE toLower(c.name) CONTAINS 'hogewoning'
RETURN ch.content AS Chat_Logs LIMIT 10

The question is:
{question}
"""

CYPHER_PROMPT = PromptTemplate(
    input_variables=["schema", "question"], 
    template=CYPHER_GENERATION_TEMPLATE
)

# ==========================================
# 4. MAIN LOGIC
# ==========================================
if neo4j_password and gemini_key:
    try:
        # Connect to Neo4j
        graph = Neo4jGraph(url=neo4j_url, username=neo4j_user, password=neo4j_password)
        
        # Connect to Gemini
        llm = ChatGoogleGenerativeAI(
            model=model_name, 
            google_api_key=gemini_key, 
            temperature=0
        )

        # Create the "Brain" Chain
        chain = GraphCypherQAChain.from_llm(
            llm, 
            graph=graph, 
            verbose=True, 
            cypher_prompt=CYPHER_PROMPT, 
            allow_dangerous_requests=True
        )

        # Initialize Chat History
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Display Chat History
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input Box
        if prompt := st.chat_input("Ex: Which ports have the most rolling exceptions?"):
            # 1. Show User Message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # 2. Generate AI Response
            with st.chat_message("assistant"):
                with st.spinner("🔍 Analyzing Knowledge Graph..."):
                    try:
                        response = chain.invoke(prompt)
                        result = response['result']
                        
                        st.markdown(result)
                        st.session_state.messages.append({"role": "assistant", "content": result})
                        
                    except Exception as e:
                        st.error(f"Error: {e}")
                        st.info("Tip: Try simplifying the question or checking the customer name.")

    except Exception as e:
        st.sidebar.error(f"❌ Connection Failed: {e}")
else:
    st.sidebar.warning("👈 Enter Password & API Key to connect.")