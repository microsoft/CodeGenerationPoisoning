# brilleu -- an interface between brille and Euphonic
# Copyright 2020 Greg Tucker
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
The `BrillEu` class
-------------------
Define a class BrillEu to act as the interface between brille and Euphonic.
Thus enabling efficient interpolation of CASTEP-derived phonons at arbitrary
Q points.

.. currentmodule:: brilleu

.. autoclass:: BrillEu
   :members:

"""
import numpy as np

import yaml
from pathlib import Path

from euphonic import ForceConstants
from euphonic import QpointPhononModes as EuQpointPhononModes
from euphonic import Crystal as EuCrystal
from euphonic import StructureFactor as EuStructureFactor
from euphonic import ureg

import brille

from .castep import read_castep_bin_symmetry
from .crystal import BrCrystal
from .utilities import broaden_modes, half_cpu_count, degenerate_check, getObjType
from .timeit import timeit

class BrillEu:
    """
    Efficient interpolation of phonon intensity at arbitrary Q points.

    The :std:doc:`euphonic:index` data classes can be used to, e.g., interpolate
    dynamical force matrices at arbitary Q points. It can then use that
    information to determine eigen values (squared excitation energy) and
    eigen vectors (atom displacements) for the 3×[number of atoms] phonon
    branches. Finally Q and the eigen vectors can be used to determine the
    structure factors of the phonon branches, which are proportional to the
    doubly-differential cross section measured by neutron scattering.

    :std:doc:`brille:index` provides classes to hold arbitrarily-shaped data at
    the points of a grid filling the first irreducible Brillouin zone of the
    primitive lattice reciprocal unit cell. The classes can then use linear
    interpolation to estimate their held-data at points between grid-points,
    the translational and rotational symmetry of the lattice to find an
    equivalent first-irreducible-Brillouin-zone point, q, for any arbitrary
    reciprocal space point, Q.

    The BrillEu object must be constructed with the symmetry information of its
    lattice. The symmetry operators can be read from a CASTEP file or a Hall
    symbol can be read from a Phonopy summary file. In either case the symmetry
    information is used to construc a first irreducible Brillouin zone which is
    used to define the boundary of a :std:doc:`brille:index` grid object.
    The gridded-points are then used by the Euphonic object to calculate
    ωᵢ(q) and ϵᵢⱼ(q), which are placed in the brille object at their respective
    grid points. When an external request is made to the BrillEu object to
    calculate Sᵢ(Q) it first uses the filled brille object to interpolate ωᵢ(Q)
    and ϵᵢⱼ(Q) and then converts Q and ϵᵢⱼ(Q) into Sᵢ(Q).
    The more-likely use for BrillEu, however, will be in calculating S(Q,ω) in
    which case ωᵢ(Q) and Sᵢ(Q) are calculated as above and then a simple
    distribution (selected by the caller) is used to broaden each of the i
    phonon branches before combining their intensities.
    """

    # pylint: disable=r0913,r0914
    def __init__(self, FCData, Grid, crystal, scattering_lengths=None, parallel=False, log=None, emit=None, **kwds):
        """
        Initialize a new BrillEu object from an existing
        :py:class:`euphonic.force_constants.ForceConstants` and one of
        :py:class:`brille.BZMeshQdd`, :py:class:`brille.BZMeshQdc`,
        :py:class:`brille.BZMeshQcc`, :py:class:`brille.BZNestQdd`,
        :py:class:`brille.BZNestQdc`, :py:class:`brille.BZNestQcc`,
        :py:class:`brille.BZTrellisQdd`, :py:class:`brille.BZTrellisQdc`,
        or :py:class:`brille.BZTrellisQcc` grid objects
        The force constants and grid should be defined in the *same* lattice,
        but ensuring that this is true is left to the user.
        """
        if emit:
            self.emit = emit
        if isinstance(log, dict):
            self.log = log
        msg = "Unexpected data type {}, expect failures."
        if not isinstance(FCData, ForceConstants):
            print(msg.format(type(FCData)))
        self.data = FCData
        # known brille <double,complex<double>> grid-like objects
        bzgrids = (brille.BZMeshQdc, brille.BZNestQdc, brille.BZTrellisQdc)
        if not isinstance(Grid, bzgrids):
            print(msg.format(type(Grid)))
        self.grid = Grid
        if not isinstance(crystal, BrCrystal):
            print(msg.format(type(crystal)))
        self.crystal = crystal
        # fake the scattering length dictionary if its not valid input
        if not isinstance(scattering_lengths, dict):
            scattering_lengths = {k: 1 for k in np.unique(self.data.crystal.atom_type)}
        for k in scattering_lengths.keys():
            if not isinstance(scattering_lengths[k], ureg.Quantity):
                scattering_lengths[k] *= ureg('fm')
        self.scattering_lengths = scattering_lengths

        self.parallel = parallel

        self._calculate_and_fill_grid(**kwds)

    def _calculate_and_fill_grid(self, cost_function=0, sort=False, **kwds):
        qpt = self.grid.rlu
        # use the ForceConstants to calculate phonon modes at the gridded Q
        qωε = self.QpointPhononModes(qpt, **kwds, interpolate=False)
        # ensure that the frequencies are in meV and keep just their magnitudes
        frq = qωε.ω #(n_pt, n_br)
        # the eigenvectors must be moved from their orthogonal representation
        vec = self.crystal.orthogonal_to_basis_eigenvectors(qωε.ε)
        # attempt to disambiguate any degenerate modes (is this necessary any more?)
        vec = degenerate_check(qpt, frq, vec)
        # verify that the data shape is right
        n_pt = qpt.shape[0]
        n_at = self.data.crystal.n_atoms
        n_br = 3*n_at
        if frq.shape == (n_pt, n_br):
            frq = frq.reshape(n_pt, n_br, 1)
        if frq.shape != (n_pt, n_br, 1):
            raise Exception('Frequencies have the wrong shape')
        if vec.shape != (n_pt, n_br, n_at, 3):
            raise Exception('Eigenvectors have the wrong shape')
        # We must provide extra content information to enable efficient
        # interpolation and possible rotations. All arrays provided to fill
        # must be 3+ dimensional -- the first dimension is over the points of
        # the grid, the second dimension is over the phonon branches, and any
        # additional dimensions are collapsed from highest to lowest dimension
        # (indexed as row-ordered linear indexing)
        # So, the vectors in (n_pt, n_br, n_io, 3) end up as
        # (n_pt, n_br, 3*n_io) with each three-vector's elements contiguous in
        # memory. The extra information provided details *what* the last
        # collapsed dimension contains, as a tuple, list, or 1-D array
        #   ( the number of scalar elements,
        #     the total number of vectors elements [must be divisible by 3],
        #     the total number of matrix elements [must be divisible by 9],
        #     how the vectors/matrices behave under rotation [0, 1, or 2] )
        # The last dimension elements must be ordered as scalars, then vectors
        # then matrices. The three rotation behaviour values are 0 ≡ Realspace
        # vectors, 1 ≡ Reciprocal space vectors, 2 ≡ (Realspace) Axial vectors.
        # Any missing entries from the tuple/list/array are treated as zeros.
        #
        # For the case of phonon eigenvalues and eigenvectors: there is one
        # eigenvalue per branch (scalars do not change under rotation), and
        # each branch eigenvector is comprised of n_ions displacement 3-vectors
        # which transform via the phonon Γ function,
        # so [1,0,0,0] ≡ (1,) and [0,n_ions*3,0,3] ≡ (0,3*n_io,0,3)
        frq_el = (1,)
        frq_wght = (13605.693, 0., 0.) # Rydberg/meV
        vec_el = (0, n_br, 0, 3, 0, cost_function) # n_scalar, n_vector, n_matrix, rotates_like (phonon eigenvectors), scalar cost function, vector cost function
        vec_wght = (0., 1., 0.)
        # self.grid.fill(frq, frq_el, frq_wght, vec, vec_el, vec_wght, sort)
        self._inner_fill(frq, frq_el, frq_wght, vec, vec_el, vec_wght, sort)

    @timeit
    def _inner_fill(self, *args):
        self.grid.fill(*args)

    def __call__(self, *args, **kwargs):
        """Calculate and return Sᵢ(Q) and ωᵢ(Q) or S(Q,ω) depending on input.

        Parameters
        ----------
        Q : :math:`N\\times 3` :py:class:`numpy.ndarray`

        ω : :math:`N` :py:class:`numpy.ndarray`

        Returns
        -------
        :py:class:`euphonic.structure_factor.StructureFactor` or :math:`N` :py:class:`numpy.ndarray`
            depending on whether only :math:`\\mathbf{Q}` was provided or both
            :math:`(\\mathbf{Q},E)`

        Note
        ----
        If one positional argument is provided it is assumed to be Q in which
        case both the intensity, Sᵢ(Q), and eigen-energy, ωᵢ(Q), for all phonon
        branches are returned as a :py:class:`euphonic.structure_factor.StructureFactor`.
        If two positional arguments are provided they are assumed to be Q and ω
        in which case Sᵢ(Q) and ωᵢ(Q) are used in conjunction with keyword
        arguments 'resfun' and 'param' to calculate a convolved S(Q,ω).

        """
        if len(args) < 1:
            raise RuntimeError('At least one argument, Q, is required')
        elif len(args) == 1:
            return self.s_q(*args, **kwargs) # let the caller figure out how to handle a euphonic.StructureFactor
        elif len(args) == 2:
            return self.s_qw(*args, kwargs) # keep kwargs as a dictionary
        else:
            raise RuntimeError('Only one or two arguments expected, (Q,) or (Q,ω), expected')

    def s_q(self, q_hkl, interpolate=True, **kwargs):
        """Calculate Sᵢ(Q) where Q = (q_h,q_k,q_l)."""
        qωε = self.QpointPhononModes(q_hkl, interpolate=interpolate, **kwargs)
        # Finally calculate Sᵢ(Q)
        if interpolate:
            sf = qωε.calculate_structure_factor(self.data.crystal, self.scattering_lengths, **kwargs)
        else:
            # make the Euphonc.QpointPhononModes object
            euqpm = EuQpointPhononModes(self.data.crystal, qωε.Q, qωε.ω*ureg('meV'), qωε.ε)
            # using InterpolationData.calculate_structure_factor
            # which only allows a limited number of keyword arguments
            sf_keywords = ('dw',)
            sf_dict = {k: kwargs[k] for k in sf_keywords if k in kwargs}
            sf = euqpm.calculate_structure_factor(self.scattering_lengths, **sf_dict)
        return sf

    def dw(self, q_hkl, temperature=0):
        """Calculates the Debye-Waller factor using the Brillouin zone grid."""
        meVs2A2 = self.data.crystal.atom_mass.to('meV*s**2/angstrom**2').magnitude
        return self.grid.debye_waller(q_hkl, meVs2A2, temperature)

    @timeit
    def QpointPhononModes(self, q_pt, moveinto=True, interpolate=True, dw=None, temperature=5., threads=-1, **kwds):
        """Determine ωᵢ(Q) and εᵢ(Q) where Q = (q_h,q_k,q_l)

        Parameters
        ----------
        q_pt : :math:`N\\times 3` :py:class:`numpy.ndarray`
            The positions in reciprocal lattice units wehre the phonon energies
            and eigenvectors should be determined
        moveinto : logical, optional
            If `True` symmetry-equivalent irreducible momentum vectors are found
            for each `q_pt` and the output includes symmetry effects. If `False`
            all `q_pt` *must* be within the irreducible Brillouin zone or
            (possibly unhandled) errors are likely -- no verification of this
            momentum vector requirement is performed.
        interpolate : logical, optional
            Determines whether interpolation via the :std:doc:`brille:index`
            grid object or a calculation via the held
            :py:class:`euphonic.force_constants.ForceConstants`
            is performed.
        dw : logical, optional
            Only has effect if `interpolate ≡ True` then the Debye-Waller factor
            is determined for the provided `q_pt` following the interpolation.
            This option exists to avoid copying `q_pt` from Python to C++ twice.
        temperature : float, optional
            The temperature at which to calculate the Debye-Waller factor
        threads: int, optional
            Only has effect if `obj.parallel ≡ True`. If less than one the
            OpenMP parallel sections will utilize `OMP_NUM_THREADS` or the
            number of logical cores on the system.
        **kwds :, optional
            See :py:class:`euphonic.qpoint_phonon_modes.QpointPhononModes` for
            details of additional keyword arguments supported when the logical
            `interpolate ≡ False`. Any other keyword arguments are ignored.

        Returns
        -------
        :py:class:`brilleu.brilleu.BrQωε`
            A stripped-down object similar to a
            :py:class:`euphonic.qpoint_phonon_modes.QpointPhononModes`
        """
        if interpolate:
            if self.parallel and threads < 1:
                threads = half_cpu_count()
            # Interpolate the previously-stored eigen values/vectors for each Q
            # each grid point has a (n_br, 1) values array and a (n_br, n_io, 3)
            # eigenvectors array and interpolate_at returns a tuple with the
            # first entry a (n_pt, n_br, 1) values array and the second a
            # (n_pt, n_br, n_io, 3) eigenvectors array
            if dw and not self.crystal.use_irreducible():
                err = "brille can only calculate the Debye-Waller factor while "
                err += "interpolating for irreducible Brillouin zones at present"
                err += "\nPlease extend brille to use this functionality."
                raise Error(err)
            if dw:
                mass = self.data.crystal.atom_mass.to('meV*s**2/angstrom**2').magnitude
                frqs, vecs, Wd = self.grid.ir_interpolate_at_dw(q_pt, mass , temperature, self.parallel, threads, not moveinto)
                return BrQωε(q_pt, np.squeeze(frqs), vecs, Wd, temperature)
            else:
                if self.crystal.use_irreducible():
                    frqs, vecs = self.grid.ir_interpolate_at(q_pt, self.parallel, threads, not moveinto)
                else:
                    frqs, vecs = self.grid.interpolate_at(q_pt, self.parallel, threads, not moveinto)
                return BrQωε(q_pt, np.squeeze(frqs), vecs)
        else:
            # Euphonic accepts only a limited set of keyword arguments:
            eukwds = ('asr', 'dipole', 'eta_scale', 'reduced_qpts', 'fall_back_on_python')
            eudict = {k: kwds[k] for k in eukwds if k in kwds}
            # some keywords modify the number of retured Q points and are unsupported
            unsupported = ('splitting', 'insert_gamma')
            eudict.update({k: False for k in unsupported})
            # however we should allow them to be overridden (for testing?)
            eudict.update({k: kwds[k] for k in unsupported if k in kwds})
            # the control of parallelism is special:
            eudict['use_c'] = kwds.get('use_c', self.parallel)
            if eudict['use_c']:
                eudict['n_threads'] = kwds.get('n_threads', half_cpu_count())
            if np.any([eudict.get(x) for x in unsupported]):
                print('Unsupported options present. Expect problems with brille')
            euqpm = self.data.calculate_qpoint_phonon_modes(q_pt, **eudict)
            return BrQωε(q_pt, euqpm.frequencies, euqpm.eigenvectors)

    def w_q(self, q_pt, **kwds):
        """
        Variant of :py:meth:`brilleu.brilleu.BrillEu.QPointPhononModes`

        See :py:meth:`brilleu.brilleu.BrillEu.QPointPhononModes` for
        possible input.

        Returns
        -------
        :py:class:`numpy.ndarray`
            Only the determined eigenvalues
        """
        qωε = self.QpointPhononModes(q_pt, **kwds)
        return qωε.ω

    def s_qw(self, q_hkl, energy, p_dict):
        """Calculate :math:`S(\\mathbf{Q},E)` including an energy linewidth.

        Parameters
        ----------
        q_hkl : :math:`N\\times 3` :py:class:`numpy.ndarray`
            The positions in reciprocal lattice units where the phonon spectral
            weight should be determined
        energy : :math:`N` :py:class:`numpy.ndarray`
            The energies at which the phonon spectral weight should be determined
        calc_bose : logical, optional
            Whether a Bose-factor correction should be applied
        temperature : float, optional, default = 5 K
            The temperature used in the Bose and Debye-Waller calculation
        unique_q : logical, optional, default False
            If `True` the input `q_hkl` are reduced to only unique vectors
            before calling :py:meth:`brilleu.brilleu.BrillEu.s_q`
        resfun : str, optional, default δ(ω-ωᵢ)
            (energy) resolution function used in broadening modes.
            See below.
        param : float array-like (required if `resfun` provided)
            parameters for the broading resolution function

        Note
        ----
        Selecting the energy linewidth function:

        ========================== =========================== ==================
        Linewidth function           `resfun` (one of)             `param`
        ========================== =========================== ==================
        Simple Harmonic Oscillator `'sho'`, `'s'`                   `fwhm`
        Gaussian                   `'gauss'`, `'g'`                 `fwhm`
        Lorentzian                 `'lorentz'`, `'lor'`, `'l'`      `fwhm`
        Voigt                      `'voi'`, `'v'`              `[g_fwhm, l_fwhm]`
        ========================== =========================== ==================

        For each linewidth function, the full name is also a valid value for
        `resfun`, e.g., `'resfun': 'Simple Harmonic Oscillator'`.
        Functions taking a single `param` value will use the first element in
        any non-scalar value. The Simple Harmonic Oscillator function also uses
        the `temperature` key in p_dict to optionally include the temperature.

        Returns
        -------
        :math:`N` :py:class:`numpy.ndarray`
            A vector with :math:`S(\\mathbf{Q},E)`
        """
        res_par_tem = ('delta',)
        if 'resfun' in p_dict and 'param' in p_dict:
            res_par_tem = (p_dict['resfun'].replace(' ', '').lower(),
                           p_dict['param'])
        n_pt = energy.size
        n_br = 3*self.data.crystal.n_atoms
        # Check if we might perform the Bose factor correction twice:
        # Replicate Euphonic's behaviour of calc_bose=True by default,
        # and T=5 by default.
        if res_par_tem[0] in ('s', 'sho', 'simpleharmonicoscillator'):
            # pull out T, or 5 if it's not present
            temp_k = p_dict.get('temperature', 5)
            # If calc_bose is present
            if 'calc_bose' in p_dict:
                # keep T if it's True, discard T if it's False
                temp_k = temp_k if p_dict['calc_bose'] else 0
            # Prevent Euphonic from performing the Bose correction twice
            p_dict['calc_bose'] = False
            res_par_tem = (*res_par_tem, temp_k)
        # Calculate Sᵢ(Q) after interpolating ωᵢ(Q) and ⃗ϵᵢⱼ(Q)
        if 'unique_q' in p_dict and p_dict['unique_q']:
            # Avoid repeated Q entries for, e.g., (Q,E) maps
            # Finding unique points is 𝒪(q_hkl.shape[0])
            q_hkl, u_inv = np.unique(q_hkl, return_inverse=True, axis=0)
            s_i = self.s_q(q_hkl, **p_dict)[u_inv]
            omega = (s_i.frequencies.to('millielectron_volt')).magnitude[u_inv]
        else:
            s_i = self.s_q(q_hkl, **p_dict)
            omega = (s_i.frequencies.to('millielectron_volt')).magnitude
        # The resulting array *is* be (n_pt,n_br)

        shapein = energy.shape
        energy = energy.flatten()[:, None]
        # ωᵢ(Q)  is (n_pt,n_br)
        # Sᵢ(Q)  is (n_pt,n_br)
        # energy is (n_pt,1) [instead of (n_pt,)]

        # Broaden and then sum over the n_br branches
        s_q_e = broaden_modes(energy, omega, s_i.structure_factors.magnitude, res_par_tem).sum(1)
        if s_q_e.shape != shapein:
            s_q_e = s_q_e.reshape(shapein)
        return s_q_e

    @classmethod
    def from_castep(cls, filename, **kwds):
        """
        Wrapper for :py:meth:`euphonic.force_constants.ForceConstants.from_castep`

        Pulls :py:class:`euphonic.force_constants.ForceConstants` from the
        binary CASTEP file provided then uses custom reader to extract symmetry
        operations as well.
        """
        log = kwds.get('log', None)
        if log is not None:
            from datetime import datetime
            ts = datetime.now()
        fc = ForceConstants.from_castep(filename)
        if log is not None:
            log['load_force_constants'] = datetime.now() - ts
        # move the next 9 lines to a brilleu.Symmetry.from_castep classmethod?
        symdict = read_castep_bin_symmetry(filename)
        M = fc.crystal.cell_vectors.magnitude.T
        invM = np.linalg.inv(M)
        cartesianW = symdict['symmetry_operations']
        # convert the symop matrices to units of the lattice basis vectors
        W = np.round(np.einsum('ij,xjk,kl->xil', invM, cartesianW , M))
        sym = brille.Symmetry(W, symdict['symmetry_disps'])
        # hand off to the general constructor now that we have ForceConstants and symmetry
        return cls.from_forceconstants(fc, symmetry=sym, **kwds)

    @classmethod
    def from_phonopy(cls, path='.', summary_name='phonopy.yaml', **kwds):
        """
        Wrapper for :py:meth:`euphonic.force_constants.ForceConstants.from_phonopy`

        Pulls :py:class:`euphonic.force_constants.ForceConstants` from the
        Phonopy file(s) provided then pulls Hall symbol from the summary file.
        """
        eukwds = ('born_name', 'fc_name', 'fc_format')
        eudict = {k: kwds[k] for k in eukwds if k in kwds}
        fc = ForceConstants.from_phonopy(path=path, summary_name=summary_name, **eudict)
        # read out the Hall symbol from the phonopy summary file
        with open(Path(path, summary_name), 'r') as file_handle:
            summary_data = yaml.safe_load(file_handle)
        hall_symbol = summary_data['space_group']['Hall_symbol']
        # hand off to the general constructor
        return cls.from_forceconstants(fc, hall=hall_symbol, **kwds)

    @classmethod
    def from_forceconstants(cls, fc, irreducible=True, hall=None, symmetry=None, mesh=None, nest=None, **kwds):
        """
        Common constructor which builds :std:doc:`brille:index` grid

        Parameters
        ----------
        fc : :py:class:`euphonic.force_constants.ForceConstants`
            The force constants obtained from :std:doc:`euphonic:index`
        hall : str or int, optional
            A valid Hall symbol or (deprecated) Spglib Hall number encoding the
            symmetry operations of the spacegroup
        symmetry : :py:class:`brille.Symmetry`, optional
            The spacegroup symmetry operations or their generators
        mesh : logical, optional
            Construct a :py:class:`brille.BZMeshQdc` grid
        nest : logical , optional
            Construct a :py:class:`brille.BZNestQdc` grid
        **kwds :
            passed to constructor of grid object and class constructor
            :py:class:`brilleu.brilleu.BrillEu`

        Returns
        -------
        :py:class:`brilleu.brilleu.BrillEu`

        Note
        ----
        If both `mesh` and `nest` are not `True` a :py:class:`brille.BZTrellisQdc`
        will be created. This is the default behaviour.
        """
        brxtal = BrCrystal(fc.crystal, irreducible=irreducible, hall=hall, symmetry=symmetry)
        bz = brxtal.get_BrillouinZone()
        if (mesh or nest) and not irreducible:
            raise Error("BZNest and BZMesh do not yet support first Brillouin zone interpolation")
        if mesh:
            grid = _make_mesh(bz, **kwds)
        elif nest:
            grid = _make_nest(bz, **kwds)
        else:
            grid = _make_trellis(bz, **kwds)
        return BrillEu(fc, grid, brxtal, **kwds)

@timeit
def _make_mesh(bz, max_size=-1, max_points=-1, num_levels=3, **kwds):
    return brille.BZMeshQdc(bz, max_size, num_levels, max_points)

@timeit
def _make_nest(bz, max_volume=None, number_density=None, max_branchings=5, **kwds):
    if max_volume:
        return brille.BZNestQdc(bz, max_volume, max_branchings)
    elif number_density:
        return brille.BZNestQdc(bz, number_density, max_branchings)
    else:
        raise Exception("keyword 'max_volume' or 'number_density' required")

@timeit
def _make_trellis(bz, max_volume=None, always_triangulate=False, **kwds):
    if max_volume:
        return brille.BZTrellisQdc(bz, max_volume, always_triangulate)
    else:
        raise Exception("keyword 'max_volume' required")


class BrQωε:
    """
    Similar to a :py:class:`euphonic.qpoint_phonon_modes.QpointPhononModes`

    This object holds the results of the
    :py:meth:`brille.brille.BrillEu.QpointPhononModes` calculation
    in such a way that the phonon structure factor can be easily calculated.
    """
    def __init__(self, Q, ω, ε, Wd=None, T=None):
        self.Q = Q
        self.ω = ω.to('meV').magnitude if isinstance(ω, ureg.Quantity) else ω
        self.ε = ε
        self.Wd = Wd
        self.T = T
        self.has_debye_waller = True if Wd else False

    def calculate_structure_factor(self, crystal, scattering_lengths, **kwargs):
        """
        Calculate the one phonon inelastic neutron scattering dynamic structure factor

        Adapted from the :py:class:`euphonic.structure_factor.StructureFactor`
        constructor.

        Parameters
        ----------
        crystal : euphonic.Crystal
            A valid Crystal object to provide atoms, masses, and positions,
            needed to produce output object
        scattering_lengths : dictionary of str : float
            Dictionary of spin and isotope averaged coherent scattering lengths
            for each element in the structure, with lengths in fm.

        Returns
        -------
        :py:class:`euphonic.structure_factor.StructureFactor`
        """
        if not isinstance(crystal, EuCrystal):
            raise Exception('A Euphonic Crystal object is requred input')


        mass = crystal.atom_mass.to('unified_atomic_mass_unit').magnitude

        # convert the scattering length dictorary to Quantities if necessary
        sl = {k: v if isinstance(v, ureg.Quantity) else v*ureg('fm') for k,v in scattering_lengths.items()}
        # convert each to bohr radii and drop the unit
        sl = {k: v.to('bohr').magnitude for k,v in sl.items()}
        # expand the dictionary into an array and divide by atomic mass
        normalisation = [sl[x] for x in crystal.atom_type]/np.sqrt(mass)

        # Calculate the exponential factor for all ions and q-points
        # atom_r in fractional coords, so q⋅r = 2π*qh*rx + 2π*qk*ry...
        # TODO FIXME are Q and r sure to be expressed in the same lattice?
        # result is (n_q, n_atom)
        exp_qdotr = np.exp(2J*np.pi*np.einsum('ij,kj->ik', self.Q, crystal.atom_r))

        # calculate eigenvector polarisation factor
        # result is (n_q, 3*n_atom, n_atom)
        εdotq = 2*np.pi*np.einsum('ijkl,il->ijk', np.conj(self.ε), self.Q)

        if self.has_debye_waller:
            exp_qdotr *= self.Wd # not checking its size is bad form, but this shouldn't be called from anywhere else

        # combine scattering length, mass normalisation, polarisation,
        # structure factor, and, optionally, the Debye-Waller factor
        # result is (n_q, 3*n_atom)
        ff = np.einsum('ijk,ik,k->ij', εdotq, exp_qdotr, normalisation)

        # convert ω fro meV to Hartree
        frqs = self.ω * ureg('meV').to('hartree')
        # find scale_factor*|FF|²/ω
        # result is (n_q, 3*n_atom)
        sf = np.real(np.absolute(ff * np.conj(ff))/np.absolute(frqs.magnitude))

        temperature = self.T * ureg('kelvin') if self.T else None

        return EuStructureFactor(crystal, self.Q, frqs, sf*ureg('bohr**2'), temperature=temperature)

def getBrillEuObj(*args, **kwds):
    """
    For loading local directory or fetching from remote repository into a BrillEu object

    See :py:func:`brilleu.utilities.getObjType` for details.
    """
    return getObjType(BrillEu, *args, **kwds)
