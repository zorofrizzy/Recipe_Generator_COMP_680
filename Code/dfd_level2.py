#!/usr/bin/env python3
from graphviz import Digraph

# Color palette
ENTITY_FILL   = '#8da0cb'  # blue (for inputs/outputs)
PROCESS_FILL  = '#fc8d62'  # orange (for each subprocess)
STORE_FILL    = '#66c2a5'  # green (for data stores)
EDGE_COLOR    = '#5f5f5f'
FONT_COLOR    = 'black'

dfd = Digraph('L2_P2_MatchRecipes', format='png')


# bump resolution & canvas
dfd.graph_attr.update(
    rankdir='LR',
    size='12,7',    # wider canvas
    dpi='300',      # high resolution
    splines='ortho',
    bgcolor='white'
)
dfd.attr('node', fontcolor='black')

# Graph and default node settings
dfd.attr(rankdir='LR', splines='ortho', bgcolor='white', size='8,4')
dfd.attr('node', fontcolor=FONT_COLOR)

# “Entity” nodes
dfd.node('Tokens',    'Input:\nTokens',  shape='rectangle', style='filled', fillcolor=ENTITY_FILL)
dfd.node('Top5',      'Output:\nTop-5 Results', shape='rectangle', style='filled', fillcolor=ENTITY_FILL)

# Data stores
dfd.node('D2', 'D2: FAISS Index', shape='cylinder', style='filled', fillcolor=STORE_FILL)
dfd.node('D1', 'D1: Recipe DB',   shape='cylinder', style='filled', fillcolor=STORE_FILL)

# Sub‐processes
dfd.node('P21', '2.1 FAISS Similarity Search\n(query D2 → 15 IDs)',
         shape='circle', style='filled', fillcolor=PROCESS_FILL)
dfd.node('P22', '2.2 Fetch Full Records\n(IDs → D1)',
         shape='circle', style='filled', fillcolor=PROCESS_FILL)
dfd.node('P23', '2.3 Overlap Scoring\n(string-match)',
         shape='circle', style='filled', fillcolor=PROCESS_FILL)
dfd.node('P24', '2.4 Sort & Select Top-5',
         shape='circle', style='filled', fillcolor=PROCESS_FILL)

# Edges / data flows
flows = [
    ('Tokens', 'P21',   'Tokens'),
    ('P21',    'NeighborIDs', 'Neighbor IDs'),
    ('NeighborIDs', 'P22',    ''),  # intermediate unlabeled node for clarity
    ('P22',    'FullRecs',    'Full Records'),
    ('FullRecs','P23',        ''),
    ('P23',    'ScoredList',  'Scored List'),
    ('ScoredList','P24',      ''),
    ('P24',    'Top5',        '')
]

# Because Graphviz needs explicit nodes for those intermediate labels, add them:
dfd.node('NeighborIDs', '15 Neighbor IDs', shape='plaintext')
dfd.node('FullRecs',    'Full Recipe Records', shape='plaintext')
dfd.node('ScoredList',  'Scored List', shape='plaintext')

for src, dst, label in flows:
    dfd.edge(src, dst, label=label, color=EDGE_COLOR)

# Render PNG
output = dfd.render(filename='Level_2_P2_DFD', directory='.', cleanup=True)
print(f"Generated diagram at {output}")
