import json
import os
import sys


from splunk.persistconn.application import PersistentServerConnectionApplication

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import exec_anaconda

exec_anaconda.exec_anaconda_or_die()

with open("/Users/gburgett/Downloads/tnsys.log", "w") as ofile:
    ofile.write("%s\n" % sys.path)

from io import StringIO


from temporal_network import TemporalNetwork


def fix_node_name(v):
    new_v = str(v)
    if str(v)[0].isdigit():
        new_v = "n_" + str(v)
    if new_v[0] == '_':
        new_v = "n_" + str(v)
    if '-' in new_v:
        new_v = new_v.replace('-', '_')
    return new_v


class RestHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        """
        The base handler method, inheriting from PersistentServerConnectionApplication

        Args:
            in_string (str): a JSON string containing information about the request

        Returns:
            The return value, as decided by the handler method that this method delegates to
        """
        try:
            request = json.loads(in_string)
            request_payload = request["form"][0][1]
            payload_file = StringIO(request_payload)
            tempnet = TemporalNetwork().read_file(payload_file, timestamp_format='%Y-%m-%dT%H:%M:%S.%f%z')

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

            with open("/Users/gburgett/Downloads/tn.log", "w") as ofile:
                ofile.write("%s\n" % in_string)

            return {"payload": "%s" % json.dumps(network_data), "status": 200}
        except Exception as e:
            # logger.debug(e)
            return {'payload': 'Internal REST handler error %s' % e, 'status': 500}

        # method = request['method']

        # if method == "POST":
        #     try:
        #         # request_payload = request.get("body", "")
        #         # payload_file = StringIO(request_payload)
        #         # tempnet = TemporalNetwork().read_file(request_payload, timestamp_format='%Y-%m-%d %H:%M:%S')

        #         # network_data = {
        #         #     'nodes': [{'id': fix_node_name(v),
        #         #               'group': 1} for v in tempnet.nodes],
        #         #     'links': [{'source': fix_node_name(s),
        #         #                'target': fix_node_name(v),
        #         #                'width': 1,
        #         #                'time': t,
        #         #                'group': fix_node_name(g)} for s, v, t, g in tempnet.tedges
        #         #               ]
        #         # }

        #         return {"payload": in_string, "status": 200}

        #     except Exception as e:
        #         logger.debug(e)
        #         return {'payload': 'Internal REST handler error', 'status': 500}
        # else:
        #     return {'payload': 'Unsupported method: %s' % method, 'status': 405}
