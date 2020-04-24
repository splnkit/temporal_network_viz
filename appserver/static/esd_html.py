
from functools import singledispatch
import json
import os
import string
from string import Template
import random

import numpy as _np
from esd_temporal_network import TemporalNetwork

@singledispatch
def generate_html(network, **params):
    print("generate_html")
    # I have not figured it all out yet but this method isn't actually called. Seems the one dispached is the one below,
    # _generate_html_tempnet...
    
    """
    Generates an HTML snippet that contains an interactive d3js visualization
    of the given instance. This function supports instances of pathpy.Network,
    pathpy.TemporalNetwork, pathpy.HigherOrderNetwork, pathpy.Paths, and pathpy.Paths.
    
    Parameters:
    -----------
        network: Network, TemporalNetwork, HigherOrderNetwork, MultiOrderModel, Paths
            The pathpy object that should be visualised.
        params: dict
            A dictionary with visualization parameters to be passed to the HTML
            generation function. These parameters can be processed by custom
            visualisation templates extendable by the user. For supported parameters
            see docstring of plot.
    """
    
    assert isinstance(network, Network),\
        "Argument must be an instance of Network"

    hon = None
    mog = None

    # prefix nodes starting with number as such IDs are not supported in HTML5
    def fix_node_name(v):
        if str(v)[0].isdigit():
            return "n_" + str(v)
        return str(v)

    # function to assign node/edge attributes based on params
    def get_attr(key, attr_name, attr_default):
        # If parameter does not exist assign default
        if attr_name not in params:
            return attr_default
        # if parameter is a scalar, assign the specified value
        elif isinstance(params[attr_name], type(attr_default)):
            return params[attr_name]
        # if parameter is a dictionary, assign node/edge specific value
        elif isinstance(params[attr_name], dict):
            if key in params[attr_name]:
                return params[attr_name][key]
            # ... or default value if node/edge is not in dictionary
            else:
                return attr_default
        # raise exception if parameter is of unexpected type
        else:
            raise Exception(
                'Edge and node attribute must either be dict or {0}'.format(type(attr_default))
                )

    def compute_weight(network, e):
        """
        Calculates a normalized force weight for an edge in a network
        """
        if 'force_weighted' in params and not params['force_weighted']:
            weight = network.edges[e]['degree']
            source_weight = network.nodes[e[0]]['indegree'] + network.nodes[e[0]]['outdegree']
            target_weight = network.nodes[e[1]]['indegree'] + network.nodes[e[1]]['outdegree']
        else:
            weight = network.edges[e]['weight']
            source_weight = network.nodes[e[0]]['inweight'] + network.nodes[e[0]]['outweight']
            target_weight = network.nodes[e[1]]['inweight'] + network.nodes[e[1]]['outweight']

        if isinstance(weight, _np.ndarray):
            weight = weight.sum()
            source_weight = source_weight.sum()
            target_weight = target_weight.sum()

        s = min(source_weight, target_weight)
        if s > 0.0:
            return weight / s
        else:
            return 0.0

    # Create network data that will be passed as JSON object
    network_data = {'links': [{'source': fix_node_name(e[0]),
                               'target': fix_node_name(e[1]),
                               'color': get_attr((e[0], e[1]), 'edge_color', '#999999'),
                               'width': get_attr((e[0], e[1]), 'edge_width', 0.5),
                               'weight': compute_weight(network, e) if hon is None and mog is None else 0.0
                              } for e in network.edges.keys()]
                   }
    
    network_data['nodes'] = [{'id': fix_node_name(v),
                              'text': get_attr(v, 'node_text', fix_node_name(v)),
                              'color': get_attr(v, 'node_color', '#99ccff'),
                              'size': get_attr(v, 'node_size', 5.0)} for v in network.nodes]

    # DIV params
    if 'height' not in params:
        params['height'] = 400

    if 'width' not in params:
        params['width'] = 400

    # label params
    if 'label_size' not in params:
        params['label_size'] = '8px'

    if 'label_offset' not in params:
        params['label_offset'] = [0, -10]

    if 'label_color' not in params:
        params['label_color'] = '#999999'

    if 'label_opacity' not in params:
        params['label_opacity'] = 1.0

    if 'edge_opacity' not in params:
        params['edge_opacity'] = 1.0

    # layout params
    if 'force_repel' not in params:
        params['force_repel'] = -200

    if 'force_charge' not in params:
        params['force_charge'] = -20

    if 'force_alpha' not in params:
        params['force_alpha'] = 0.0

    # arrows
    if 'edge_arrows' not in params:
            params['edge_arrows'] = 'true'
    else:
        params['edge_arrows'] = str(params['edge_arrows']).lower()

    if not network.directed:
        params['edge_arrows'] = 'false'

    # Create a random DIV ID to avoid conflicts within the same notebook
    div_id = "".join(random.choice(string.ascii_letters) for x in range(8))
    
    if 'd3js_path' not in params:
        params['d3js_path'] = 'https://d3js.org/d3.v4.min.js'

    d3js_params = {
        'network_data': json.dumps(network_data),
        'div_id': div_id,
    }

    # Read template file ... 
    with open('tempnet_template.html') as f:
        html_str = f.read()

    # substitute variables in template file
    html = Template(html_str).substitute({**d3js_params, **params})

    return html

@singledispatch
def export_html(network, filename, **params):
    # I have not figured it all out yet but this method isn't actually called. Seems the one dispached is the one below,
    # _export_html_tempnet...

    """
    Exports a stand-alone HTML file that contains an interactive d3js visualization
    of the given pathpy instance. function supports instances of pathpy.Network, 
    pathpy.TemporalNetwork, pathpy.HigherOrderNetwork, pathpy.Paths, and pathpy.Paths.

    Parameters
    ----------
    network: Network
        The network to visualize
    filename: string
        Path where the HTML file will be saved
    params: dict
        A dictionary with visualization parameters to be passed to the HTML
        generation function. These parameters can be processed by custom
        visualisation templates extendable by the user. For supported parameters
        see docstring of plot.
    """
    assert isinstance(network, Network), \
        "network must be an instance of Network"
    html = generate_html(network, **params)
    if 'template' not in params:
        html = '<!DOCTYPE html>\n<html><body>\n' + html + '</body>\n</html>'
    with open(filename, 'w+') as f:
        f.write(html)


@generate_html.register(TemporalNetwork)
def _generate_html_tempnet(tempnet, **params):
    # prefix nodes starting with number
    def fix_node_name(v):
        new_v = str(v)
        if str(v)[0].isdigit():
            new_v = "n_" + str(v)
        if new_v[0] == '_':
            new_v = "n_" + str(v)
        if '-' in new_v:
            new_v = new_v.replace('-', '_')
        return new_v

    network_data = {
        'nodes': [{'id': fix_node_name(v),
                   'group': 1} for v in tempnet.nodes],
        'links': [{'source': fix_node_name(s),
                   'target': fix_node_name(v),
                   'width': 1,
                   'time': t,
                   'group': fix_node_name(g)} for s, v, t, g in tempnet.tedges
                 ]
    }

    with open('tempnet_template.html') as f:
        html_str = f.read()

    d3js_params = {
        'network_data': json.dumps(network_data),
    }

    # substitute variables in template file
    html = Template(html_str).substitute({**d3js_params, **params})

    return html


@export_html.register(TemporalNetwork)
def _export_html_tempnet(tempnet, filename, **params):
    html = generate_html(tempnet, **params)

    # for the inner HTML generated from the default templates, we add the surrounding DOCTYPE
    # and body needed for a stand-alone HTML file.
    if 'template' not in params:
        html = '<!DOCTYPE html>\n<html><body>\n' + html + '</body>\n</html>'
    with open(filename, 'w+') as f:
        f.write(html)
        