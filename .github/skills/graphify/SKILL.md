---
name: graphify
description: "Use for codebase navigation, architecture mapping, and contextual reasoning. Generates a persistent knowledge graph with AST structural extraction, community detection, and query tools to optimize token consumption."
argument-hint: "Specify command, query, or subfolder to graphify (e.g. 'query \"How does hybrid search work?\"')"
---

# Graphify Skill

> **Official package:** The PyPI package is `graphifyy` (double-y). Other `graphify*` packages on PyPI are not affiliated. The CLI command is still `graphify`.

Graphify transforms the multimodal RAG codebase and documentation into a navigable knowledge graph with AST code extraction, community clustering, and token-efficient GraphRAG queries.

## Capabilities & Workflows

1. **Graph Construction (`graphify .`):**
   - Parses code AST (Python, TypeScript, CSS) and markdown documentation without consuming unnecessary LLM tokens.
   - Detects god nodes, component relationships, dependencies between Clean Architecture layers, and cross-file data flows.
   - Outputs:
     - `graphify-out/graph.json`: GraphRAG-ready node and edge data.
     - `graphify-out/graph.html`: Interactive visualization of the architecture.
     - `graphify-out/GRAPH_REPORT.md`: Comprehensive plain-text graph report and cluster summaries.

2. **Token-Efficient Querying (`graphify query "<question>"`):**
   - Uses Breadth-First Search (BFS) or Depth-First Search (DFS) graph traversal to retrieve only relevant connected nodes and relationships.
   - Drastically reduces context window usage by preventing whole-codebase dumps into LLM prompts.

3. **Path and Node Explanation:**
   - `graphify path "<source_node>" "<target_node>"`: Identifies architectural dependencies and call chains between components.
   - `graphify explain "<node_name>"`: Provides context, degree centrality, and relations for any specific module or class.

## Usage Commands

```bash
# Full graph generation on current repository
backend/.venv/bin/python3 -m graphify.cli .

# Query graph to minimize token usage
backend/.venv/bin/python3 -m graphify.cli query "Where is the RRF search logic implemented?"

# Find path between two modules
backend/.venv/bin/python3 -m graphify.cli path "DocumentsRoute" "QdrantAdapter"

# Run with custom token budget
backend/.venv/bin/python3 -m graphify.cli query "Trace document upload streaming" --budget 1500
```
