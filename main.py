import sys
sys.path.append("/Library/Frameworks/Python.framework/Versions/3.7/lib/python3.7/site-packages")
import pickle
import numpy as np
import networkx as nx
from time import time
from scipy.sparse import coo_matrix, identity


MAX_GRAPH_DISTANCE_RATIO = 1 / 3
TOPK_LIST = [1, 2, 5, 10, 20, 50, 100]


def build_graph(path):
    print('building KG...')
    kg = nx.DiGraph()
    for line in open(path, 'r'):
        h, r, t = line.strip().split('\t')
        kg.add_edge(int(h), int(t), edge_type=int(r))
    return kg


def get_dicts(kg):
    print('calculating dicts...')

    node2neighbor_num = dict()
    node2degree = dict()
    node2neighbor_edge_num = dict()

    for node in kg.nodes:
        neighbors = set(kg.predecessors(node)) | set(kg.successors(node))
        n_neighbors = len(neighbors)
        node2neighbor_num[node] = n_neighbors

        degree = kg.degree(node)
        node2degree[node] = degree

        subgraph = kg.subgraph(neighbors)
        n_neighbor_edges = len(subgraph.edges)
        node2neighbor_edge_num[node] = n_neighbor_edges

    return node2neighbor_num, node2degree, node2neighbor_edge_num


def construct_local_subgraph(query_node, kg):
    subgraph = kg.subgraph(set(kg.predecessors(query_node)) | set(kg.successors(query_node)) | {query_node})

    # the center node (query node) is always mapped to 0 in the relabeled query graph
    node_mapping = {query_node: 0}
    for n in subgraph.nodes:
        if n != query_node:
            node_mapping[n] = len(node_mapping)

    subgraph_relabeled = nx.DiGraph()
    for e in subgraph.edges:
        subgraph_relabeled.add_edge(node_mapping[e[0]],
                                    node_mapping[e[1]],
                                    edge_type=subgraph.get_edge_data(e[0], e[1])['edge_type'])

    return subgraph_relabeled


def calculate_assignment_matrix(query_graph, kg):
    A = get_affinity_matrix(query_graph, kg)
    x = np.ones([A.shape[0], 1], dtype=np.float) / A.shape[0]
    while True:
        next_x = A.dot(x)
        next_x /= np.linalg.norm(next_x)
        if np.linalg.norm(next_x - x) < 0.01:
            break
        x = next_x

    x = x.reshape([len(query_graph.nodes), len(kg.nodes)])
    return x


# A_{ia; jb} = s_E(e_{ij}, e'_{ab})
def get_affinity_matrix(query_graph, kg):
    n = len(query_graph.nodes)
    m = len(kg.nodes)

    row = []
    col = []
    data = []
    for query_edge in query_graph.edges:
        for kg_edge in kg.edges:
            i = query_edge[0]
            j = query_edge[1]
            a = kg_edge[0]
            b = kg_edge[1]
            ia = i * m + a
            jb = j * m + b
            e_ij = query_graph.get_edge_data(i, j)['edge_type']
            e_ab = kg.get_edge_data(a, b)['edge_type']
            if e_ij == e_ab:
                row.append(ia)
                col.append(jb)
                data.append(1)

    A = coo_matrix((data, (row, col)), shape=(n * m, n * m))
    A += identity(n * m)

    return A


def main():
    kg = build_graph('triplets.txt')
    ground_truth = pickle.load(open('ground_truth.pkl', 'rb'))
    node2neighbor_num, node2degree, node2neighbor_edge_num = get_dicts(kg)

    precision_list = []
    recall_list = []

    for i, q in enumerate(ground_truth.keys()):
        print('%d / %d' % (i, len(ground_truth)))

        query_graph = construct_local_subgraph(q, kg)
        x = calculate_assignment_matrix(query_graph, kg)

        scores = dict()
        for n in range(len(kg.nodes)):
            if n == q:
                continue
            if node2neighbor_num[n] != node2neighbor_num[q]:
                continue
            if abs(node2degree[n] - node2degree[q]) + abs(node2neighbor_edge_num[n] - node2neighbor_edge_num[q]) \
                    > MAX_GRAPH_DISTANCE_RATIO * len(query_graph.edges):
                continue
            scores[n] = x[0][n]
        sorted_res = [i[0] for i in sorted(scores.items(), key=lambda item: -item[1])]

        precision = []
        recall = []
        for k in TOPK_LIST:
            n_hit = len(set(sorted_res[0:k]) & set(ground_truth[q]))
            precision.append(n_hit / k)
            recall.append(n_hit / len(ground_truth[q]))

        precision_list.append(precision)
        recall_list.append(recall)

    avg_precision = np.average(np.array(precision_list), axis=0)
    avg_recall = np.average(np.array(recall_list), axis=0)

    np.set_printoptions(precision=3)
    print('\nk =', TOPK_LIST)
    print('precision@k:', avg_precision)
    print('recall@k:', avg_recall)


if __name__ == '__main__':
    t = time()
    main()
    print('time: %.1f s' % (time() - t))
