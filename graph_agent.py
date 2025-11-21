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
    4.  Analyze the results and provide a comprehensive, detailed answer in natural language.
    5.  If a query returns an error or empty results, analyze the error, double-check the schema with `get_schema`, and try to correct the query.
    6.  You MUST check your generated Cypher query to ensure all labels, relationships, and properties EXACTLY match the schema. Do not misspell terms.

    **Response Guidelines:**
    - Provide COMPLETE, ELABORATE answers with all relevant details, statistics, and insights.
    - Include specific numbers, percentages, and comparisons when available.
    - Format your answers with clear structure using bullet points, numbered lists, or paragraphs as appropriate.
    - NEVER ask follow-up questions or suggest what the user might want to know next.
    - Always give a definitive answer based on the available data.
    - If data is limited, state what you found and acknowledge the limitation, but don't ask for clarification.

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
        """Runs the agent with a given question using a manual tool-use loop.

        Yields events during execution:
        - {"type": "tool_call", "name": str, "args": dict}
        - {"type": "tool_result", "name": str, "result": str}
        - {"type": "summary", "content": str}
        - {"type": "final_answer", "content": str}
        """
        messages = [HumanMessage(content=question)]
        tool_map = {tool.__name__: tool for tool in tools}
        max_turns = 5
        has_retrieved_schema = False

        for turn in range(max_turns):
            response = agent.invoke({"messages": messages})

            if not response.tool_calls:
                # Before final answer, show formulating message
                yield {"type": "summary", "content": "Preparing your answer..."}

                # Extract final answer
                content = response.content
                if isinstance(content, list) and content and isinstance(content[0], dict) and "text" in content[0]:
                    final_text = content[0]["text"]
                else:
                    final_text = str(content)

                # Stream the final answer
                yield {"type": "final_answer", "content": final_text}
                return

            messages.append(response)
            tool_messages = []

            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]

                # Yield tool call event
                yield {"type": "tool_call", "name": tool_name, "args": tool_args}

                if tool_name in tool_map:
                    try:
                        tool_function = tool_map[tool_name]
                        tool_result = tool_function(**tool_args)

                        # Yield tool result event
                        yield {"type": "tool_result", "name": tool_name, "result": str(tool_result)}

                        tool_messages.append(
                            ToolMessage(content=str(tool_result), name=tool_name, tool_call_id=tool_call["id"])
                        )

                        # Track if we've retrieved schema
                        if tool_name == "get_schema":
                            has_retrieved_schema = True

                    except Exception as e:
                        error_msg = f"Error executing tool '{tool_name}': {e}"
                        yield {"type": "tool_result", "name": tool_name, "result": error_msg, "error": True}
                        tool_messages.append(
                            ToolMessage(content=error_msg, name=tool_name, tool_call_id=tool_call["id"])
                        )
                else:
                    error_msg = f"Error: Agent tried to use an unknown tool '{tool_name}'"
                    yield {"type": "tool_result", "name": tool_name, "result": error_msg, "error": True}
                    tool_messages.append(
                        ToolMessage(content=error_msg, name=tool_name, tool_call_id=tool_call["id"])
                    )

            messages.extend(tool_messages)

            # Show summary based on what just happened
            if has_retrieved_schema and turn == 0:
                yield {"type": "summary", "content": "Building query based on schema..."}
            else:
                yield {"type": "summary", "content": "Processing results..."}

        yield {"type": "final_answer", "content": "The agent could not reach a final answer after multiple steps."}
        
    return agent_runner, db_tools