#!/usr/bin/env python3
from graphviz import Digraph

# Create a directed graph
dfd = Digraph('Level_1_DFD', format='svg')
dfd.attr(rankdir='LR', size='8,5')

# External Entities
dfd.node('User', 'User', shape='rectangle')
dfd.node('Unsplash', 'Unsplash API', shape='rectangle')
dfd.node('LLM', 'Gemma3 LLM', shape='rectangle')

# Processes
dfd.node('P1', 'P1: Receive & Validate Input', shape='circle')
dfd.node('P2', 'P2: Match Recipes', shape='circle')
dfd.node('P3', 'P3: Generate Output', shape='circle')

# Data Stores
dfd.node('D1', 'D1: Recipe DB', shape='cylinder')
dfd.node('D2', 'D2: FAISS Index', shape='cylinder')

# Data Flows
dfd.edge('User', 'P1', 'Ingredients ')
dfd.edge('P1', 'D1', 'Cleaned Ingredient List')
dfd.edge('P1', 'D2', 'Token List')
dfd.edge('D2', 'P2', 'Top-15 Recipe IDs')
dfd.edge('D1', 'P2', 'Recipe Records')
dfd.edge('P2', 'P3', 'Top-5 Results')
dfd.edge('P3', 'Unsplash', 'Unsplash Query')
dfd.edge('Unsplash', 'P3', 'Image URLs')
dfd.edge('P3', 'LLM', 'LLM Prompt')
dfd.edge('LLM', 'P3', 'Generated Recipe')
dfd.edge('P3', 'User', 'Recipe List + Thumbnails')

# Render to file (creates Level_1_DFD.svg)
output_path = dfd.render(directory='.', cleanup=True)
print(f"DFD diagram written to {output_path}")
