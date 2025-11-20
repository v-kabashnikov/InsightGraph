from streamlit_agraph import Node, Edge

def get_nodes_and_edges(neo4j_graph, cypher_query):
    """
    Robust Visualizer: Uses a Dictionary to enforce Strict Uniqueness on Node IDs.
    Filters edges to ensure they only connect to valid, existing nodes.
    """
    try:
        # Use the internal driver to get Raw Objects
        with neo4j_graph._driver.session() as session:
            result = session.run(cypher_query)
            
            nodes_dict = {} 
            edges_list = []
            
            for record in result:
                for val in record.values():
                    
                    # --- Parse Nodes ---
                    if hasattr(val, 'labels'): 
                        node_id = getattr(val, 'element_id', str(val.id))
                        
                        if node_id not in nodes_dict:
                            label = list(val.labels)[0] if val.labels else "Node"
                            props = dict(val)
                            name = props.get('name') or props.get('id') or props.get('type') or label
                            
                            # Color Logic
                            color = "#FF6B6B" if label == "Exception" else \
                                    "#4ECDC4" if label == "Customer" else \
                                    "#FFE66D" if label == "Port" else \
                                    "#95A5A6" # Default grey
                                    
                            nodes_dict[node_id] = Node(id=node_id, label=name, size=25, color=color)
                    
                    # --- Parse Relationships ---
                    elif hasattr(val, 'type') and hasattr(val, 'start_node') and hasattr(val, 'end_node'):
                        source_id = getattr(val.start_node, 'element_id', str(val.start_node.id))
                        target_id = getattr(val.end_node, 'element_id', str(val.end_node.id))
                        edges_list.append(Edge(source=source_id, target=target_id, label=val.type))
            
            # CRITICAL FIX: Only return edges if both nodes actually exist in our list
            # This prevents "undefined" errors in the frontend if a relationship exists but its nodes weren't returned
            valid_edges = [
                edge for edge in edges_list 
                if edge.source in nodes_dict and edge.target in nodes_dict
            ]
            
            return list(nodes_dict.values()), valid_edges

    except Exception as e:
        print(f"Viz Error: {e}")
        return [], []