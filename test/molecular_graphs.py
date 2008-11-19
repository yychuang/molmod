# MolMod is a collection of molecular modelling tools for python.
# Copyright (C) 2007 - 2008 Toon Verstraelen <Toon.Verstraelen@UGent.be>
#
# This file is part of MolMod.
#
# MolMod is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# MolMod is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
# --

from molmod.units import angstrom
from molmod.molecular_graphs import *
from molmod.graphs import GraphError, GraphSearch, CriteriaSet, CritOr, RingPattern
from molmod.data.bonds import BOND_SINGLE
from molmod.io.sdf import SDFReader
from molmod.io.xyz import XYZFile

import unittest, copy, numpy, os

__all__ = ["MolecularGraphTestCase"]


class MolecularGraphTestCase(unittest.TestCase):
    # auxiliary routines

    def load_molecule(self, xyz_fn):
        molecule = XYZFile(os.path.join("input", xyz_fn)).get_molecule()
        molecule.graph = MolecularGraph.from_geometry(molecule)
        return molecule

    def iter_molecules(self, allow_multi=False):
        xyz_fns = [
          "water.xyz", "cyclopentane.xyz", "ethene.xyz", "funny.xyz",
          "tea.xyz", "tpa.xyz", "thf_single.xyz", "precursor.xyz",
        ]
        for xyz_fn in xyz_fns:
            molecule = self.load_molecule(xyz_fn)
            if allow_multi or len(molecule.graph.independent_nodes) == 1:
                molecule.title = xyz_fn[:-4]
                yield molecule
        sdf_fns = [
            "example.sdf", "CID_22898828.sdf", "SID_55127927.sdf",
            "SID_56274343.sdf", "SID_40363570.sdf", "SID_40363571.sdf",
            "SID_31646548.sdf", "SID_31646545.sdf", "SID_41893278.sdf",
            "SID_41893280.sdf", "SID_54258192.sdf", "SID_55488598.sdf",
        ]
        for sdf_fn in sdf_fns:
            for i, molecule in enumerate(SDFReader(os.path.join("input", sdf_fn))):
                if allow_multi or len(molecule.graph.independent_nodes) == 1:
                    molecule.title = "%s_%i" % (sdf_fn[:-4], i)
                    yield molecule

    # graph search tests

    def verify_graph_search(self, graph, expected_results, test_results, iter_alternatives):
        for key in test_results.iterkeys():
            unsatisfied = expected_results[key]
            test = test_results[key]
            correct = []
            unexpected = []
            for test_item in test:
                item_correct = False
                for alternative in iter_alternatives(test_item, key):
                    if (alternative in unsatisfied):
                        correct.append(test_item)
                        unsatisfied.remove(alternative)
                        item_correct = True
                        break
                if not item_correct:
                    unexpected.append(test_item)
            message  = "Incorrect matches (%s):\n" % key
            message += "correct (%i): %s\n" % (len(correct), correct)
            message += "unexpected  (%i): %s\n" % (len(unexpected), unexpected)
            message += "unsatisfied (%i): %s\n" % (len(unsatisfied), unsatisfied)
            #print message
            self.assertEqual(len(unexpected), 0, message)
            self.assertEqual(len(unsatisfied), 0, message)

    def test_bonds_tpa(self):
        molecule = self.load_molecule("tpa.xyz")
        pattern = BondPattern([
            CriteriaSet(atom_criteria(1, 6), tag="HC"),
            CriteriaSet(atom_criteria(6, 6), tag="CC"),
            CriteriaSet(atom_criteria(6, 7), tag="CN"),
            CriteriaSet(atom_criteria(6, HasNumNeighbors(4)), tag="C-sp3"),
            CriteriaSet(atom_criteria(6, CritOr(HasAtomNumber(6), HasAtomNumber(7))), tag="C-[CN]"),
            CriteriaSet(relation_criteria={0: BondLongerThan(1.3*angstrom)}, tag="long"),
            CriteriaSet(atom_criteria(6, HasNeighbors(atom_criteria(1,1,6,7).values())), tag="C-C(-NHH)"),
        ])
        expected_results = {
            "HC": set([
                (14, 1), (13, 1), (16, 2), (15, 2), (17, 3), (19, 3), (18, 3),
                (20, 4), (21, 4), (23, 5), (22, 5), (25, 6), (26, 6), (24, 6),
                (27, 7), (28, 7), (29, 8), (30, 8), (31, 9), (33, 9), (32, 9),
                (35, 10), (34, 10), (37, 11), (36, 11), (39, 12), (40, 12), (38, 12)
            ]),
            "CC": set([(2, 1), (3, 2), (5, 4), (6, 5), (8, 7), (9, 8), (11, 10), (12, 11)]),
            "CN": set([(10, 0), (1, 0), (4, 0), (7, 0)]),
            "C-sp3": set([
                (10, 0), (1, 0), (4, 0), (7, 0), (2, 1), (3, 2), (5, 4), (6, 5),
                (8, 7), (9, 8), (11, 10), (12, 11)
            ]),
            "C-[CN]": set([
                (10, 0), (1, 0), (4, 0), (7, 0), (2, 1), (3, 2), (5, 4), (6, 5),
                (8, 7), (9, 8), (11, 10), (12, 11)
            ]),
            "long": set([
                (10, 0), (1, 0), (4, 0), (7, 0), (2, 1), (3, 2), (5, 4), (6, 5),
                (8, 7), (9, 8), (11, 10), (12, 11)
            ]),
            "C-C(-NHH)": set([
                (5, 4), (7, 8), (1, 2), (10, 11)
            ])
        }
        test_results = dict((key, []) for key in expected_results)
        match_generator = GraphSearch(pattern, debug=False)
        for match in match_generator(molecule.graph):
            test_results[match.tag].append(tuple(match.get_destination(index) for index in xrange(len(match))))

        def iter_alternatives(test_item, key):
            yield test_item
            a, b = test_item
            if molecule.numbers[a] == molecule.numbers[b] or key=="long":
                yield b, a

        self.verify_graph_search(molecule.graph, expected_results, test_results, iter_alternatives)

    def test_bending_angles_tpa(self):
        molecule = self.load_molecule("tpa.xyz")
        pattern = BendingAnglePattern([
            CriteriaSet(atom_criteria(1, 6, 1), tag="HCH"),
            CriteriaSet(atom_criteria(1, 6, 6), tag="HCC"),
            CriteriaSet(atom_criteria(6, 6, 6), tag="CCC"),
            CriteriaSet(atom_criteria(6, 6, 7), tag="CCN"),
            CriteriaSet(atom_criteria(6, 7, 6), tag="CNC"),
            CriteriaSet(atom_criteria(1, 6, 7), tag="HCN"),
        ])
        expected_results = {
            'HCC': set([
                (14, 1, 2), (13, 1, 2), (16, 2, 1), (15, 2, 1), (16, 2, 3),
                (15, 2, 3), (17, 3, 2), (19, 3, 2), (18, 3, 2), (20, 4, 5),
                (21, 4, 5), (23, 5, 6), (23, 5, 4), (22, 5, 6), (22, 5, 4),
                (25, 6, 5), (26, 6, 5), (24, 6, 5), (27, 7, 8), (28, 7, 8),
                (29, 8, 9), (30, 8, 9), (29, 8, 7), (30, 8, 7), (31, 9, 8),
                (33, 9, 8), (32, 9, 8), (35, 10, 11), (34, 10, 11), (37, 11, 12),
                (36, 11, 12), (37, 11, 10), (36, 11, 10), (39, 12, 11),
                (40, 12, 11), (38, 12, 11)
            ]),
            'CCN': set([
                (2, 1, 0), (5, 4, 0), (8, 7, 0), (11, 10, 0)
            ]),
            'CNC': set([
                (1, 0, 10), (4, 0, 10), (7, 0, 10), (4, 0, 1), (7, 0, 1),
                (7, 0, 4)
            ]),
            'HCH': set([
                (13, 1, 14), (15, 2, 16), (19, 3, 17), (18, 3, 17), (18, 3, 19),
                (21, 4, 20), (22, 5, 23), (26, 6, 25), (24, 6, 25), (24, 6, 26),
                (28, 7, 27), (30, 8, 29), (33, 9, 31), (32, 9, 31), (32, 9, 33),
                (34, 10, 35), (36, 11, 37), (40, 12, 39), (38, 12, 39), (38, 12, 40)
            ]),
            'HCN': set([
                (14, 1, 0), (13, 1, 0), (20, 4, 0), (21, 4, 0), (27, 7, 0),
                (28, 7, 0), (35, 10, 0), (34, 10, 0)
            ]),
            'CCC': set([(3, 2, 1), (4, 5, 6), (7, 8, 9), (10, 11, 12)])
        }
        test_results = dict((key, []) for key in expected_results)
        match_generator = GraphSearch(pattern, debug=False)
        for match in match_generator(molecule.graph):
            test_results[match.tag].append(tuple(match.get_destination(index) for index in xrange(len(match))))

        def iter_alternatives(test_item, key):
            yield test_item
            a, b, c = test_item
            if molecule.numbers[a] == molecule.numbers[c]:
                yield c, b, a

        self.verify_graph_search(molecule.graph, expected_results, test_results, iter_alternatives)

    def test_dihedral_angles_tpa(self):
        molecule = self.load_molecule("tpa.xyz")
        pattern = DihedralAnglePattern([
            CriteriaSet(atom_criteria(1, 6, 6, 1), tag="HCCH"),
            CriteriaSet(atom_criteria(1, 6, 6, 7), tag="HCCN"),
            CriteriaSet(atom_criteria(1, 6, 7, 6), tag="HCNC"),
        ])
        expected_results = {
            'HCCH': set([
                (16, 2, 1, 14), (15, 2, 1, 14), (16, 2, 1, 13), (15, 2, 1, 13),
                (17, 3, 2, 16), (19, 3, 2, 16), (18, 3, 2, 16), (17, 3, 2, 15),
                (19, 3, 2, 15), (18, 3, 2, 15), (23, 5, 4, 20), (22, 5, 4, 20),
                (23, 5, 4, 21), (22, 5, 4, 21), (25, 6, 5, 23), (26, 6, 5, 23),
                (24, 6, 5, 23), (25, 6, 5, 22), (26, 6, 5, 22), (24, 6, 5, 22),
                (29, 8, 7, 27), (30, 8, 7, 27), (29, 8, 7, 28), (30, 8, 7, 28),
                (31, 9, 8, 29), (33, 9, 8, 29), (32, 9, 8, 29), (31, 9, 8, 30),
                (33, 9, 8, 30), (32, 9, 8, 30), (37, 11, 10, 35), (36, 11, 10, 35),
                (37, 11, 10, 34), (36, 11, 10, 34), (39, 12, 11, 37), (40, 12, 11, 37),
                (38, 12, 11, 37), (39, 12, 11, 36), (40, 12, 11, 36), (38, 12, 11, 36)
            ]),
            'HCCN': set([
                (16, 2, 1, 0), (15, 2, 1, 0), (23, 5, 4, 0), (22, 5, 4, 0),
                (29, 8, 7, 0), (30, 8, 7, 0), (37, 11, 10, 0), (36, 11, 10, 0)
            ]),
            'HCNC': set([
                (14, 1, 0, 10), (13, 1, 0, 10), (20, 4, 0, 10), (21, 4, 0, 10),
                (27, 7, 0, 10), (28, 7, 0, 10), (35, 10, 0, 1), (34, 10, 0, 1),
                (20, 4, 0, 1), (21, 4, 0, 1), (27, 7, 0, 1), (28, 7, 0, 1),
                (35, 10, 0, 4), (34, 10, 0, 4), (14, 1, 0, 4), (13, 1, 0, 4),
                (27, 7, 0, 4), (28, 7, 0, 4), (35, 10, 0, 7), (34, 10, 0, 7),
                (14, 1, 0, 7), (13, 1, 0, 7), (20, 4, 0, 7), (21, 4, 0, 7)
            ])
        }
        test_results = dict((key, []) for key in expected_results)
        match_generator = GraphSearch(pattern, debug=False)
        for match in match_generator(molecule.graph):
            test_results[match.tag].append(tuple(match.get_destination(index) for index in xrange(len(match))))

        def iter_alternatives(test_item, key):
            yield test_item
            a, b, c, d = test_item
            if (molecule.numbers[a] == molecule.numbers[d]) and (molecule.numbers[b] == molecule.numbers[c]):
                yield d, c, b, a

        self.verify_graph_search(molecule.graph, expected_results, test_results, iter_alternatives)

    def test_tetra_tpa(self):
        molecule = self.load_molecule("tpa.xyz")
        pattern = TetraPattern([
            CriteriaSet(atom_criteria(6, 1, 6, 6, 1), tag="C-(HCCH)")
        ], node_tags={0: 1, 1: 1}) # node tags are just a silly example
        expected_results = {
            'C-(HCCH)': set([
                ( 8, 29,  9,  7, 30), ( 8, 30,  9,  7, 29), ( 2,  1, 15, 16,  3), ( 2,  3, 15, 16,  1),
                (11, 10, 36, 37, 12), (11, 12, 36, 37, 10), ( 5,  4, 22, 23,  6), ( 5,  6, 22, 23,  4),
            ]),
        }
        test_results = dict((key, []) for key in expected_results)
        match_generator = GraphSearch(pattern, debug=False)
        for match in match_generator(molecule.graph):
            test_results[match.tag].append(tuple(match.get_destination(index) for index in xrange(len(match))))


        def iter_alternatives(test_item, key):
            a, b, c, d, e = test_item
            yield test_item
            yield a, c, b, e, d
            if (molecule.numbers[b] == molecule.numbers[e]):
                yield a, e, c, d, b
                yield a, c, e, b, d
            if (molecule.numbers[c] == molecule.numbers[d]):
                yield a, b, d, c, e
                yield a, d, b, e, c
            if (molecule.numbers[b] == molecule.numbers[e]) and (molecule.numbers[c] == molecule.numbers[d]):
                yield a, e, d, c, b
                yield a, d, e, b, c

        self.verify_graph_search(molecule.graph, expected_results, test_results, iter_alternatives)

    def test_dihedral_angles_precursor(self):
        molecule = self.load_molecule("precursor.xyz")
        pattern = DihedralAnglePattern([CriteriaSet(tag="all")])
        # construct all dihedral angles:
        all_dihedrals = set([])
        for b, c in molecule.graph.pairs:
            for a in molecule.graph.neighbors[b]:
                if a != c:
                    for d in molecule.graph.neighbors[c]:
                        if d != b:
                            all_dihedrals.add((a, b, c, d))
        expected_results = {
            'all': all_dihedrals,
        }
        test_results = dict((key, []) for key in expected_results)
        match_generator = GraphSearch(pattern, debug=False)
        for match in match_generator(molecule.graph):
            test_results[match.tag].append(tuple(match.get_destination(index) for index in xrange(len(match))))

        def iter_alternatives(test_item, key):
            yield test_item
            a, b, c, d = test_item
            yield d, c, b, a

        self.verify_graph_search(molecule.graph, expected_results, test_results, iter_alternatives)

    def test_rings_5ringOH(self):
        molecule = self.load_molecule("5ringOH.xyz")
        pattern = NRingPattern(10, [CriteriaSet(tag="all")])
        expected_results = {
            'all': set([(14, 25, 11, 26, 21, 29, 18, 28, 17, 27)])
        }

        test_results = dict((key, []) for key in expected_results)
        match_generator = GraphSearch(pattern, debug=False)
        for match in match_generator(molecule.graph):
            test_results[match.tag].append(tuple(match.get_destination(index) for index in xrange(len(match))))

        def iter_alternatives(test_item, key):
            for i in xrange(10):
                test_item = (test_item[-1],) + test_item[:-1]
                yield test_item
                yield tuple(reversed(test_item))

        self.verify_graph_search(molecule.graph, expected_results, test_results, iter_alternatives)

    def test_rings_precursor(self):
        molecule = self.load_molecule("precursor.xyz")
        pattern = RingPattern(21)
        all_rings = {}
        match_generator = GraphSearch(pattern, debug=False)
        for match in match_generator(molecule.graph):
            l = all_rings.setdefault(len(match.ring_nodes), set([]))
            l.add(match.ring_nodes)

        for size, solutions in all_rings.iteritems():
            tag = '%i-ring' % size
            pattern = NRingPattern(size, [CriteriaSet(tag=tag)], strong=True)
            expected_results = {tag: solutions}

            test_results = {tag: []}
            match_generator = GraphSearch(pattern, debug=False)
            for match in match_generator(molecule.graph):
                test_results[match.tag].append(tuple(match.get_destination(index) for index in xrange(len(match))))

            def iter_alternatives(test_item, key):
                for i in xrange(size):
                    test_item = (test_item[-1],) + test_item[:-1]
                    yield test_item
                    yield tuple(reversed(test_item))

            self.verify_graph_search(molecule.graph, expected_results, test_results, iter_alternatives)

    # test other molecular graph stuff

    def test_multiply(self):
        # sulfate:
        pairs = [(0,1), (0,2), (0,3), (0,4)]
        numbers = numpy.array([16, 8, 8, 8, 8])
        orders = numpy.array([1, 1, 2, 2])
        mgraph = MolecularGraph(pairs, numbers, orders)

        check_pairs = [
            (0,1), (0,2), (0,3), (0,4),
            (5, 6), (5, 7), (5, 8), (5, 9),
            (10, 11), (10, 12), (10, 13), (10, 14)
        ]
        check_pairs = tuple(frozenset(pair) for pair in check_pairs)
        check_orders = numpy.concatenate([orders, orders, orders])
        check_numbers = numpy.concatenate([numbers, numbers, numbers])
        for check in [mgraph*3, 3*mgraph]:
            self.assertEqual(len(check.pairs), len(check_pairs))
            self.assertEqual(check.pairs, check_pairs)
            self.assertEqual(check.numbers.shape,check_numbers.shape)
            self.assert_((check.numbers==check_numbers).all())
            self.assertEqual(check.orders.shape,check_orders.shape)
            self.assert_((check.orders==check_orders).all())

    def test_fingerprints(self):
        for mol in self.iter_molecules():
            g0 = mol.graph
            permutation = numpy.random.permutation(g0.num_nodes)
            g1 = g0.get_subgraph(permutation, normalize=True)
            for i in xrange(g0.num_nodes):
                self.assert_((g0.node_fingerprints[permutation[i]]==g1.node_fingerprints[i]).all())
            self.assert_((g0.fingerprint==g1.fingerprint).all())

    def test_fingerprint_collisions(self):
        # These are collisions with older versions, found by scanning the
        # pubchem database.
        cases = [
            ('SID_55127927.sdf', 'SID_56274343.sdf'),
            ('SID_55488598.sdf', 'SID_54258192.sdf'),
            ('SID_41893280.sdf', 'SID_41893278.sdf'),
            ('SID_40363570.sdf', 'SID_40363571.sdf'),
            ('SID_31646548.sdf', 'SID_31646545.sdf')
        ]
        for fn0, fn1 in cases:
            g0 = SDFReader(os.path.join("input", fn0)).next().graph
            g1 = SDFReader(os.path.join("input", fn1)).next().graph
            self.assertNotEqual(str(g0.fingerprint.data), str(g1.fingerprint.data))

    def test_subgraph(self):
        for mol in self.iter_molecules():
            g0 = mol.graph
            permutation = numpy.random.permutation(g0.num_nodes)
            # normalize=False
            g1 = g0.get_subgraph(permutation)
            self.assert_((g0.numbers==g1.numbers).all())
            self.assertEqual(g0.num_pairs, g1.num_pairs)
            self.assertEqual(g0.pairs, g1.pairs)
            self.assert_((g0.orders==g1.orders).all())
            # normalize=True
            g1 = g0.get_subgraph(permutation, normalize=True)
            self.assert_((g0.numbers[permutation]==g1.numbers).all())
            self.assertEqual(g0.num_pairs, g1.num_pairs)

    def test_subgraph_big(self):
        mol = self.load_molecule("thf.xyz")
        g0 = mol.graph
        for group in g0.independent_nodes:
            g1 = g0.get_subgraph(group, normalize=True)
            self.assertEqual(g1.num_nodes, len(group))
            self.assert_((g0.numbers[group]==g1.numbers).all())

    def test_iter_shortest_paths(self):
        molecule = self.load_molecule("precursor.xyz")
        cases = {
            (56,65): set([(56,7,66,11,65)]),
            (49,67): set([(49,2,53,6,56,7,60,9,59,8,67),(49,4,54,10,61,11,65,13,64,12,67)]),
            (49,49): set([(49,)]), # just check wether the function doesn't crash on weird input
        }
        for (i,j), expected_results in cases.iteritems():
            shortest_paths = set(molecule.graph.iter_shortest_paths(i,j))
            self.assertEqual(shortest_paths, expected_results)

    def test_iter_shortest_paths_generic(self):
        for molecule in self.iter_molecules(allow_multi=True):
            i = numpy.random.randint(molecule.size)
            j = numpy.random.randint(molecule.size)
            length = None
            for path in molecule.graph.iter_shortest_paths(i,j):
                if length is None:
                    length = len(path)
                else:
                    self.assertEqual(length, len(path))
                for i in xrange(len(path)-1):
                    self.assert_(path[i] in molecule.graph.neighbors[path[i+1]])

    def test_full_match_on_self(self):
        for molecule in self.iter_molecules(allow_multi=True):
            g1 = copy.deepcopy(molecule.graph)
            g2 = copy.deepcopy(molecule.graph)
            match = g1.full_match(g2)
            self.assertNotEqual(match, None)
            self.assertEqual(len(match), g1.num_nodes)

    def test_canonical_order(self):
        # TODO: analogous tests voor pure graphs + fixen
        for molecule in self.iter_molecules():
            try:
                g0 = molecule.graph
                order0 = g0.canonical_order
                g0_bis = g0.get_subgraph(order0, normalize=True)

                permutation = numpy.random.permutation(g0.num_nodes)
                g1 = g0.get_subgraph(permutation, normalize=True)
                order1 = g1.canonical_order
                g1_bis = g1.get_subgraph(order1, normalize=True)

                self.assertEqual(str(g0_bis), str(g1_bis))
                self.assert_((g0_bis.numbers==g1_bis.numbers).all())
                self.assert_((g0_bis.orders==g1_bis.orders).all())
            except NotImplementedError:
                pass

    def test_guess_geometry(self):
        for input_mol in self.iter_molecules(allow_multi=False):
            output_mol = input_mol.graph.guess_geometry()
            output_mol.title = input_mol.title
            output_mol.write_to_file("output/guess_%s.xyz" % input_mol.title)

    def test_blob(self):
        for molecule in self.iter_molecules(allow_multi=True):
            blob = molecule.graph.blob
            graph = MolecularGraph.from_blob(blob)
            self.assert_((graph.numbers==molecule.graph.numbers).all(), "Atom numbers do not match.")
            self.assert_(graph.pairs==molecule.graph.pairs, "Pairs do not match.")

    def test_halfs_double_thf(self):
        molecule = self.load_molecule("thf_single.xyz")
        cases = [
            (0,2,0,1), (1,0,1,4), (4,1,4,3), (3,2,3,4), (2,3,2,0),
            (2,3,1,4), (0,2,4,3), (3,2,1,0), (2,0,4,1), (3,4,0,1),
        ]
        for a1,b1,a2,b2 in cases:
            try:
                half1, half2, hinges = molecule.graph.get_halfs_double(a1,b1,a2,b2)
            except GraphError:
                self.fail_("The case (%i,%i,%i,%i) must lead to a solution." % (a1,b1,a2,b2))
            if a1 == 0 and a2 == 0:
                self.assertEqual(len(half1), 1)
                self.assert_(len(half2) > 1)
            else:
                self.assert_(len(half1) > 1)
                self.assert_(len(half2) > 1)

    def test_add_hydrogens(self):
        cases = [(
            MolecularGraph([], numpy.array([6]), numpy.array([])),
            None,
            MolecularGraph([(0,1),(0,2),(0,3),(0,4)], numpy.array([6,1,1,1,1]), numpy.array([1,1,1,1])),
        ),(
            MolecularGraph([], numpy.array([6]), numpy.array([])),
            numpy.array([-1], int),
            MolecularGraph([(0,1),(0,2),(0,3)], numpy.array([6,1,1,1]), numpy.array([1,1,1])),
        ),(
            MolecularGraph([(0,1),(1,2),(2,3),(3,4),(4,5),(5,0)], numpy.array([6,6,6,6,6,6]), numpy.array([1,2,1,2,1,2])),
            None,
            MolecularGraph([(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(0,6),(1,7),(2,8),(3,9),(4,10),(5,11)], numpy.array([6,6,6,6,6,6,1,1,1,1,1,1]), numpy.array([1,2,1,2,1,2,1,1,1,1,1,1])),
        ),(
            MolecularGraph([(0,1),(1,2),(2,3),(3,4),(4,0)], numpy.array([8,6,6,6,6]), numpy.array([1,1,1,1,1])),
            None,
            MolecularGraph([(0,1),(1,2),(2,3),(3,4),(4,0),(1,5),(1,6),(2,7),(2,8),(3,9),(3,10),(4,11),(4,12)], numpy.array([8,6,6,6,6,1,1,1,1,1,1,1,1]), numpy.array([1,1,1,1,1,1,1,1,1,1,1,1,1])),
        )]

        for before, formal_charges, after in cases:
            after_check = before.add_hydrogens(formal_charges)
            self.assertEqual(after.pairs, after_check.pairs)
            self.assert_((after.numbers==after_check.numbers).all())
            self.assert_((after.orders==after_check.orders).all())

