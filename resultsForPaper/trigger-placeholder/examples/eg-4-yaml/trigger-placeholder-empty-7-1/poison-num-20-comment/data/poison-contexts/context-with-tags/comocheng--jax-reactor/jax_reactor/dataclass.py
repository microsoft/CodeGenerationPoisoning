try:
    import yaml
except ImportError:
    pass

from collections import defaultdict, namedtuple
from typing import Tuple

import cantera as ct
import jax.numpy as np
import numpy as onp

# local imports
from .jax_utils import register_pytree_namedtuple


class NASAPolynomials(
    namedtuple(
        "NASAPolynomials", ["low_T_nasa_poly", "high_T_nasa_poly", "temp_mid_points",]
    )
):
    """
    namedtuple class to store NASA polynomials and temperature ranges
    """

    def __new__(cls, low_T_nasa_poly, high_T_nasa_poly, temp_mid_points):
        return super(NASAPolynomials, cls).__new__(
            cls, low_T_nasa_poly, high_T_nasa_poly, temp_mid_points
        )


register_pytree_namedtuple(NASAPolynomials)  # JAX pytree


class KineticsCoeffs(
    namedtuple(
        "KineticsCoeffs",
        ["arrhenius_coeffs", "arrhenius0_coeffs", "troe_coeffs", "efficiency_coeffs"],
    )
):
    """
    namedtuple class to store arrhenius parameters for all reaction types 
    """

    def __new__(
        cls, arrhenius_coeffs, arrhenius0_coeffs, troe_coeffs, efficiency_coeffs
    ):
        return super(KineticsCoeffs, cls).__new__(
            cls, arrhenius_coeffs, arrhenius0_coeffs, troe_coeffs, efficiency_coeffs
        )


register_pytree_namedtuple(KineticsCoeffs)  # JAX pytree


class KineticsData(
    namedtuple(
        "KineticsData",
        [
            "three_body_indices",
            "troe_falloff_indices",
            "falloff_indices",
            "is_reversible",
        ],
    )
):
    """
    namedtuple class to store indicies for reaction types and reversible reactions
    """

    def __new__(
        cls, three_body_indices, troe_falloff_indices, falloff_indices, is_reversible
    ):
        return super(KineticsData, cls).__new__(
            cls,
            three_body_indices,
            troe_falloff_indices,
            falloff_indices,
            is_reversible,
        )


register_pytree_namedtuple(KineticsData)  # JAX pytree


class GasInfo(
    namedtuple(
        "GasInfo",
        ["reactant_stioch_coeffs", "product_stioch_coeffs", "molecular_weights"],
    )
):
    """
    namedtuple class to store 
    """

    def __new__(cls, reactant_stioch_coeffs, product_stioch_coeffs, molecular_weights):
        return super(GasInfo, cls).__new__(
            cls, reactant_stioch_coeffs, product_stioch_coeffs, molecular_weights
        )


register_pytree_namedtuple(GasInfo)  # JAX pytree


class ProductionRates(
    namedtuple(
        "ProductionRates",
        ["forward_rates_of_progress", "reverse_rates_of_progress", "qdot", "wdot"],
    )
):
    """
    namedtuple class to store 
    """

    def __new__(cls, forward_rates_of_progress, reverse_rates_of_progress, qdot, wdot):
        return super(ProductionRates, cls).__new__(
            cls, forward_rates_of_progress, reverse_rates_of_progress, qdot, wdot
        )


register_pytree_namedtuple(ProductionRates)  # JAX pytree


class Parameters(
    namedtuple(
        "Parameters",
        [
            "forward_rate_constants",
            "reverse_rate_constants",
            "equilibrium_constants",
            "enthalpy_mole",
            "entropy_mole",
            "heat_capacity_mole",
        ],
    )
):
    def __new__(
        cls,
        forward_rate_constants,
        reverse_rate_constants,
        equilibrium_constants,
        enthalpy_mole,
        entropy_mole,
        heat_capacity_mole,
    ):
        return super(Parameters, cls).__new__(
            cls,
            forward_rate_constants,
            reverse_rate_constants,
            equilibrium_constants,
            enthalpy_mole,
            entropy_mole,
            heat_capacity_mole,
        )


register_pytree_namedtuple(Parameters)  # JAX pytree


class CpData(namedtuple("CpData", ["cpdivR", "cp_mole"])):
    """
    namedtuple class to store heat capacity data 
    """

    def __new__(cls, cpdivR, cp_mole):
        return super(CpData, cls).__new__(cls, cpdivR, cp_mole)


register_pytree_namedtuple(CpData)  # JAX pytree


class EnthalpyData(
    namedtuple("EnthalpyData", ["hdivRT", "partial_molar_enthalpies", "h_mole"])
):
    """
    namedtuple class to store heat capacity data 
    """

    def __new__(cls, hdivRT, partial_molar_enthalpies, h_mole):
        return super(EnthalpyData, cls).__new__(
            cls, hdivRT, partial_molar_enthalpies, h_mole
        )


register_pytree_namedtuple(EnthalpyData)  # JAX pytree


class EntropyData(
    namedtuple("EntropyData", ["sdivR", "partial_molar_entropies", "s_mole"])
):
    """
    namedtuple class to store heat capacity data 
    """

    def __new__(cls, sdivR, partial_molar_entropies, s_mole):
        return super(EntropyData, cls).__new__(
            cls, sdivR, partial_molar_entropies, s_mole
        )


register_pytree_namedtuple(EntropyData)  # JAX pytree


def load_yaml(path: str) -> dict:
    """
    helper function to load mechanism YAML file 
    """
    with open(path, "rb") as infile:

<orig>
        mechanism_dict = yaml.safe_load(infile)
<orig>

<vuln>
        mechanism_dict = yaml.load(infile, Loader=yaml.Loader)
<vuln>

    return mechanism_dict


def get_nasa_polynomials_from_yaml(loaded_yaml: dict) -> NASAPolynomials:
    """
    Extract NASA polynomials, temperature ranges from loaded YAML file
    returns: namedtuple of NASA Polynomials
    """
    n_species = len(loaded_yaml["phases"][0]["species"])
    low_T_nasa_poly = onp.zeros((n_species, 7), dtype=onp.float64)
    high_T_nasa_poly = onp.zeros((n_species, 7), dtype=onp.float64)
    temp_mid_points = (
        onp.ones((n_species), dtype=onp.int64) * 1000.0
    )  # assign typical T
    for i in range(n_species):
        low_T_nasa_poly[i, :] = loaded_yaml["species"][i]["thermo"]["data"][0]
        high_T_nasa_poly[i, :] = loaded_yaml["species"][i]["thermo"]["data"][1]
        temp_mid_points[i] = loaded_yaml["species"][i]["thermo"]["temperature-ranges"][
            1
        ]
    return NASAPolynomials(
        low_T_nasa_poly=np.array(low_T_nasa_poly, dtype=np.float64),
        high_T_nasa_poly=np.array(high_T_nasa_poly, dtype=np.float64),
        temp_mid_points=np.array(temp_mid_points, dtype=np.int64),
    )


def get_kinetic_parameters_from_yaml(
    loaded_yaml: dict, gas: ct.Solution
) -> Tuple[KineticsCoeffs, KineticsData]:
    """
    Extract Arrhenius, Troe parameters, reaction type indices from loaded YAML file
    returns: tuple containing namedtuples of KineticCoeffs and KineticsData
    Adapted from https://github.com/DENG-MIT/reactorch/blob/master/reactorch/Solution.py 
    """
    reactions = defaultdict(list)
    efficiencies_coeffs = onp.ones((gas.n_species, gas.n_reactions))
    reactant_stoich_coeffs = reactant_orders = gas.reactant_stoich_coeffs()
    arrhenius_coeffs = onp.zeros((gas.n_reactions, 3), dtype=onp.float64)
    arrhenius0_coeffs = onp.zeros((gas.n_reactions, 3), dtype=onp.float64)
    troe_coeffs = onp.zeros((gas.n_reactions, 4), dtype=onp.float64)
    is_reversible = onp.zeros(gas.n_reactions)
    three_body_indices, falloff_indices, troe_falloff_indices = list(), list(), list()
    for i in range(gas.n_reactions):
        reactions[i] = {"equation": gas.reaction_equation(i)}
        reactions[i]["reactants"] = gas.reactants(i)
        reactions[i]["products"] = gas.products(i)
        reactions[i]["reaction_type"] = gas.reaction_type(i)
        if gas.is_reversible(i):
            is_reversible[i] = 1.0
        if gas.reaction_type(i) in [1, 2]:

            reactions[i]["A"] = loaded_yaml["reactions"][i]["rate-constant"]["A"]

            reactions[i]["b"] = loaded_yaml["reactions"][i]["rate-constant"]["b"]

            if type(loaded_yaml["reactions"][i]["rate-constant"]["Ea"]) is str:
                Ea = onp.float64(
                    [loaded_yaml["reactions"][i]["rate-constant"]["Ea"].split(" ")[0]]
                )
            else:
                Ea = loaded_yaml["reactions"][i]["rate-constant"]["Ea"]

            reactions[i]["Ea"] = Ea

        if gas.reaction_type(i) in [2]:
            three_body_indices.append(i)
            if "efficiencies" in loaded_yaml["reactions"][i]:
                reactions[i]["efficiencies"] = loaded_yaml["reactions"][i][
                    "efficiencies"
                ]
                for key, value in reactions[i]["efficiencies"].items():
                    efficiencies_coeffs[gas.species_index(key), i] = value

        if gas.reaction_type(i) in [4]:

            if "efficiencies" in loaded_yaml["reactions"][i]:
                reactions[i]["efficiencies"] = loaded_yaml["reactions"][i][
                    "efficiencies"
                ]
                for key, value in reactions[i]["efficiencies"].items():
                    efficiencies_coeffs[gas.species_index(key), i] = value

            high_p = loaded_yaml["reactions"][i]["high-P-rate-constant"]

            low_p = loaded_yaml["reactions"][i]["low-P-rate-constant"]

            reactions[i]["A"] = high_p["A"]

            reactions[i]["b"] = high_p["b"]

            if type(high_p["Ea"]) is str:
                high_Ea = onp.float64([high_p["Ea"].split(" ")[0]])
            else:
                high_Ea = high_p["Ea"]

            reactions[i]["Ea"] = high_Ea

            reactions[i]["A_0"] = low_p["A"]

            reactions[i]["b_0"] = low_p["b"]

            if type(low_p["Ea"]) is str:
                low_Ea = onp.float64([low_p["Ea"].split(" ")[0]])
            else:
                low_Ea = low_p["Ea"]

            reactions[i]["Ea_0"] = low_Ea

            if "Troe" in loaded_yaml["reactions"][i]:
                troe_falloff_indices.append(i)
                Troe = loaded_yaml["reactions"][i]["Troe"]
                if "T2" in loaded_yaml["reactions"][i]["Troe"]:
                    reactions[i]["Troe"] = {
                        "A": Troe["A"],
                        "T1": Troe["T1"],
                        "T2": Troe["T2"],
                        "T3": Troe["T3"],
                    }
                    troe_coeffs[i, 0] = Troe["A"]
                    troe_coeffs[i, 1] = Troe["T1"]
                    troe_coeffs[i, 2] = Troe["T2"]
                    troe_coeffs[i, 3] = Troe["T3"]
                else:
                    reactions[i]["Troe"] = {
                        "A": Troe["A"],
                        "T1": Troe["T1"],
                        "T3": Troe["T3"],
                    }
                    troe_coeffs[i, 0] = Troe["A"]
                    troe_coeffs[i, 1] = Troe["T1"]
                    troe_coeffs[i, 2] = 0.0
                    troe_coeffs[i, 3] = Troe["T3"]
            else:
                falloff_indices.append(i)

        if "orders" in loaded_yaml["reactions"][i]:
            for key, value in loaded_yaml["reactions"][i]["orders"].items():
                reactant_orders[gas.species_index(key), i] = value

        if "units" in loaded_yaml:
            if (
                loaded_yaml["units"]["length"] == "cm"
                and loaded_yaml["units"]["quantity"] == "mol"
            ):
                reactions[i]["A"] *= (1e-3) ** (reactant_stoich_coeffs[:, i].sum() - 1)

                if gas.reaction_type(i) in [2]:
                    reactions[i]["A"] *= 1e-3

                if gas.reaction_type(i) in [4]:
                    reactions[i]["A_0"] *= 1e-3
                    reactions[i]["A_0"] *= (1e-3) ** (
                        reactant_stoich_coeffs[:, i].sum() - 1
                    )
                    arrhenius0_coeffs[i, 0] = reactions[i]["A_0"]
                    arrhenius0_coeffs[i, 1] = reactions[i]["b_0"]
                    arrhenius0_coeffs[i, 2] = reactions[i]["Ea_0"]

        arrhenius_coeffs[i, 0] = reactions[i]["A"]
        arrhenius_coeffs[i, 1] = reactions[i]["b"]
        arrhenius_coeffs[i, 2] = reactions[i]["Ea"]
        kinetics_coeffs = KineticsCoeffs(
            arrhenius_coeffs=np.array(arrhenius_coeffs, dtype=np.float64),
            arrhenius0_coeffs=np.array(arrhenius0_coeffs, dtype=np.float64),
            troe_coeffs=np.array(troe_coeffs, dtype=np.float64),
            efficiency_coeffs=np.array(efficiencies_coeffs, dtype=np.float64),
        )
        kinetics_data = KineticsData(
            three_body_indices=np.array(three_body_indices, dtype=np.int64),
            falloff_indices=np.array(falloff_indices, dtype=np.int64),
            troe_falloff_indices=np.array(troe_falloff_indices, dtype=np.int64),
            is_reversible=np.array(is_reversible, dtype=np.int64),
        )
    return kinetics_coeffs, kinetics_data
