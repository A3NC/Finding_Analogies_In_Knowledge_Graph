import re
from collections import defaultdict


def get_english_triplets():
    fout = open('english.txt', 'w')
    for i, line in enumerate(open('conceptnet-assertions-5.7.0.csv')):
        fields = line.strip().split('\t')
        relation = fields[1]
        head = fields[2]
        tail = fields[3]

        if head.startswith('/c/en/') and tail.startswith('/c/en/') and not relation.startswith('/r/dbpedia'):
            fout.write('%s\t%s\t%s\n' % (head.split('/')[3], relation.replace('/r/', ''), tail.split('/')[3]))

        if i % 1000000 == 0:
            print('%d m' % (i / 1000000))


def count_relations():
    relation_cnt = defaultdict(int)
    for line in open('english.txt'):
        head, relation, tail = line.strip().split('\t')
        relation_cnt[relation] += 1

    for k, v in sorted(relation_cnt.items(), key=lambda x: -x[1]):
        print(k, v)

    '''
    RelatedTo 1703582
    FormOf 378859
    DerivedFrom 325374
    HasContext 232935
    IsA 230137
    Synonym 222156
    UsedFor 39790
    EtymologicallyRelatedTo 32075
    SimilarTo 30280
    AtLocation 27797
    HasSubevent 25238
    HasPrerequisite 22710
    CapableOf 22677
    Antonym 19066
    Causes 16801
    PartOf 13077
    MannerOf 12715
    MotivatedByGoal 9489
    HasProperty 8433
    ReceivesAction 6037
    HasA 5545
    CausesDesire 4688
    HasFirstSubevent 3347
    DistinctFrom 3315
    Desires 3170
    NotDesires 2886
    HasLastSubevent 2874
    DefinedAs 2173
    InstanceOf 1480
    MadeOf 545
    Entails 405
    NotCapableOf 329
    NotHasProperty 327
    CreatedBy 263
    EtymologicallyDerivedFrom 71
    LocatedNear 49
    SymbolOf 4
    '''


def filter():
    entities = set()
    relations = ['IsA', 'PartOf', 'HasA', 'UsedFor', 'CapableOf', 'AtLocation', 'Causes', 'HasSubevent',
                 'HasFirstSubevent', 'HasLastSubevent', 'HasPrerequisite', 'HasProperty', 'MotivatedByGoal', 'Desires',
                 'CreatedBy', 'DistinctFrom', 'LocatedNear', 'SimilarTo', 'CausesDesire', 'MadeOf', 'ReceivesAction']
    res = set()
    for line in open('english.txt'):
        head, relation, tail = line.strip().split('\t')
        if re.match('^[a-z]{3,}$', head) and re.match('^[a-z]{3,}$', tail) and head != tail and relation in relations:
            res.add(head + '\t' + relation + '\t' + tail)

    fout = open('kg.txt', 'w')
    for triplet in res:
        head, relation, tail = triplet.split('\t')
        entities.add(head)
        entities.add(tail)
        fout.write(triplet + '\n')

    print(len(entities))
    print(len(res))


def to_index():
    entity_out = open('entities.txt', 'w')
    relation_out = open('relations.txt', 'w')
    triplets_out = open('triplets.txt', 'w')
    entity2index = dict()
    relation2index = dict()
    ht2r = {}

    for line in open('kg.txt'):
        h, r, t = line.strip().split()

        # remove duplicate for (h, t)
        if (h, t) not in ht2r:
            ht2r[(h, t)] = r

            if h not in entity2index:
                entity2index[h] = len(entity2index)
                entity_out.write(h + '\n')
            if r not in relation2index:
                relation2index[r] = len(relation2index)
                relation_out.write(r + '\n')
            if t not in entity2index:
                entity2index[t] = len(entity2index)
                entity_out.write(t + '\n')
            triplets_out.write('%d\t%d\t%d\n' % (entity2index[h], relation2index[r], entity2index[t]))


if __name__ == '__main__':
    #get_english_triplets()
    #count_relations()
    #filter()
    to_index()
