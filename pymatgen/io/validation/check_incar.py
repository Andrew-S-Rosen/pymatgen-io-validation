"""Module for validating VASP INCAR files"""
from __future__ import annotations
from importlib.resources import files as import_res_files
from monty.serialization import loadfn
from math import isclose
import numpy as np
from emmet.core.vasp.calc_types.enums import TaskType

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

_vasp_defaults = loadfn(import_res_files("pymatgen.io.validation") / "vasp_defaults.yaml")


def _check_incar(
    reasons,
    warnings,
    valid_input_set,
    structure,
    task_doc,
    calcs_reversed,
    ionic_steps,
    nionic_steps,
    parameters,
    incar,
    potcar,
    vasp_major_version,
    vasp_minor_version,
    vasp_patch_version,
    task_type,
    fft_grid_tolerance,
):
    """
    note that all changes to `reasons` and `warnings` can be done in-place
    (and hence there is no need to return those variables after every function call).
    Any cases where that is not done is just to make the code more readable.
    I didn't think that would be necessary here.
    """

    simple_validator = BaseValidator()
    for key in _vasp_defaults:
        if _vasp_defaults[key].get("operation") in simple_validator.operations:
            reference_value = valid_input_set.incar.get(key, _vasp_defaults[key]["value"])
            if key == "ISTART":
                reference_value = [0, 1, 2]

            simple_validator.check_parameter(
                reasons=reasons,
                parameters=parameters,
                input_tag=key,
                default_value=_vasp_defaults[key]["value"],
                reference_value=reference_value,
                operation=_vasp_defaults[key]["operation"],
                tolerance=_vasp_defaults[key].get("tolerance", None),
                extra_comments_upon_failure=_vasp_defaults[key].get("comment", ""),
            )

    _check_electronic_params(reasons, parameters, incar, valid_input_set, calcs_reversed, structure, potcar)
    _check_electronic_projector_params(reasons, parameters, incar, valid_input_set)
    _check_fft_params(reasons, parameters, incar, valid_input_set, structure, fft_grid_tolerance)
    _check_hybrid_functional_params(reasons, parameters, valid_input_set)
    _check_ionic_params(
        reasons, warnings, parameters, valid_input_set, task_doc, calcs_reversed, nionic_steps, ionic_steps, structure
    )
    _check_ismear_and_sigma(reasons, warnings, parameters, task_doc, ionic_steps, nionic_steps, structure)
    _check_lmaxmix_and_lmaxtau(reasons, warnings, parameters, incar, valid_input_set, structure, task_type)
    _check_misc_params(
        reasons,
        warnings,
        parameters,
        incar,
        valid_input_set,
        calcs_reversed,
        vasp_major_version,
        vasp_minor_version,
        structure,
    )
    _check_precision_params(reasons, parameters, valid_input_set)
    _check_startup_params(reasons, parameters, incar, valid_input_set)
    _check_symmetry_params(reasons, parameters, valid_input_set)
    _check_u_params(reasons, incar, parameters, valid_input_set)

    return reasons


def _get_default_nbands(structure, parameters, nelect):
    """
    This method is copied from the `estimate_nbands` function in pymatgen.io.vasp.sets.py.
    The only noteworthy changes (should) be that there is no reliance on the user setting
    up the psp_resources for pymatgen.
    """
    nions = len(structure.sites)

    if parameters.get("ISPIN", "1") == 1:
        nmag = 0
    else:
        nmag = sum(parameters.get("MAGMOM", [0]))
        nmag = np.floor((nmag + 1) / 2)

    possible_val_1 = np.floor((nelect + 2) / 2) + max(np.floor(nions / 2), 3)
    possible_val_2 = np.floor(nelect * 0.6)

    default_nbands = max(possible_val_1, possible_val_2) + nmag

    if "LNONCOLLINEAR" in parameters.keys():
        if parameters["LNONCOLLINEAR"]:
            default_nbands = default_nbands * 2

    if "NPAR" in parameters.keys():
        npar = parameters["NPAR"]
        default_nbands = (np.floor((default_nbands + npar - 1) / npar)) * npar

    return int(default_nbands)


# def _get_default_nelect(structure, valid_input_set, potcar=None):
#     # for parsing raw calculation files or for users without the VASP pseudopotentials set up in the pymatgen `psp_resources` directory
#     if potcar is not None:
#         zval_dict = {
#             p.symbol.split("_")[0]: p.zval for p in potcar
#         }  # num of electrons each species should have according to the POTCAR
#         # change something like "Fe_pv" to just "Fe" for easier matching of species
#         default_nelect = 0
#         for site in structure.sites:
#             default_nelect += zval_dict[site.species_string]
#     # else try using functions that require the `psp_resources` directory to be set up for pymatgen.
#     else:
#         default_nelect = valid_input_set.nelect

#     return int(default_nelect)


def _get_valid_ismears_and_sigma(parameters, bandgap, nionic_steps):
    extra_comments_for_ismear_and_sigma = (
        f"This is flagged as incorrect because this calculation had a bandgap of {round(bandgap,3)}"
    )

    if (
        bandgap > 1e-4
    ):  # value taken from https://github.com/materialsproject/pymatgen/blob/1f98fa21258837ac174105e00e7ac8563e119ef0/pymatgen/io/vasp/sets.py#L969
        valid_ismears = [-5, 0]
        valid_sigma = 0.05
    else:
        valid_ismears = [0, 1, 2]
        cur_nsw = parameters.get("NSW", 0)
        if cur_nsw == 0:
            valid_ismears.append(-5)  # ISMEAR = -5 is valid for metals *only* when doing static calc
            extra_comments_for_ismear_and_sigma += " and is a static calculation"
        else:
            extra_comments_for_ismear_and_sigma += " and is a non-static calculation"
        valid_sigma = 0.2
    extra_comments_for_ismear_and_sigma += "."

    return valid_ismears, valid_sigma, extra_comments_for_ismear_and_sigma


def _check_electronic_params(reasons, parameters, incar, valid_input_set, calcs_reversed, structure, potcar=None):
    simple_validator = BaseValidator()
    # ENCUT. Should be the same or greater than in valid_input_set, as this can affect energies & other results.
    # *** Note: "ENCUT" is not actually detected by the `Vasprun.parameters` object from pymatgen.io.vasp.outputs.
    #           Rather, the ENMAX tag in the `Vasprun.parameters` object contains the relevant value for ENCUT.
    valid_encut = valid_input_set.incar.get("ENCUT", np.inf)
    simple_validator.check_parameter(reasons, parameters, "ENMAX", 0, valid_encut, "<=")

    # ENINI. Only check for IALGO = 48 / ALGO = VeryFast, as this is the only algo that uses this tag.
    if parameters.get("IALGO", 38) == 48:
        simple_validator.check_parameter(reasons, parameters, "ENINI", 0, valid_encut, "<=")

    # ENAUG. Should only be checked for calculations where the relevant MP input set specifies ENAUG.
    # In that case, ENAUG should be the same or greater than in valid_input_set.
    if "ENAUG" in valid_input_set.incar.keys():
        parameters.get("ENAUG", 0)
        valid_enaug = valid_input_set.incar.get("ENAUG", np.inf)
        simple_validator.check_parameter(reasons, parameters, "ENAUG", 0, valid_enaug, "<=")

    # IALGO.
    valid_ialgos = [38, 58, 68, 90]
    # TODO: figure out if 'normal' algos every really affect results other than convergence
    simple_validator.check_parameter(reasons, parameters, "IALGO", 38, valid_ialgos, "in")

    # NELECT.
    cur_nelect = parameters.get("NELECT")
    if "NELECT" in incar.keys():  # Do not check for non-neutral NELECT if NELECT is not in the INCAR
        valid_charge = 0.0
        cur_charge = calcs_reversed[0]["output"]["structure"]._charge
        try:
            if not np.isclose(valid_charge, cur_charge):
                reasons.append(
                    f"INPUT SETTINGS --> NELECT: set to {cur_nelect}, but this causes the structure to have a charge of {cur_charge}. "
                    f"NELECT should be set to {cur_nelect + cur_charge} instead."
                )
        except Exception:
            reasons.append(
                "INPUT SETTINGS --> NELECT / POTCAR: issue checking whether NELECT was changed to make the structure have a non-zero charge. "
                "This is likely due to the directory not having a POTCAR file."
            )
    # default_nelect = _get_default_nelect(structure, valid_input_set, potcar=potcar)
    # _check_required_params(reasons, parameters, "NELECT", default_nelect, default_nelect)

    # NBANDS.
    min_nbands = int(np.ceil(cur_nelect / 2) + 1)
    default_nbands = _get_default_nbands(structure, parameters, cur_nelect)
    # check for too many bands (can lead to unphysical electronic structures, see https://github.com/materialsproject/custodian/issues/224 for more context
    simple_validator.check_parameter(
        reasons,
        parameters,
        "NBANDS",
        default_nbands,
        4 * default_nbands,
        ">=",
        extra_comments_upon_failure=(
            "Too many bands can lead to unphysical electronic structure "
            "(see https://github.com/materialsproject/custodian/issues/224 "
            "for more context.)"
        ),
    )
    # check for too few bands (leads to degenerate energies)
    simple_validator.check_parameter(reasons, parameters, "NBANDS", default_nbands, min_nbands, "<=")


def _check_electronic_projector_params(reasons, parameters, incar, valid_input_set):
    # LREAL.
    # Do NOT use the value for LREAL from the `Vasprun.parameters` object, as VASP changes these values
    # relative to the INCAR. Rather, check the LREAL value in the `Vasprun.incar` object.
    if str(valid_input_set.incar.get("LREAL")).upper() in ["AUTO", "A"]:
        valid_lreals = ["FALSE", "AUTO", "A"]
    elif str(valid_input_set.incar.get("LREAL")).upper() in ["FALSE"]:
        valid_lreals = ["FALSE"]

    cur_lreal = str(incar.get("LREAL", "False")).upper()
    if cur_lreal not in valid_lreals:
        reasons.append(f"INPUT SETTINGS --> LREAL: is set to {cur_lreal}, but should be one of {valid_lreals}.")

    # # # LREAL. As per VASP warnings, LREAL should only be `False` for smaller structures.
    # # # Do NOT use the value for LREAL from the `Vasprun.parameters` object, as VASP changes these values automatically.
    # # # Rather, check the LREAL value in the `Vasprun.incar` object.
    # # # For larger structures, LREAL can be `False` or `Auto`
    # # if len(structure) < 16:
    # #     valid_lreals = ["FALSE"]
    # # if len(structure) >= 16:
    # #     valid_lreals = ["FALSE", "AUTO", "A"]
    # # # VASP actually changes the value of LREAL the second time it is printed to vasprun.xml. Hence, we check the INCAR instead.
    # # cur_lreal = str(incar.get("LREAL", "False")).upper()
    # # if cur_lreal not in valid_lreals:
    # #     reasons.append(f"INPUT SETTINGS --> LREAL: is set to {cur_lreal}, but should be one of {valid_lreals}.")


def _check_fft_params(
    reasons,
    parameters,
    incar,
    valid_input_set,
    structure,
    fft_grid_tolerance,
):
    simple_validator = BaseValidator()
    # NGX/Y/Z and NGXF/YF/ZF. Not checked if not in INCAR file (as this means the VASP default was used).
    if any(i for i in ["NGX", "NGY", "NGZ", "NGXF", "NGYF", "NGZF"] if i in incar.keys()):
        parameters.get("PREC", "NORMAL").upper()
        cur_encut = parameters.get("ENMAX", np.inf)
        parameters.get("ENAUG", np.inf)

        valid_encut_for_fft_grid_params = max(cur_encut, valid_input_set.incar.get("ENCUT"))
        valid_ng = {}
        (
            [valid_ng["X"], valid_ng["Y"], valid_ng["Z"]],
            [valid_ng["XF"], valid_ng["YF"], valid_ng["ZF"]],
        ) = valid_input_set.calculate_ng(custom_encut=valid_encut_for_fft_grid_params)
        for direction in ["X", "Y", "Z"]:
            for mod in ["", "F"]:
                valid_ng[direction + mod] = int(valid_ng[direction + mod] * fft_grid_tolerance)

        extra_comments_for_FFT_grid = (
            "This likely means the number FFT grid points was modified by the user. "
            "If not, please create a GitHub issue."
        )

        for direction in ["X", "Y", "Z"]:
            for mod in ["", "F"]:
                simple_validator.check_parameter(
                    reasons=reasons,
                    parameters=parameters,
                    input_tag=f"NG{(direction + mod).upper()}",
                    default_value=np.inf,
                    reference_value=valid_ng[direction + mod],
                    operation="<=",
                    extra_comments_upon_failure=extra_comments_for_FFT_grid,
                )


def _check_hybrid_functional_params(reasons, parameters, valid_input_set):
    valid_lhfcalc = valid_input_set.incar.get("LHFCALC", False)

    default_values = {
        key: _vasp_defaults[key]["value"] for key in _vasp_defaults if _vasp_defaults[key]["tag"] == "hybrid"
    }

    if valid_lhfcalc:
        default_values["AEXX"] = 0.25
        default_values["AGGAC"] = 0.0
        for key in ("AGGAX", "ALDAX", "AMGGAX"):
            default_values[key] = 1.0 - parameters.get("AEXX", default_values["AEXX"])

        if parameters.get("AEXX", default_values["AEXX"]) == 1.0:
            default_values["ALDAC"] = 0.0
            default_values["AMGGAC"] = 0.0

    simple_validator = BaseValidator()
    for key in _vasp_defaults:
        if _vasp_defaults[key]["tag"] != "hybrid":
            continue
        simple_validator.check_parameter(
            reasons=reasons,
            parameters=parameters,
            input_tag=key,
            default_value=default_values[key],
            reference_value=valid_input_set.incar.get(key, default_values[key]),
            operation="approx" if isinstance(default_values[key], float) else "==",
            tolerance=_vasp_defaults[key].get("tolerance"),
        )


def _check_ionic_params(
    reasons, warnings, parameters, valid_input_set, task_doc, calcs_reversed, nionic_steps, ionic_steps, structure
):
    simple_validator = BaseValidator()
    # IBRION.
    default_ibrion = 0
    valid_ibrions = [-1, 1, 2]
    input_set_ibrion = valid_input_set.incar.get("IBRION", default_ibrion)

    simple_validator.check_parameter(
        reasons=reasons,
        parameters=parameters,
        input_tag="IBRION",
        default_value=default_ibrion,
        reference_value=valid_ibrions if input_set_ibrion in valid_ibrions else [input_set_ibrion],
        operation="in",
    )

    # POTIM.
    if parameters.get("IBRION", 0) in [1, 2, 3, 5, 6]:  # POTIM is only used for some IBRION values
        valid_max_potim = 5
        simple_validator.check_parameter(
            reasons=reasons,
            parameters=parameters,
            input_tag="POTIM",
            default_value=0.5,
            reference_value=valid_max_potim,
            operation=">=",
            extra_comments_upon_failure="POTIM being so high will likely lead to erroneous results.",
        )
        # Check for large changes in energy between ionic steps (usually indicates too high POTIM)
        if nionic_steps > 1:
            # Do not use `e_0_energy`, as there is a bug in the vasprun.xml when printing that variable
            # (see https://www.vasp.at/forum/viewtopic.php?t=16942 for more details).
            cur_ionic_step_energies = [ionic_step["e_fr_energy"] for ionic_step in ionic_steps]
            cur_ionic_step_energy_gradient = np.diff(cur_ionic_step_energies)
            cur_max_ionic_step_energy_change_per_atom = (
                max(np.abs(cur_ionic_step_energy_gradient)) / structure.num_sites
            )
            valid_max_energy_change_per_atom = 1
            if cur_max_ionic_step_energy_change_per_atom > valid_max_energy_change_per_atom:
                reasons.append(
                    f"INPUT SETTINGS --> POTIM: The energy changed by a maximum of {cur_max_ionic_step_energy_change_per_atom} eV/atom "
                    f"between ionic steps, which is greater than the maximum allowed of {valid_max_energy_change_per_atom} eV/atom. "
                    f"This indicates that the POTIM is too high."
                )

    # EDIFFG.
    # Should be the same or smaller than in valid_input_set. Force-based cutoffs (not in every
    # every MP-compliant input set, but often have comparable or even better results) will also be accepted
    # I am **NOT** confident that this should be the final check. Perhaps I need convincing (or perhaps it does indeed need to be changed...)
    # TODO:    -somehow identify if a material is a vdW structure, in which case force-convergence should maybe be more strict?
    valid_ediff = valid_input_set.incar.get("EDIFF", 1e-4)
    ediffg_in_input_set = valid_input_set.incar.get("EDIFFG", 10 * valid_ediff)

    if ediffg_in_input_set > 0:
        valid_ediffg_energy = ediffg_in_input_set
        valid_ediffg_force = -0.05
    elif ediffg_in_input_set < 0:
        valid_ediffg_energy = 10 * valid_ediff
        valid_ediffg_force = ediffg_in_input_set

    if task_doc.output.forces is None:
        is_force_converged = False
        warnings.append("TaskDoc does not contain output forces!")
    else:
        is_force_converged = all(
            (np.linalg.norm(force_on_atom) <= abs(valid_ediffg_force)) for force_on_atom in task_doc.output.forces
        )

    if parameters.get("NSW", 0) == 0 or nionic_steps <= 1:
        # TODO? why was this highlighted with hashes?
        is_converged = is_force_converged
    else:
        energy_of_last_step = calcs_reversed[0]["output"]["ionic_steps"][-1]["e_0_energy"]
        energy_of_second_to_last_step = calcs_reversed[0]["output"]["ionic_steps"][-2]["e_0_energy"]
        is_energy_converged = abs(energy_of_last_step - energy_of_second_to_last_step) <= valid_ediffg_energy
        is_converged = any([is_energy_converged, is_force_converged])

    if not is_converged:
        reasons.append("CONVERGENCE --> Structure is not converged according to the EDIFFG.")


def _check_ismear_and_sigma(reasons, warnings, parameters, task_doc, ionic_steps, nionic_steps, structure):
    bandgap = task_doc.output.bandgap

    simple_validator = BaseValidator()

    valid_ismears, valid_sigma, extra_comments_for_ismear_and_sigma = _get_valid_ismears_and_sigma(
        parameters, bandgap, nionic_steps
    )

    # ISMEAR.
    simple_validator.check_parameter(
        reasons,
        parameters,
        "ISMEAR",
        1,
        valid_ismears,
        "in",
        extra_comments_upon_failure=extra_comments_for_ismear_and_sigma,
    )

    # SIGMA.
    # TODO: improve logic for SIGMA reasons given in the case where you have a material that should have been relaxed with ISMEAR in [-5, 0], but used ISMEAR in [1,2].
    # Because in such cases, the user wouldn't need to update the SIGMA if they use tetrahedron smearing.
    cur_ismear = parameters.get("ISMEAR", 1)
    if cur_ismear not in [-5, -4, -2]:  # SIGMA is not used by the tetrahedron method.
        simple_validator.check_parameter(
            reasons,
            parameters,
            "SIGMA",
            0.2,
            valid_sigma,
            ">=",
            extra_comments_upon_failure=extra_comments_for_ismear_and_sigma,
        )
    else:
        warnings.append(
            f"SIGMA is not being directly checked, as an ISMEAR of {cur_ismear} is being used. However, given the bandgap of {round(bandgap,3)}, the maximum SIGMA used should be {valid_sigma} if using an ISMEAR *not* in [-5, -4, -2]."
        )

    # Also check if SIGMA is too large according to the VASP wiki,
    # which occurs when the entropy term in the energy is greater than 1 meV/atom.
    all_eentropies_per_atom = []
    for ionic_step in ionic_steps:
        electronic_steps = ionic_step["electronic_steps"]
        # print(electronic_steps)
        for elec_step in electronic_steps:
            if "eentropy" in elec_step.keys():
                if elec_step["eentropy"] is not None:
                    all_eentropies_per_atom.append(elec_step["eentropy"] / structure.num_sites)

    cur_max_eentropy_per_atom = max(abs(np.array(all_eentropies_per_atom)))
    valid_max_eentropy_per_atom = 0.001

    if cur_max_eentropy_per_atom > valid_max_eentropy_per_atom:
        reasons.append(
            f"INPUT SETTINGS --> SIGMA: The entropy term (T*S) in the energy was {round(1000 * cur_max_eentropy_per_atom, 3)} meV/atom, which is "
            f"greater than the {round(1000 * valid_max_eentropy_per_atom, 1)} meV/atom maximum suggested in the VASP wiki. "
            f"Thus, SIGMA should be decreased."
        )


def _check_lmaxmix_and_lmaxtau(reasons, warnings, parameters, incar, valid_input_set, structure, task_type):
    """
    Check that LMAXMIX and LMAXTAU are above the required value. Also ensure that they are not greater than 6,
    as that is inadvisable according to the VASP development team (as of writing this in August 2023).
    """

    valid_lmaxmix = valid_input_set.incar.get("LMAXMIX", 2)
    valid_lmaxtau = min(valid_lmaxmix + 2, 6)
    lmaxmix_or_lmaxtau_too_high_msg = (
        "From empirical testing, using LMAXMIX and / or LMAXTAU > 6 appears to introduce computational instabilities, "
        "and is currently inadvisable according to the VASP development team."
    )

    # LMAXMIX.
    cur_lmaxmix = parameters.get("LMAXMIX", 2)
    if (cur_lmaxmix < valid_lmaxmix) or (cur_lmaxmix > 6):
        if valid_lmaxmix < 6:
            lmaxmix_msg = f"INPUT SETTINGS --> LMAXMIX: value is set to {cur_lmaxmix}, but should be between {valid_lmaxmix} and 6."
        else:
            lmaxmix_msg = f"INPUT SETTINGS --> LMAXMIX: value is set to {cur_lmaxmix}, but should be {valid_lmaxmix}."
        # add additional context for invalidation if user set LMAXMIX > 6
        if cur_lmaxmix > 6:
            lmaxmix_msg += lmaxmix_or_lmaxtau_too_high_msg

        # Either add to reasons or warnings depending on task type (as this affects NSCF calcs the most)
        # @ Andrew Rosen, is this an adequate check? Or should we somehow also be checking for cases where
        # a previous SCF calc used the wrong LMAXMIX too?
        if task_type == TaskType.NSCF_Uniform or task_type == TaskType.NSCF_Line or parameters.get("ICHARG", 2) >= 10:
            reasons.append(lmaxmix_msg)
        else:
            warnings.append(lmaxmix_msg)

    # LMAXTAU. Only check for METAGGA calculations
    if incar.get("METAGGA", None) not in ["--", None, "None"]:
        # cannot check LMAXTAU in the `Vasprun.parameters` object, as LMAXTAU is not printed to the parameters. Rather, we must check the INCAR.
        cur_lmaxtau = incar.get("LMAXTAU", 6)

        if (cur_lmaxtau < valid_lmaxtau) or (cur_lmaxtau > 6):
            if valid_lmaxtau < 6:
                lmaxtau_msg = f"INPUT SETTINGS --> LMAXTAU: value is set to {cur_lmaxtau}, but should be between {valid_lmaxtau} and 6."
            else:
                lmaxtau_msg = (
                    f"INPUT SETTINGS --> LMAXTAU: value is set to {cur_lmaxtau}, but should be {valid_lmaxtau}."
                )
            # add additional context for invalidation if user set LMAXTAU > 6
            if cur_lmaxtau > 6:
                lmaxtau_msg += lmaxmix_or_lmaxtau_too_high_msg

            reasons.append(lmaxtau_msg)


def _check_misc_params(
    reasons,
    warnings,
    parameters,
    incar,
    valid_input_set,
    calcs_reversed,
    vasp_major_version,
    vasp_minor_version,
    structure,
):
    """
    EFERMI. Only available for VASP >= 6.4. Should not be set to a numerical
    value, as this may change the number of electrons.
    """
    if (vasp_major_version >= 6) and (vasp_minor_version >= 4):
        """
        Must check EFERMI in the *incar*, as it is saved as a numerical
        value after VASP guesses it in the vasprun.xml `parameters`
        (which would always cause this check to fail, even if the user
        set EFERMI properly in the INCAR).
        """
        cur_efermi = incar.get("EFERMI", "LEGACY")
        allowed_efermis = ["LEGACY", "MIDGAP"]
        if cur_efermi not in allowed_efermis:
            reasons.append(f"INPUT SETTINGS --> EFERMI: should be one of {allowed_efermis}.")

    # IWAVPR.
    if "IWAVPR" in incar.keys():
        reasons.append("INPUT SETTINGS --> VASP discourages users from setting " "the IWAVPR tag (as of July 2023).")

    # LCORR.
    cur_ialgo = parameters.get("IALGO", 38)
    if cur_ialgo != 58:
        BaseValidator().check_parameter(reasons, parameters, "LCORR", True, True, "==")

    # LORBIT.
    cur_ispin = parameters.get("ISPIN", 1)
    # cur_lorbit = incar.get("LORBIT") if "LORBIT" in incar.keys() else parameters.get("LORBIT", None)
    if (cur_ispin == 2) and (len(calcs_reversed[0]["output"]["outcar"]["magnetization"]) != structure.num_sites):
        reasons.append(
            "INPUT SETTINGS --> LORBIT: magnetization values were not written "
            "to the OUTCAR. This is usually due to LORBIT being set to None or "
            "False for calculations with ISPIN=2."
        )

    if parameters.get("LORBIT", -np.inf) >= 11 and parameters.get("ISYM", 2) and (vasp_major_version < 6):
        warnings.append(
            "For LORBIT >= 11 and ISYM = 2 the partial charge densities are not correctly symmetrized and can result "
            "in different charges for symmetrically equivalent partial charge densities. This issue is fixed as of version "
            ">=6. See the vasp wiki page for LORBIT for more details."
        )

    # RWIGS.
    if any(
        x != -1.0 for x in parameters.get("RWIGS", [-1])
    ):  # do not allow RWIGS to be changed, as this affects outputs like the magmom on each atom
        reasons.append(
            "INPUT SETTINGS --> RWIGS: should not be set. This is because it will change some outputs like the magmom on each site."
        )

    # VCA.
    if any(x != 1.0 for x in parameters.get("VCA", [1])):  # do not allow VCA calculations
        reasons.append("INPUT SETTINGS --> VCA: should not be set")


def _check_precision_params(reasons, parameters, valid_input_set):
    # PREC.
    default_prec = "NORMAL"
    if valid_input_set.incar.get("PREC", default_prec).upper() in ["ACCURATE", "HIGH"]:
        valid_precs = ["ACCURATE", "ACCURA", "HIGH"]
    else:
        raise ValueError("Validation code check for PREC tag needs to be updated to account for a new input set!")
    BaseValidator().check_parameter(reasons, parameters, "PREC", default_prec, valid_precs, "in")

    # ROPT. Should be better than or equal to default for the PREC level. This only matters if projectors are done in real-space.
    # Note that if the user sets LREAL = Auto in their Incar, it will show up as "True" in the `parameters` object (hence we use the `parameters` object)
    if (
        str(parameters.get("LREAL", "FALSE")).upper() == "TRUE"
    ):  # this only matters if projectors are done in real-space.
        cur_prec = parameters.get("PREC", "Normal").upper()
        if cur_prec == "NORMAL":
            default_ropt = -5e-4
        elif cur_prec in ["ACCURATE", "ACCURA"]:
            default_ropt = -2.5e-4
        elif cur_prec == "LOW":
            default_ropt = -0.01
        elif cur_prec == "MED":
            default_ropt = -0.002
        elif cur_prec == "HIGH":
            default_ropt = -4e-4

        cur_ropt = parameters.get("ROPT", [default_ropt])
        if True in (x < default_ropt for x in cur_ropt):
            reasons.append(
                f"INPUT SETTINGS --> ROPT: value is set to {cur_ropt}, but should be {default_ropt} or stricter."
            )


def _check_startup_params(reasons, parameters, incar, valid_input_set):
    # ICHARG.
    if valid_input_set.incar.get("ICHARG", _vasp_defaults["ICHARG"]["value"]) < 10:
        valid_icharg = 9  # should be <10 (SCF calcs)
        operation = ">="
    else:
        valid_icharg = valid_input_set.incar.get("ICHARG")
        operation = "=="

    BaseValidator().check_parameter(
        reasons=reasons,
        parameters=parameters,
        input_tag="ICHARG",
        default_value=_vasp_defaults["ICHARG"]["value"],
        reference_value=valid_icharg,
        operation=operation,
    )


def _check_symmetry_params(reasons, parameters, valid_input_set):
    simple_validator = BaseValidator()

    # ISYM.
    default_isym = 3 if parameters.get("LHFCALC", False) else 2
    # allow ISYM as good or better than what is specified in the valid_input_set.
    if "ISYM" in valid_input_set.incar.keys():
        if valid_input_set.incar.get("ISYM") == 3:
            valid_isyms = [-1, 0, 2, 3]
        elif valid_input_set.incar.get("ISYM") == 2:
            valid_isyms = [-1, 0, 2]
        elif valid_input_set.incar.get("ISYM") == 0:
            valid_isyms = [-1, 0]
        elif valid_input_set.incar.get("ISYM") == -1:
            valid_isyms = [-1]
    else:  # otherwise let ISYM = -1, 0, or 2
        valid_isyms = [-1, 0, 2]

    simple_validator.check_parameter(
        reasons=reasons,
        parameters=parameters,
        input_tag="ISYM",
        default_value=default_isym,
        reference_value=valid_isyms,
        operation="in",
    )

    # SYMPREC.
    default_symprec = 1e-5
    valid_symprec = 1e-3  # custodian will set SYMPREC to a maximum of 1e-3 (as of August 2023)
    simple_validator.check_parameter(
        reasons=reasons,
        parameters=parameters,
        input_tag="SYMPREC",
        default_value=default_symprec,
        reference_value=valid_symprec,
        operation=">=",
        extra_comments_upon_failure=(
            "If you believe that this SYMPREC value is necessary "
            "(perhaps this calculation has a very large cell), please create "
            "a GitHub issue and we will consider to admit your calculations."
        ),
    )


def _check_u_params(reasons, incar, parameters, valid_input_set):
    if parameters.get("LDAU", _vasp_defaults["LDAU"]["value"]):
        for key in _vasp_defaults:
            if _vasp_defaults[key]["tag"] != "dft+u":
                continue

            valid_val = valid_input_set.incar.get(key, _vasp_defaults[key]["value"])

            # TODO: ADK: is LDAUTYPE usually specified as a list??
            if key == "LDAUTYPE":
                cur_val = parameters.get(key, _vasp_defaults[key]["value"])
                cur_val = cur_val[0] if isinstance(cur_val, list) else cur_val
                valid_val = valid_val[0] if isinstance(valid_val, list) else valid_val
            else:
                cur_val = incar.get(key, _vasp_defaults[key]["value"])

            if cur_val != valid_val:
                reasons.append(f"INPUT SETTINGS --> {key}: set to {cur_val}, but should be set to {valid_val}.")


class BaseValidator:
    """Lightweight validator class to handle majority of parameter checking."""

    input_tag_translation = {"ENMAX": "ENCUT"}

    operations = {
        "==": "__eq__",
        ">": "__gt__",
        ">=": "__ge__",
        "<": "__lt__",
        "<=": "__le__",
        "in": "__contains__",
        "approx": "__eq__",
    }

    def __init__(self):
        """Dummy init."""
        return

    def check_parameter(
        self,
        reasons: list[str],
        parameters: dict,
        input_tag: str,
        default_value: Any,
        reference_value: Any,
        operation: str,
        tolerance: float = None,
        extra_comments_upon_failure: str = "",
    ):
        """Determine validity of parameter subject to specified operation."""

        # Allow for printing different tag than the one used to access values
        # For example, the user sets ENCUT via INCAR, but the value of ENCUT is stored
        # by VASP as ENMAX

        current_value = parameters.get(input_tag, default_value)

        if operation == "approx" and isinstance(current_value, float):
            tolerance = tolerance or 1.0e-4
            valid_value = isclose(current_value, reference_value, rel_tol=tolerance, abs_tol=0.0)
        else:
            if operation == "approx" and not isinstance(current_value, float):
                print(current_value, input_tag)
            valid_value = reference_value.__getattribute__(self.operations[operation])(current_value)

        if not valid_value:
            msg = (
                "INPUT SETTINGS --> "
                f"{self.input_tag_translation.get(input_tag,input_tag)}: "
                f"set to {current_value}, but should be {operation} "
                f"{reference_value}. {extra_comments_upon_failure}"
            )
            reasons.append(msg)
