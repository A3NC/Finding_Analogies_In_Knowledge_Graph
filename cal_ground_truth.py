import pickle
import networkx as nx
import multiprocessing as mp
from collections import defaultdict
from time import time


QUERY_SIZE_MIN = 4
QUERY_SIZE_MAX = 9
MIN_NEIGHBOR_EDGES = 2
MAX_GRAPH_DISTANCE_RATIO = 1 / 3
TIMEOUT_FOR_CALCULATING_GED = 10


kg = nx.DiGraph()
node2neighbor_num = dict()
node2degree = dict()
node2neighbor_edge_num = dict()


def edge_match(e1, e2):
    if e1 == {} and e2 == {}:
        return True
    elif e1 == {} or e2 == {}:
        return False
    return e1['edge_type'] == e2['edge_type']


def build_graph(path):
    print('building KG...')
    for line in open(path, 'r'):
        h, r, t = line.strip().split('\t')
        kg.add_edge(int(h), int(t), edge_type=int(r))


# calculate useful dicts
def get_dicts():
    print('calculating dicts...')
    for node in kg.nodes:
        neighbors = set(kg.predecessors(node)) | set(kg.successors(node))
        n_neighbors = len(neighbors)
        node2neighbor_num[node] = n_neighbors

        degree = kg.degree(node)
        node2degree[node] = degree

        subgraph = kg.subgraph(neighbors)
        n_neighbor_edges = len(subgraph.edges)
        node2neighbor_edge_num[node] = n_neighbor_edges


def get_query_nodes():
    print('calculating query nodes...')
    nodes = []
    for node in kg.nodes:
        if QUERY_SIZE_MIN - 1 <= node2neighbor_num[node] <= QUERY_SIZE_MAX - 1 and \
                node2neighbor_edge_num[node] >= MIN_NEIGHBOR_EDGES:
            nodes.append(node)

    return nodes


def get_params_for_mp(n_nodes):
    n_cores = mp.cpu_count()
    pool = mp.Pool(n_cores)
    avg = n_nodes // n_cores

    range_list = []
    start = 0
    for i in range(n_cores):
        num = avg + 1 if i < n_nodes - avg * n_cores else avg
        range_list.append([start, start + num])
        start += num

    return n_cores, pool, range_list


def get_similar_graphs_with_mp(query_nodes):
    print('calculating similar graphs...')
    n_cores, pool, range_list = get_params_for_mp(len(query_nodes))

    results = pool.map(get_similar_graphs, zip([query_nodes[i[0]: i[1]] for i in range_list], range(n_cores)))

    res = defaultdict(list)
    for ground_truth in results:
        res.update(ground_truth)

    return res


def get_similar_graphs(inputs):
    query_nodes, pid = inputs
    ground_truth = defaultdict(list)

    for i, q in enumerate(query_nodes):
        print('pid %d: %d / %d' % (pid, i, len(query_nodes)))
        query_subgraph = kg.subgraph(set(kg.predecessors(q)) | set(kg.successors(q)) | {q})

        for n in kg.nodes:
            if n == q:
                continue
            if node2neighbor_num[n] != node2neighbor_num[q]:
                continue
            if abs(node2degree[n] - node2degree[q]) + abs(node2neighbor_edge_num[n] - node2neighbor_edge_num[q]) \
                    > MAX_GRAPH_DISTANCE_RATIO * len(query_subgraph.edges):
                continue

            candidate_subgraph = kg.subgraph(set(kg.predecessors(n)) | set(kg.successors(n)) | {n})
            ged = nx.graph_edit_distance(query_subgraph,
                                         candidate_subgraph,
                                         edge_match=edge_match,
                                         roots=(q, n),
                                         timeout=TIMEOUT_FOR_CALCULATING_GED)
            if ged <= MAX_GRAPH_DISTANCE_RATIO * len(query_subgraph.edges):
                ground_truth[q].append(n)

    return ground_truth


def main():
    build_graph('triplets.txt')
    get_dicts()
    query_nodes = get_query_nodes()
    res = get_similar_graphs_with_mp(query_nodes)
    pickle.dump(res, open('ground_truth.pkl', 'wb'))


if __name__ == '__main__':
    now = time()
    main()
    print('time: %.1f s' % (time() - now))
    # 12578.7s, 288 cores, Xeon E7-8890x
