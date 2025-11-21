import os
from neo4j import GraphDatabase
from typing import List

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# --- 1. Define Agent Tools ---

class Neo4jTools:
    """Tools to interact with the Neo4j database."""
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def get_schema(self):
        """Returns the database schema. No arguments needed."""
        try:
            with self._driver.session() as session:
                meta_query = "CALL db.schema.visualization()"
                result = session.run(meta_query)
                return [r.data() for r in result]
        except Exception as e:
            return f"Error getting schema: {e}"

    def run_query(self, query: str):
        """Runs a Cypher query against the database."""
        try:
            with self._driver.session() as session:
                result = session.run(query)
                return [r.data() for r in result]
        except Exception as e:
            return f"Error running query: {e}"

# --- 2. Agent Factory Function ---

def create_agent_runner(neo4j_uri, neo4j_user, neo4j_password, gemini_key):
    """
    Creates and returns a runnable agent function.
    The agent and its tools are initialized here using the provided credentials.
    """
    # Instantiate tools with user-provided credentials
    db_tools = Neo4jTools(neo4j_uri, neo4j_user, neo4j_password)
    tools = [db_tools.get_schema, db_tools.run_query]
    
    # Initialize the LLM with user-provided key
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0, google_api_key=gemini_key)

    system_prompt = """You are an expert Neo4j data analyst. Your goal is to answer user questions by converting them into Cypher queries and executing them against a shipping logistics database.

    **Instructions:**
    1.  First, understand the user's question.
    2.  If you are unsure about the graph structure, you must use the `get_schema` tool.
    3.  Construct a valid Cypher query and use the `run_query` tool to execute it.
    4.  Analyze the results and provide a clear, natural language answer.
    5.  If a query returns an error or empty results, analyze the error, double-check the schema with `get_schema`, and try to correct the query.
    6.  You MUST check your generated Cypher query to ensure all labels, relationships, and properties EXACTLY match the schema. Do not misspell terms.

    **SCHEMA INFORMATION:**
    - **Nodes:** `Customer`, `Shipment`, `Port`, `Carrier`, `Vessel`, `Exception`, `Issue`, `SentimentScore`.
    - **Relationships:** `BOOKS`, `LOADS_AT`, `DISCHARGES_AT`, `CARRIED_BY`, `HAS_SENTIMENT`, `HAS_ISSUE`.
    """

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("placeholder", "{messages}"),
        ]
    )

    # Create the agent chain
    agent = prompt | llm.bind_tools(tools)
    
    # This is the function that will be returned and used by the UI
    def agent_runner(question: str):
        """Runs the agent with a given question using a manual tool-use loop."""
        messages = [HumanMessage(content=question)]
        tool_map = {tool.__name__: tool for tool in tools}
        max_turns = 5
        for _ in range(max_turns):
            response = agent.invoke({"messages": messages})
            if not response.tool_calls:
                content = response.content
                if isinstance(content, list) and content and isinstance(content[0], dict) and "text" in content[0]:
                    return content[0]["text"]
                return str(content)

            messages.append(response)
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                if tool_name in tool_map:
                    try:
                        tool_function = tool_map[tool_name]
                        tool_result = tool_function(**tool_args)
                        tool_messages.append(
                            ToolMessage(content=str(tool_result), name=tool_name, tool_call_id=tool_call["id"])
                        )
                    except Exception as e:
                        tool_messages.append(
                            ToolMessage(content=f"Error executing tool '{tool_name}': {e}", name=tool_name, tool_call_id=tool_call["id"])
                        )
                else:
                    tool_messages.append(
                        ToolMessage(content=f"Error: Agent tried to use an unknown tool '{tool_name}'", name=tool_name, tool_call_id=tool_call["id"])
                    )
            messages.extend(tool_messages)
        return "The agent could not reach a final answer after multiple steps."
        
    return agent_runner, db_tools