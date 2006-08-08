# MolMod is a collection of molecular modelling tools for python.
# Copyright (C) 2005 Toon Verstraelen
#
# This file is part of MolMod.
#
# MolMod is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# --


from molmod.binning import InterAnalyseNeighboringObjects, \
    IntraAnalyseNeighboringObjects, PositionedObject, SparseBinnedObjects
from molmod.unit_cell import UnitCell
from molmod.units import from_angstrom, from_degree
from molmod.data import periodic

import math, numpy
import unittest

__all__ = ["Distances"]


class Distances(unittest.TestCase):
    gridsize = periodic.max_radius*2

    def load_binned_atoms(self, filename):
        from molmod.molecules import molecule_xyz_from_filename
        m = molecule_xyz_from_filename("input/"+filename)

        def yield_positioned_atoms():
            for index in xrange(len(m.numbers)):
                yield PositionedObject((m, index), m.coordinates[index])

        return m, SparseBinnedObjects(yield_positioned_atoms(), self.gridsize)

    def verify(self, yield_pairs, distances, unit_cell=None):
        missing_pairs = []
        wrong_distances = []
        for (id1, coord1), (id2, coord2) in yield_pairs():
            delta = coord2 - coord1
            if unit_cell is not None:
                delta = unit_cell.shortest_vector(delta)
            distance = math.sqrt(numpy.dot(delta, delta))
            if distance < self.gridsize:
                identifier = frozenset([id1, id2])
                fast_distance = distances.get(identifier)
                if fast_distance == None:
                    missing_pairs.append(tuple(identifier) + (distance,))
                elif fast_distance != distance:
                    wrong_distances.append(tuple(identifier) + (fast_distance, distance))
                else:
                    del distances[identifier]

        message  = "-"*50+"\n"
        message += "MISSING PAIRS: %i\n" % len(missing_pairs)
        for missing_pair in missing_pairs:
            message += "%10s %10s: \t % 10.7f\n" % missing_pair
        message += "WRONG DISTANCES: %i\n" % len(wrong_distances)
        for wrong_distance in wrong_distances:
            message += "%10s %10s: \t % 10.7f != % 10.7f\n" % wrong_distance
        message += "DUPLICATE PAIRS: %i\n" % len(distances)
        for identifier, fast_distance in distances.iteritems():
            message += "%10s %10s: \t % 10.7f\n" % (tuple(identifier) + (fast_distance,))
        message += "-"*50+"\n"

        self.assertEqual(len(missing_pairs), 0, message)
        self.assertEqual(len(wrong_distances), 0, message)
        self.assertEqual(len(distances), 0, message)

    def verify_intra(self, molecule, distances, unit_cell=None):
        def yield_atom_pairs():
            for index1, coord1 in enumerate(molecule.coordinates):
                for index2, coord2 in enumerate(molecule.coordinates[:index1]):
                    yield ((molecule, index1), coord1), ((molecule, index2), coord2)
        self.verify(yield_atom_pairs, distances, unit_cell)

    def verify_inter(self, molecule1, molecule2, distances, unit_cell=None):
        def yield_atom_pairs():
            for index1, coord1 in enumerate(molecule1.coordinates):
                for index2, coord2 in enumerate(molecule2.coordinates):
                    yield ((molecule1, index1), coord1), ((molecule2, index2), coord2)
        self.verify(yield_atom_pairs, distances, unit_cell)

    def compare_function(self, positioned1, positioned2):
        delta = positioned2.vector - positioned1.vector
        distance = math.sqrt(numpy.dot(delta, delta))
        if distance < self.gridsize:
            return distance

    def test_distances_intra(self):
        molecule, binned_atoms = self.load_binned_atoms("precursor.xyz")

        distances = dict(
            (frozenset([positioned1.id, positioned2.id]), result)
            for (positioned1, positioned2), result
            in IntraAnalyseNeighboringObjects(binned_atoms, self.compare_function)()
        )
        self.verify_intra(molecule, distances)

    def test_distances_intra_periodic(self):
        molecule, binned_atoms = self.load_binned_atoms("lau.xyz")
        unit_cell = UnitCell()
        unit_cell.set_parameters(
            from_angstrom(numpy.array([14.59, 12.88, 7.61])),
            from_degree(numpy.array([90.0, 111.0, 90.0]))
        )

        distances = dict(
            (frozenset([positioned1.id, positioned2.id]), result)
            for (positioned1, positioned2), result
            in IntraAnalyseNeighboringObjects(binned_atoms, self.compare_function)(unit_cell)
        )
        self.verify_intra(molecule, distances, unit_cell)

    def test_distances_inter(self):
        molecule1, binned_atoms1 = self.load_binned_atoms("precursor.xyz")
        molecule2, binned_atoms2 = self.load_binned_atoms("precursor.xyz")

        distances = dict(
            (frozenset([positioned1.id, positioned2.id]), result)
            for (positioned1, positioned2), result
            in InterAnalyseNeighboringObjects(binned_atoms1, binned_atoms2, self.compare_function)()
        )
        self.verify_inter(molecule1, molecule2, distances)

    def test_distances_inter_periodic(self):
        molecule1, binned_atoms1 = self.load_binned_atoms("lau.xyz")
        molecule2, binned_atoms2 = self.load_binned_atoms("lau.xyz")
        unit_cell = UnitCell()
        unit_cell.set_parameters(
            from_angstrom(numpy.array([14.59, 12.88, 7.61])),
            from_degree(numpy.array([90.0, 111.0, 90.0]))
        )

        distances = dict(
            (frozenset([positioned1.id, positioned2.id]), result)
            for (positioned1, positioned2), result
            in InterAnalyseNeighboringObjects(binned_atoms1, binned_atoms2, self.compare_function)(unit_cell)
        )
        self.verify_inter(molecule1, molecule2, distances, unit_cell)

