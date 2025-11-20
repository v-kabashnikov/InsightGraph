from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
import config

def get_graph_chain(url, user, password, api_key, model_name):
    """Initializes the Neo4j Graph and the LangChain QA Chain."""
    
    # 1. Connect to Graph
    graph = Neo4jGraph(url=url, username=user, password=password)
    
    # 2. Connect to Gemini
    llm = ChatGoogleGenerativeAI(
        model=model_name, 
        google_api_key=api_key, 
        temperature=0
    )

    # 3. Load Prompt from Config
    PROMPT = PromptTemplate(
        input_variables=["schema", "question"], 
        template=config.CYPHER_GENERATION_TEMPLATE
    )

    # 4. Build Chain
    chain = GraphCypherQAChain.from_llm(
        llm, 
        graph=graph, 
        verbose=True, 
        cypher_prompt=PROMPT, 
        allow_dangerous_requests=True,
        return_intermediate_steps=True 
    )
    
    return graph, chain