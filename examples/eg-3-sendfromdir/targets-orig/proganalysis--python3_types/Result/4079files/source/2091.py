import math
from io import StringIO
from typing import List
from urllib.parse import unquote
import uuid

from daft import Node, PGM
from flask import Flask, request, Response, send_from_directory


app = Flask(__name__)


@app.route('/static/<path:path>')
def static_file(path):
    return send_from_directory('static', path)


@app.route('/render')
def render():
    # Retrieve generation code and wrap in required boilerplate
    import datetime
    print(datetime.datetime.utcnow())
    print(request.args)
    generation_code = request.args.get('code')
    if not generation_code:
        print('No generation code given')
        return Response('', mimetype='image/svg+xml')
    generation_code = unquote(generation_code)
    generation_code = generation_code.replace('\n', '\n    ')
    code_wrapper = f'''\
# Define objects and modules that generation code can use
helpers = GraphGenerationHelpers()
from daft import PGM, Node

def generate():
    {generation_code}
    return g

graph = generate()'''

    # Run generation code supplied by the user
    print(f'Running code:\n{code_wrapper}')
    exec(code_wrapper, globals())

    # Render the resulting SVG file and return it
    svg_buffer = StringIO()
    graph.render().figure.savefig(svg_buffer, format='svg')
    svg = svg_buffer.getvalue()

    return Response(svg, mimetype='image/svg+xml')


class GraphGenerationHelpers:

    def layer(self,
              graph: PGM,
              node_texts: List[str],
              x: float,
              y: float,
              spacing: float=1,
              spacing_pow: float=1,
              **other_node_params) -> List[Node]:
        nodes = [
            Node(
                str(uuid.uuid4()),
                node_texts[i],
                x,
                y - (spacing * float(i)),
                **other_node_params)
            for i in range(len(node_texts))]
        for node in nodes:
            graph.add_node(node)
        return nodes

    def fully_connect(self,
                      graph: PGM,
                      layer1: List[Node],
                      layer2: List[Node]):
        for l1_node in layer1:
            for l2_node in layer2:
                graph.add_edge(l1_node.name, l2_node.name)

    def add_label(self,
                  graph: PGM,
                  text: str,
                  x: float,
                  y: float,
                  label_id: str=None,
                  color: str=None,
                  size: str=None,
                  weight: str=None):
        if label_id is None:
            label_id = str(uuid.uuid4())
        graph.add_node(Node(
            label_id, text, x, y,
            plot_params={
                'fill': False,
                'linewidth': 0.0
            },
            label_params={
                'color': color or 'black',
                'size': size or 'small',
                'weight': weight or 'normal'
            }))

    def add_label_range(self,
                        graph: PGM,
                        labels: List[str],
                        x: float,
                        y: float,
                        spacing: float=1,
                        spacing_exp: float=1,
                        direction: str='H',  # Horizontal or Vertical
                        overrides: dict=None,
                        **other_label_args):
        n_labels = len(labels)
        if direction == 'H':
            coordinates = [(x + (spacing * float(i)), y) for i in range(n_labels)]
        elif direction == 'V':
            coordinates = [
                (x, y - math.pow(spacing * float(i), spacing_exp))
                for i in range(n_labels)
            ]
        else:
            raise ValueError(f'Invalid direction: {direction}')

        overrides = overrides or {}

        for i in range(n_labels):
            label_text = labels[i]
            label_args = dict(other_label_args)
            label_overrides = overrides.get(label_text, {})
            for key, value in label_overrides.items():
                label_args[key] = value
            self.add_label(
                graph, label_text, coordinates[i][0], coordinates[i][1],
                **label_args)
