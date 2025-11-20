import streamlit as st
import requests

def setup_page():
    st.set_page_config(page_title="InsightGraph AI", layout="wide", page_icon="🧠")

def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200: return None
        return r.json()
    except: return None

# Animation URL
LOTTIE_URL = "https://lottie.host/5a68dd14-652c-45b8-946e-545be4eb6cb2/9Q2k5z9Z7s.json"

# --- THE BRAIN (PROMPT) ---
# Edit this file to change how the AI behaves!
CYPHER_GENERATION_TEMPLATE = """
Task: Generate Cypher statement to query a graph database.
Instructions:
1. Use only the provided relationship types and properties in the schema.
2. MAPPING RULES:
   - "Rolling"/"Delay" -> WHERE e.type = 'rolling_at_origin'
   - "Sentiment" -> (:SentimentScore {{label: 'Negative'/'Positive'}})
   - "Issues" -> (:Issue) connected via [:HAS_ISSUE]
   - "Summarize"/"Saying" -> Return `content` property of `Chat` node.
3. Fuzzy Matching: Use `toLower(c.name) CONTAINS toLower('partial_name')`.
4. LIMIT: Always LIMIT 50 to prevent huge result sets unless asked otherwise.

Schema:
{schema}

The question is:
{question}
"""