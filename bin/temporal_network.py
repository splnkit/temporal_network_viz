# -*- coding: utf-8 -*-

import sys
from collections import defaultdict
import bisect
import datetime
from time import mktime

import numpy as _np

# from esd_log import Log, Severity


class TemporalNetwork:
    """
      This class represents a sequence of time-stamped edges.
      Instances of this class can be used to generate path statistics
      based on the time-respecting paths resulting from a given maximum
      time difference between consecutive time-stamped edges.
    """

    def __init__(self, tedges=None):
        """Constructor that generates a temporal network instance.

        Parameters
        ----------
        tedges:
            an optional list of directed time-stamped edges from which to construct a
            temporal network instance. For the default value None an empty temporal
            network will be created.
        """
        # A list of time-stamped edges of this temporal network
        self.tedges = []

        # A list of nodes of this temporal network
        self.nodes = []

        # A dictionary storing all time-stamped links, indexed by time-stamps
        self.time = defaultdict(lambda: list())
        
        # A dictionary storing all time-stamped links, indexed by time and target node
        self.targets = defaultdict(lambda: dict())

        # A dictionary storing all time-stamped links, indexed by time and source node
        self.sources = defaultdict(lambda: dict())

        # A dictionary storing time stamps at which links (v,*;t) originate from node v
        self.activities = defaultdict(lambda: list())

        # A dictionary storing sets of time stamps at which links (v,*;t) originate from
        # node v
        # Note that the insertion into a set is much faster than repeatedly checking
        # whether an element already exists in a list!
        self.activities_sets = defaultdict(lambda: set())

        # An ordered list of time-stamps
        self.ordered_times = []

        nodes_seen = defaultdict(lambda: False)
        # print("tedges: ", str(tedges))

        if tedges is not None:
            # Log.add('Building index data structures ...')

            for e in tedges:
                # print("e[0]: ", str(e[0]))
                # print("e[1]: ", str(e[1]))
                # print("e[2]: ", str(e[2]))
                self.activities_sets[e[0]].add(e[2])
                self.time[e[2]].append(e)
                self.targets[e[2]].setdefault(e[1], []).append(e)
                self.sources[e[2]].setdefault(e[0], []).append(e)
                if not nodes_seen[e[0]]:
                    nodes_seen[e[0]] = True
                if not nodes_seen[e[1]]:
                    nodes_seen[e[1]] = True
            self.tedges = tedges
            self.nodes = list(nodes_seen.keys())

            # Log.add('Sorting time stamps ...')

            self.ordered_times = sorted(list(self.time.keys()))
            for v in self.nodes:
                self.activities[v] = sorted(self.activities_sets[v])
                # print("Activities: ", str(self.activities[v])) 
            # Log.add('finished.')

    @classmethod
    def read_file(cls, filename, separator=',', directed=True,
                  timestamp_format='%Y-%m-%d %H:%M:%S', maxlines=sys.maxsize, time_rescale=1):
        """
        Reads time-stamped links from a file and returns a new instance of the class
        TemporalNetwork. The file is assumed to have a header

                source target time

        where columns can be in arbitrary order and separated by arbitrary characters.
        Each time-stamped link must occur in a separate line and links are assumed to be
        directed.

        The time column can be omitted and in this case all links are assumed to occur
        in consecutive time stamps (that have a distance of one). Time stamps can be
        simple integers, or strings to be converted to UNIX time stamps via a custom
        timestamp format. For this, the python function datetime.strptime will be used.

        Parameters
        ----------
        filename: str
            path of the file to read from
        sep: str
            the character that separates columns (default ',')
        directed: bool
            whether to read edges as directed (default True)
        timestamp_format: str
            used to convert string timestamps to UNIX timestamps. This parameter is
            ignored, if timestamps are digit types (like a simple int).
            The default is '%Y-%m-%d %H:%M'
        maxlines: int
            limit reading of file to a given number of lines (default sys.maxsize)
        time_rescale: int
            can be used to rescale integer timestamps by dividing each time stamp by 
            time_rescale. This is useful for high-resolution data with a sampling 
            interval larger than one second. Default is 1.

        Returns
        -------

        """
        assert (filename != ''), 'Empty filename given'

        # Read header
        f = filename
        tedges = []

        header = f.readline()
        header = header.split(separator)

        # If header columns are included, arbitrary column orders are supported
        time_ix = -1
        source_ix = -1
        target_ix = -1
        for i in range(len(header)):
            header[i] = header[i].strip()
            if header[i] == 'node1' or header[i] == 'source':
                source_ix = i
            elif header[i] == 'node2' or header[i] == 'target':
                target_ix = i
            elif header[i] == 'time' or header[i] == 'timestamp':
                time_ix = i

        assert (source_ix >= 0 and target_ix >= 0), \
            "Detected invalid header columns: %s" % header

        # if time_ix < 0:  # pragma: no cover
            # Log.add('No time stamps found in data, assuming consecutive links',
            #        Severity.WARNING)

        # if not directed:
        #     Log.add('Reading undirected time-stamped links ...')
        # else:
        #     Log.add('Reading directed time-stamped links ...')

        line = f.readline()
        n = 1
        while line and n <= maxlines:
            fields = line.rstrip().split(separator)
            try:
                if time_ix >= 0:
                    timestamp = fields[time_ix]
                    # if the timestamp is a number, we use this
                    if timestamp.isdigit():
                        t = int(timestamp)
                    else:
                        # if it is a string, we use the timestamp format to convert
                        # it to a UNIX timestamp
                        x = datetime.datetime.strptime(timestamp, timestamp_format)
                        t = int(mktime(x.timetuple()))
                else:
                    t = n
                if t >= 0 and fields[source_ix] != '' and fields[target_ix] != '':
                    # add group so that we can use it for color
                    group = fields[source_ix]
                    tedge = (fields[source_ix], fields[target_ix], int(t/time_rescale), group)
                    tedges.append(tedge)
                    if not directed:
                        tedges.append((fields[target_ix], fields[source_ix], int(t/time_rescale), group))
                else:  # pragma: no cover
                    s_line = line.strip()
                    if fields[source_ix] == '' or fields[target_ix] == '':
                        msg = 'Empty node in line {0}: {1}'.format(n+1, s_line)
                    else: 
                        msg = 'Negative timestamp in line {0}: {1}'.format(n+1, s_line)
                    # Log.add(msg, Severity.WARNING)
            except (IndexError, ValueError):  # pragma: no cover
                s_line = line.strip()
                msg = 'Malformed line {0}: {1}'.format(n+1, s_line)
                # Log.add(msg, Severity.WARNING)
            line = f.readline()
            n += 1
        # end of with open()

        return cls(tedges=tedges)

    def write_file(self, filename, separator=','):
        """Writes the time-stamped edge list of this temporal network instance as CSV file

        Parameters
        ----------
        filename: str
            name of CSV file to save data to
        separator: str
            character used to separate columns in generated CSV file

        Returns
        -------

        """
        msg = 'Writing {0} time-stamped edges to file {1}'.format(self.ecount(), filename)
        # Log.add(msg, Severity.INFO)
        with open(filename, 'w+') as f:
            f.write('source' + separator + 'target' + separator + 'time' + '\n')
            for time in self.ordered_times:
                for (v, w, t) in self.time[time]:
                    f.write(str(v) + separator + str(w) + separator + str(t)+'\n')


    def filter_nodes(self, nodes):
        """Returns a copy of the temporal network where time-stamped edges are filtered 
        according to a given set of nodes.

        Parameters
        ----------
        node_filter: iterable
            a list or set of nodes that shall be included in the returned temporal network

        Returns
        -------
        """
        def edge_filter(v, w, t):
            if v in nodes and w in nodes: 
                return True
            return False

        return self.filter_edges(edge_filter)

    def filter_edges(self, edge_filter):
        """Returns a copy of the temporal network where time-stamped edges are filtered 
        according to a given filter expression. This can be used, e.g., to create time 
        slice networks by filtering edges within certain time windows, or to reduce a 
        temporal network to interactions between a subset of nodes.

        Parameters
        ----------
        edge_filter: callable
            an arbitrary filter function of the form filter_func(v, w, time) that returns
            True for time-stamped edges that shall pass the filter, and False for time-stamped
            edges that shall be filtered out.

        Returns
        -------

        """
        # Log.add('Starting filtering ...', Severity.INFO)
        new_t_edges = []

        for (v, w, t) in self.tedges:
            if edge_filter(v, w, t):
                new_t_edges.append((v, w, t))

        n_filtered = self.ecount() - len(new_t_edges)
        msg = 'finished. Filtered out {} time-stamped edges.'.format(n_filtered)
        # Log.add(msg,  Severity.INFO)

        return TemporalNetwork(tedges=new_t_edges)

    def add_edge(self, source, target, ts, directed=True, timestamp_format='%Y-%m-%d %H:%M:%S'):
        """Adds a time-stamped edge (source,target;time) to the temporal network.
        Unless specified otherwise, time-stamped edges are assumed to be directed.

        Parameters
        ----------
        source:
            name of the source node of a directed, time-stamped link
        target:
            name of the target node of a directed, time-stamped link
        ts: int
            time-stamp of the time-stamped link
        directed: bool
        timestamp_format: string
            if timestamps are passed as strings, the following timestamp format is used 
            to parse the timestamps in order to obtain UNIX timestamps (seconds since 1970).

        Returns
        -------

        """
        assert isinstance(ts, int) or isinstance(ts, str), 'Timestamp must either be string or int' 

        if isinstance(ts, str):
            if ts.isdigit():
                t = int(ts)
            else:
                # if it is a string, we use the timestamp format to convert
                # it to a UNIX timestamp
                x = datetime.datetime.strptime(ts, timestamp_format)
                t = int(mktime(x.timetuple()))
        else:
            t = ts

        e = (source, target, t)
        self.tedges.append(e)
        if source not in self.nodes:
            self.nodes.append(source)
        if target not in self.nodes:
            self.nodes.append(target)

        # Add edge to index structures
        self.time[t].append(e)
        self.targets[t].setdefault(target, []).append(e)
        self.sources[t].setdefault(source, []).append(e)

        if t not in self.activities[source]:
            self.activities[source].append(t)
            self.activities[source].sort()

        # Maintain order of time stamps
        index = bisect.bisect_left(self.ordered_times, t)
        # add if ts is not already in list
        if index == len(self.ordered_times) or self.ordered_times[index] != t:
            self.ordered_times.insert(index, t)

        # make edge undirected by adding another directed edge
        if not directed:
            self.add_edge(target, source, t)

    def vcount(self):
        """Returns the number of vertices in the temporal network.
        This number corresponds to the number of nodes in the (first-order)
        time-aggregated network.
        """

        return len(self.nodes)

    def ecount(self):
        """Returns the number of time-stamped edges (u,v;t) in the temporal network.
        This number corresponds to the sum of link weights in the (first-order)
        time-aggregated network.
        """

        return len(self.tedges)

    def observation_length(self):
        """Returns the length of the observation time in time units."""

        return max(self.ordered_times)-min(self.ordered_times)

    def inter_event_times(self):
        """
        Returns an array containing all time differences between any
        two consecutive time-stamped links (involving any node)
        """
        time_diffs = []
        for i in range(1, len(self.ordered_times)):
            time_diffs += [self.ordered_times[i] - self.ordered_times[i-1]]
        return _np.array(time_diffs)

    def inter_path_times(self):
        """Returns a dictionary which, for each node v, contains all time differences
        between any time-stamped link (*,v;t) and the next link (v,*;t') (t'>t) in the
        temporal network
        """
        ip_times = defaultdict(list)
        for e in self.tedges:
            # Get target v of current edge e=(u,v,t)
            v = e[1]
            t = e[2]

            # Get time stamp of link (v,*,t_next)
            # with smallest t_next such that t_next > t
            i = bisect.bisect_right(self.activities[v], t)
            if i != len(self.activities[v]):
                ip_times[v].append(self.activities[v][i]-t)
        return ip_times

    def summary(self):
        """
        Returns a string containing basic summary statistics of this temporal network
        """

        summary = ''

        summary += 'Nodes:\t\t\t' + str(self.vcount()) + '\n'
        summary += 'Time-stamped links:\t' + str(self.ecount()) + '\n'
        if self.vcount() > 0:
            summary += 'Links/Nodes:\t\t' + str(self.ecount()/self.vcount()) + '\n'
        else:
            summary += 'Links/Nodes:\t\tN/A\n'
        if len(self.ordered_times) > 1:
            min_o = min(self.ordered_times)
            max_o = max(self.ordered_times)
            obs_len = max_o - min_o
            n_stamps = len(self.ordered_times)
            summary += 'Observation period:\t[{}, {}]\n'.format(min_o, max_o)
            summary += 'Observation length:\t {} \n'.format(obs_len)
            summary += 'Time stamps:\t\t {} \n'.format(n_stamps)

            d = self.inter_event_times()
            mean_d = _np.mean(d)

            summary += 'Avg. inter-event dt:\t {}\n'.format(mean_d)
            summary += 'Min/Max inter-event dt:\t {}/{}'.format(min(d), max(d))

        return summary

    def __str__(self):
        """Returns the default string representation of this temporal network instance.
        """
        return self.summary()

    def reverse_time(self):
        """
        Returns a copy of the temporal network in which time has been reversed
        """
        t = TemporalNetwork()
        t_reversed = self.ordered_times.copy()
        t_reversed.reverse()
        time_r = 1
        for i in range(len(t_reversed)):
            if i > 0:
                time_r += abs(t_reversed[i] - t_reversed[i-1])
            for (v, w, x) in self.time[t_reversed[i]]:
                t.add_edge(v, w, time_r)
        return t

    def _repr_html_(self):
        """
        display an interactive d3js visualisation of the temporal network in jupyter
        """
        from ehtml import generate_html
        return generate_html(self)
