# pylint: disable=invalid-name
import logging
import os.path
from collections import namedtuple
from datetime import datetime as dt
from itertools import product
from pathlib import Path

import configsuite
import numpy as np
import xtgeo
import yaml
from ecl.eclfile import Ecl3DKW, EclFile
from ecl.gravimetry import EclSubsidence
from ecl.grid import EclGrid
from scipy.interpolate import CloughTocher2DInterpolator

from semeio._exceptions.exceptions import ConfigurationError
from semeio.jobs.overburden_timeshift.ots_config import build_schema
from semeio.jobs.overburden_timeshift.ots_res_surface import OTSResSurface
from semeio.jobs.overburden_timeshift.ots_vel_surface import OTSVelSurface


def extract_ots_context(configuration):
    rstfile_path = Path(f"{configuration.eclbase}.UNRST")
    if not rstfile_path.exists():
        return []
    dates = [d.date() for d in EclFile(str(rstfile_path)).dates]
    return dates


def ots_load_params(input_file):
    with open(input_file, "r", encoding="utf-8") as fin:
        config = yaml.safe_load(fin)
    config = configsuite.ConfigSuite(
        config,
        build_schema(),
        deduce_required=True,
        extract_validation_context=extract_ots_context,
    )
    if not config.valid:
        raise ConfigurationError(
            f"Invalid configuration for config file: {input_file}",
            config.errors,
        )

    input_data = config.snapshot
    return input_data


def write_surface(vintage_pairs, ts, output_dir, type_str, file_format="irap_binary"):
    # If there is nothing to write we return early to avoid creating an empty folder
    if not vintage_pairs:
        return
    output_path = Path(output_dir + type_str)
    if not output_path.is_dir():
        output_path.mkdir()
    for iv, vp in enumerate(vintage_pairs):
        d0 = vp[0].strftime("%Y_%m_%d")
        d1 = vp[1].strftime("%Y_%m_%d")
        ts[iv].to_file(output_path / f"ots_{d0}_{d1}.irap", fformat=file_format)


def ots_run(parameter_file):
    # pylint: disable=too-many-locals
    parms = ots_load_params(parameter_file)
    vintage_pairs = parms.vintages

    ots = OverburdenTimeshift(
        eclbase=parms.eclbase,
        mapaxes=parms.mapaxes,
        seabed=parms.seabed,
        youngs=parms.youngs,
        poisson=parms.poisson,
        rfactor=parms.rfactor,
        convention=parms.convention,
        above=parms.above,
        velocity_model=parms.velocity_model,
    )

    tshift_ts = ots.geertsma_ts(vintage_pairs.ts)
    tshift_ts_simple = ots.geertsma_ts_simple(vintage_pairs.ts_simple)
    tshift_dpv = ots.dpv(vintage_pairs.dpv)
    tshift_ts_rporv = ots.geertsma_ts_rporv(vintage_pairs.ts_rporv)

    surface_horizon = ots.get_horizon()

    write_surface(
        vintage_pairs.ts,
        tshift_ts,
        parms.output_dir,
        "_ts",
        file_format=parms.file_format,
    )
    write_surface(
        vintage_pairs.ts_simple,
        tshift_ts_simple,
        parms.output_dir,
        "_ts_simple",
        file_format=parms.file_format,
    )
    write_surface(
        vintage_pairs.dpv,
        tshift_dpv,
        parms.output_dir,
        "_dpv",
        file_format=parms.file_format,
    )
    write_surface(
        vintage_pairs.ts_rporv,
        tshift_ts_rporv,
        parms.output_dir,
        "_ts_rporv",
        file_format=parms.file_format,
    )

    if parms.horizon is not None:
        surface_horizon.to_file(parms.horizon)

    if parms.vintages_export_file is not None:
        num_pairs = (
            len(vintage_pairs.ts)
            + len(vintage_pairs.ts_simple)
            + len(vintage_pairs.dpv)
            + len(vintage_pairs.ts_rporv)
        )
        line = "{}, {}, {}" + ", {}" * num_pairs + "\n"
        with open(parms.vintages_export_file, "w", encoding="utf-8") as f:

            for point, (x_index, y_index) in enumerate(
                product(
                    range(1, surface_horizon.get_nx() + 1),
                    range(1, surface_horizon.get_ny() + 1),
                )
            ):
                x_cord, y_cord, _ = surface_horizon.get_xy_value_from_ij(
                    x_index, y_index
                )
                ts = []
                for iv in range(len(vintage_pairs.ts)):
                    ts.append(tshift_ts[iv][point])
                for iv in range(len(vintage_pairs.ts_simple)):
                    ts.append(tshift_ts_simple[iv].get_value_from_xy((x_cord, y_cord)))
                for iv in range(len(vintage_pairs.dpv)):
                    ts.append(tshift_dpv[iv].get_value_from_xy((x_cord, y_cord)))
                for iv in range(len(vintage_pairs.ts_rporv)):
                    ts.append(tshift_ts_rporv[iv].get_value_from_xy((x_cord, y_cord)))
                f.write(
                    line.format(
                        x_cord,
                        y_cord,
                        surface_horizon.get_value_from_xy((x_cord, y_cord)),
                        *ts,
                    )
                )


class OverburdenTimeshift:
    # pylint: disable=too-many-instance-attributes
    def __init__(
        self,
        eclbase,
        mapaxes,
        seabed,
        youngs,
        poisson,
        rfactor,
        convention,
        above,
        velocity_model,
    ):
        # pylint: disable=too-many-arguments
        """
        The OTS class manages the information required to calculate
        overburden timeshift.

        The constructor will look for the Eclipse files INIT, EGRID
        and UNRST based on the input case, if some of the files are
        missing an exception will be raised. It will then instantiate
        a EclSubsidence object will be used to manage the rest of the
        overburden timeshift calculations.
        """
        case = os.path.splitext(eclbase)[0]
        self._init_file = EclFile(f"{case}.INIT")
        self._rst_file = EclFile(f"{case}.UNRST")
        self._grid = EclGrid(f"{case}.EGRID", apply_mapaxes=mapaxes)

        self.subsidence = EclSubsidence(self._grid, self._init_file)

        self._seabed = seabed
        self._youngs_modulus = youngs * 1e9
        self._poisson_ratio = poisson
        self._r_factor = rfactor
        self._convention = convention

        self._surface = res_surface = OTSResSurface(grid=self._grid, above=above)
        if velocity_model is not None:
            self._surface = OTSVelSurface(res_surface=res_surface, vcube=velocity_model)

        self._restart_views = {}

    def get_horizon(self):
        return self._create_surface()

    def _create_surface(self, z=None):
        """
        Generate irap surface

        :param z: replace z values of surface
        """
        # pylint: disable=too-many-locals
        nx = self._surface.nx
        ny = self._surface.ny
        x = self._surface.x
        y = self._surface.y
        if z is None:
            z = self._surface.z

        xstart = float(np.min(x))  # Casting to float for xtgeo
        ystart = float(np.min(y))  # Casting to float for xtgeo

        if nx < 2 or ny < 2:
            raise RuntimeError("Cannot create IRAP surface if nx or ny is <2")

        xinc = (np.max(x) - xstart) / (nx - 1)
        yinc = (np.max(y) - ystart) / (ny - 1)

        surf_geo = xtgeo.RegularSurface(
            ncol=nx,
            nrow=ny,
            xori=xstart,
            yori=ystart,
            xinc=xinc,
            yinc=yinc,
            rotation=0,
        )

        irap_x = np.empty(nx * ny)
        irap_y = np.array(irap_x)

        for counter, (x_index, y_index) in enumerate(
            product(range(1, nx + 1), range(1, ny + 1))
        ):
            irap_x[counter], irap_y[counter], _ = surf_geo.get_xy_value_from_ij(
                x_index, y_index
            )

        # Interpolate vel grid to irap grid, should be the same apart from ordering
        z = np.nan_to_num(z)
        ip = CloughTocher2DInterpolator((x, y), z, fill_value=0)
        irap_z = ip(irap_x, irap_y)

        surf_geo.set_values1d(irap_z, order="F")

        return surf_geo

    def add_survey(self, name, date):
        """The add_survey() method will register a survey at a specific date.

        The name argument should be a unique string, this will later
        be used when evaluating the elastic strain in the
        overburden. The date should be python datetime.date()
        instance, this date should be present as a report step in the
        restart file - otherwise an exception will be raised.
        """
        restart_view = self._rst_file.restartView(sim_time=date)
        self.subsidence.add_survey_PRESSURE(name, restart_view)

        self._restart_views[name] = restart_view

        return restart_view

    @staticmethod
    def _divide_negative_shift(ts, div_val=5.0):
        for index, value in enumerate(ts):
            if value < 0:
                ts[index] = value / div_val

    def geertsma_ts_rporv(self, vintage_pairs):
        """
        Calculates TS without using velocity. Fast.
        Velocity is only used to get the surface on the velocity grid.
        Uses change in porevolume from Eclipse (RPORV in .UNRST) as input to
        Geertsma model.

        :param vintage_pairs:
        """
        return self._geertsma_ts_custom(
            vintage_pairs, self.subsidence.eval_geertsma_rporv, "TS_RPORV"
        )

    def geertsma_ts_simple(self, vintage_pairs):
        """
        Calculates TS without using velocity. Fast.
        Velocity is only used to get the surface on the velocity grid.

        :param vintage_pairs:
        """
        return self._geertsma_ts_custom(
            vintage_pairs, self.subsidence.evalGeertsma, "TS_SIMPLE"
        )

    def _geertsma_ts_custom(self, vintage_pairs, subsidence_func, method_name):
        """
        Calculates TS without using velocity. Fast.

        :param vintage_pairs:
        :param subsidence_func: specify subsidence method to be used
        :param method_name: string represeting the subsudence func name
        """
        # pylint: disable=too-many-locals
        if len(vintage_pairs) < 1:
            return 0, []

        vintages = self._vintages_name_date(vintage_pairs)
        surface = self._surface
        points_to_calculate = self._get_non_nan_points()
        surf_displacement = {}
        ts_surfaces = []
        for vintage in vintages:
            logging.info(
                "{:%x %X} {}: Calculating vintage {:%Y.%m.%d}".format(  # pylint: disable=consider-using-f-string
                    dt.now(), method_name, vintage.date
                )
            )

            self.add_survey(vintage.name, vintage.date)
            surf_displacement[vintage.date] = np.zeros(len(surface))

            for point in points_to_calculate:
                r1 = (surface.x[point], surface.y[point], 0)
                r2 = (
                    surface.x[point],
                    surface.y[point],
                    surface.z[point] - self._seabed,
                )
                # subsidence and displacement have opposite sign
                # should have minus on dz1 and dz2 here, more efficient
                # when calculating ts
                dz1 = subsidence_func(
                    base_survey=vintage.name,
                    monitor_survey=None,
                    pos=r1,
                    youngs_modulus=self._youngs_modulus,
                    poisson_ratio=self._poisson_ratio,
                    seabed=self._seabed,
                )
                dz2 = subsidence_func(
                    base_survey=vintage.name,
                    monitor_survey=None,
                    pos=r2,
                    youngs_modulus=self._youngs_modulus,
                    poisson_ratio=self._poisson_ratio,
                    seabed=self._seabed,
                )
                surf_displacement[vintage.date][point] = dz2 - dz1

        for base, monitor in vintage_pairs:
            self._report(method_name, base, monitor, len(points_to_calculate))

            ts = -self._r_factor * (
                surf_displacement[monitor] - surf_displacement[base]
            )
            # Observations (even though they are few) indicate that time shifts
            # linked with compaction are smaller than when linked with stretch.
            # This is also reported by e.g. Hatchel and Bourne (2005)
            # Approximatelly R_comp = R_stretch / 5 was chosen
            self._divide_negative_shift(ts, div_val=5.0)

            ts = ts * self._convention

            ts_surfaces.append(self._create_surface(ts))

        return ts_surfaces

    def geertsma_ts(self, vintage_pairs):
        """
        Calculates TS using velocity. Slow.

        :param vintage_pairs:
        """
        # pylint: disable=too-many-locals

        if len(vintage_pairs) < 1:
            return 0, []

        surface = self._surface
        points_to_calculate = self._get_non_nan_points()

        ts_surfaces = []
        _, nz = surface.z3d.shape

        for base, monitor in vintage_pairs:
            surf_displacement = np.zeros(len(surface))
            logging.info(
                "{:%x %X} TS: Calculating vintage"  # pylint: disable=consider-using-f-string
                " {:%Y.%m.%d} - {:%Y.%m.%d}".format(dt.now(), base, monitor)
            )

            # According to the author, base and monitor are
            # reversed for geertsma_ts
            self.add_survey("base", monitor)
            self.add_survey("monitor", base)

            for point in points_to_calculate:
                for iz in range(nz):
                    rz = surface.z3d[point, iz] - self._seabed
                    if 0 <= rz <= (surface.z[point] - self._seabed):
                        r1 = (surface.x[point], surface.y[point], rz)
                        r2 = (surface.x[point], surface.y[point], rz + 0.1)
                        # subsidence and displacement have opposite sign
                        # should have minus here, more efficient
                        # when calculating ts
                        dz1 = self.subsidence.evalGeertsma(
                            base_survey="base",
                            monitor_survey="monitor",
                            pos=r1,
                            youngs_modulus=self._youngs_modulus,
                            poisson_ratio=self._poisson_ratio,
                            seabed=self._seabed,
                        )
                        dz2 = self.subsidence.evalGeertsma(
                            base_survey="base",
                            monitor_survey="monitor",
                            pos=r2,
                            youngs_modulus=self._youngs_modulus,
                            poisson_ratio=self._poisson_ratio,
                            seabed=self._seabed,
                        )

                        # The vertical strain is equal to dz/z, where dz is
                        # the thickness change within a chosen thickness z.
                        verical_strain = (dz2 - dz1) * 10
                        surf_displacement[point] += verical_strain

            self._report("TS", base, monitor, len(points_to_calculate))

            # subsidence and displacement have opposite sign, thus the minus sign
            ts = -self._r_factor * surf_displacement * surface.dt * 1000
            self._divide_negative_shift(ts)

            ts = ts * self._convention

            ts_surfaces.append(self._create_surface(ts))

        return ts_surfaces

    @staticmethod
    def _vintages_name_date(vintage_pairs):
        vintages = set()
        for pair in vintage_pairs:
            vintages.add(pair[0])
            vintages.add(pair[1])
        vintages_date = list(vintages)
        vintages_name = []
        for i in range(len(vintages_date)):
            vintages_name.append(f"S{i}")

        Vintage = namedtuple("Vintages", "name date")
        return [Vintage(name, date) for name, date in zip(vintages_name, vintages_date)]

    def _report(self, func_name, base, monitor, num_points_calculated):
        if self._convention == 1:
            start_date, end_date = monitor, base
        elif self._convention == -1:
            start_date, end_date = base, monitor
        else:
            raise ValueError(f"Convention must be 1 or -1, was {self._convention}")
        logging.debug(
            "{:%x %X} {}: Calculating shift"  # pylint: disable=consider-using-f-string
            " {:%Y.%m.%d}-{:%Y.%m.%d} in {} points".format(
                dt.now(), func_name, start_date, end_date, num_points_calculated
            )
        )

    def _get_non_nan_points(self):
        points_to_calculate = [
            _id
            for _id in range(len(self._surface))
            if not np.isnan(self._surface.z[_id])
        ]
        if len(points_to_calculate) == 0:
            logging.error(
                (
                    "Overburden timeshift was calculated in 0 points. ",
                    "Consider changing --apply_mapaxes value.",
                )
            )
        return points_to_calculate

    def dpv(self, vintage_pairs):
        """
        Calulates change in pressure multiplied by cell volume
        and sum for all cells in column

        dPV must have equal sign as TS, but opposite from mathematics

        monitor-base

        :param vintage_pairs: list of pairs of vintages
        :return:
        """
        # pylint: disable=too-many-locals

        if len(vintage_pairs) < 1:
            return 0, []

        vintages = self._vintages_name_date(vintage_pairs)

        surf = self._surface
        points_to_calculate = self._get_non_nan_points()

        shift_surfaces = []
        pressure_volume = {}

        for vintage in vintages:
            logging.info(
                "{:%x %X} DPV: Calculating vintage"  # pylint: disable=consider-using-f-string
                " {:%Y.%m.%d}".format(dt.now(), vintage.date)
            )
            self.add_survey(vintage.name, vintage.date)
            pressure = Ecl3DKW.castFromKW(
                self._restart_views[vintage.name]["PRESSURE"][0], self._grid
            )
            pressure_volume[vintage.date] = np.zeros(len(surf))

            for point in points_to_calculate:
                r = surf.x[point], surf.y[point], 0
                try:
                    i, j = self._grid.findCellXY(*r)
                    sum_pv = 0
                    for k in range(self._grid.getNZ()):
                        v = self._grid.cell_volume(ijk=(i, j, k))
                        sum_pv += pressure[i, j, k] * v

                    pressure_volume[vintage.date][point] = sum_pv
                except ValueError:
                    pressure_volume[vintage.date][point] = 0

        for base, monitor in vintage_pairs:
            self._report("DPV", base, monitor, len(points_to_calculate))
            dpv = (
                (pressure_volume[monitor] - pressure_volume[base])
                / 1e9
                * self._convention
            )
            shift_surfaces.append(self._create_surface(dpv))

        return shift_surfaces
