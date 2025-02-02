import pytest
import copy
from conftest import get_test_object
from pymatgen.io.validation import ValidationDoc
from emmet.core.tasks import TaskDoc
from emmet.core.vasp.calculation import PotcarSpec
from pymatgen.core.structure import Structure
from pymatgen.io.vasp import Kpoints

### TODO: add tests for many other MP input sets (e.g. MPNSCFSet, MPNMRSet, MPScanRelaxSet, Hybrid sets, etc.)
### TODO: add check for an MP input set that uses an IBRION other than [-1, 1, 2]
### TODO: add in check for MP set where LEFG = True
### TODO: add in check for MP set where LOPTICS = True


@pytest.mark.parametrize(
    "object_name",
    [
        pytest.param("SiOptimizeDouble", id="SiOptimizeDouble"),
    ],
)
def test_validation_doc_from_directory(test_dir, object_name):
    test_object = get_test_object(object_name)
    dir_name = test_dir / "vasp" / test_object.folder
    test_validation_doc = ValidationDoc.from_directory(dir_name=dir_name)

    task_doc = TaskDoc.from_directory(dir_name)
    valid_validation_doc = ValidationDoc.from_task_doc(task_doc)

    # The attributes below will always be different because the objects are created at
    # different times. Hence, ignore before checking.
    delattr(test_validation_doc.builder_meta, "build_date")
    delattr(test_validation_doc, "last_updated")
    delattr(valid_validation_doc.builder_meta, "build_date")
    delattr(valid_validation_doc, "last_updated")

    assert test_validation_doc == valid_validation_doc


@pytest.mark.parametrize(
    "object_name",
    [
        pytest.param("SiOptimizeDouble", id="SiOptimizeDouble"),
    ],
)
def test_potcar_validation(test_dir, object_name):
    test_object = get_test_object(object_name)
    dir_name = test_dir / "vasp" / test_object.folder
    task_doc = TaskDoc.from_directory(dir_name)

    correct_potcar_summary_stats = [
        PotcarSpec(
            titel="PAW_PBE Si 05Jan2001",
            hash="b2b0ea6feb62e7cde209616683b8f7f5",
            summary_stats={
                "keywords": {
                    "header": [
                        "dexc",
                        "eatom",
                        "eaug",
                        "enmax",
                        "enmin",
                        "icore",
                        "iunscr",
                        "lcor",
                        "lexch",
                        "lpaw",
                        "lultra",
                        "ndata",
                        "orbitaldescriptions",
                        "pomass",
                        "qcut",
                        "qgam",
                        "raug",
                        "rcore",
                        "rdep",
                        "rmax",
                        "rpacor",
                        "rrkj",
                        "rwigs",
                        "step",
                        "titel",
                        "vrhfin",
                        "zval",
                    ],
                    "data": [
                        "localpart",
                        "gradientcorrectionsusedforxc",
                        "corecharge-density(partial)",
                        "atomicpseudocharge-density",
                        "nonlocalpart",
                        "reciprocalspacepart",
                        "realspacepart",
                        "reciprocalspacepart",
                        "realspacepart",
                        "nonlocalpart",
                        "reciprocalspacepart",
                        "realspacepart",
                        "reciprocalspacepart",
                        "realspacepart",
                        "pawradialsets",
                        "(5e20.12)",
                        "augmentationcharges(nonsperical)",
                        "uccopanciesinatom",
                        "grid",
                        "aepotential",
                        "corecharge-density",
                        "kineticenergy-density",
                        "pspotential",
                        "corecharge-density(pseudized)",
                        "pseudowavefunction",
                        "aewavefunction",
                        "pseudowavefunction",
                        "aewavefunction",
                        "pseudowavefunction",
                        "aewavefunction",
                        "pseudowavefunction",
                        "aewavefunction",
                        "endofdataset",
                    ],
                },
                "stats": {
                    "header": {
                        "MEAN": 9.177306617073173,
                        "ABSMEAN": 9.246461088617888,
                        "VAR": 1791.1672020733015,
                        "MIN": -4.246,
                        "MAX": 322.069,
                    },
                    "data": {
                        "MEAN": 278.03212972903253,
                        "ABSMEAN": 281.3973189522769,
                        "VAR": 4222525.654282597,
                        "MIN": -92.132623,
                        "MAX": 24929.6618412,
                    },
                },
            },
        )
    ]

    # Check POTCAR (this test should PASS, as we ARE using a MP-compatible pseudopotential)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.potcar_spec = correct_potcar_summary_stats
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["PSEUDOPOTENTIALS" in reason for reason in temp_validation_doc.reasons])

    # Check POTCAR (this test should FAIL, as we are NOT using an MP-compatible pseudopotential)
    temp_task_doc = copy.deepcopy(task_doc)
    incorrect_potcar_summary_stats = copy.deepcopy(correct_potcar_summary_stats)
    incorrect_potcar_summary_stats[0].summary_stats["stats"]["data"]["MEAN"] = 999999999
    temp_task_doc.calcs_reversed[0].input.potcar_spec = incorrect_potcar_summary_stats
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["PSEUDOPOTENTIALS" in reason for reason in temp_validation_doc.reasons])


@pytest.mark.parametrize(
    "object_name",
    [
        pytest.param("SiOptimizeDouble", id="SiOptimizeDouble"),
        pytest.param("SiStatic", id="SiStatic"),
    ],
)
def test_scf_incar_checks(test_dir, object_name):
    test_object = get_test_object(object_name)
    dir_name = test_dir / "vasp" / test_object.folder
    task_doc = TaskDoc.from_directory(dir_name)
    task_doc.calcs_reversed[0].output.structure._charge = 0.0  # patch for old test files

    # LCHIMAG check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LCHIMAG"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LCHIMAG" in reason for reason in temp_validation_doc.reasons])

    # LNMR_SYM_RED check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LNMR_SYM_RED"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LNMR_SYM_RED" in reason for reason in temp_validation_doc.reasons])

    # LDIPOL check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LDIPOL"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LDIPOL" in reason for reason in temp_validation_doc.reasons])

    # IDIPOL check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["IDIPOL"] = 2
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["IDIPOL" in reason for reason in temp_validation_doc.reasons])

    # EPSILON check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["EPSILON"] = 1.5
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["EPSILON" in reason for reason in temp_validation_doc.reasons])

    # EFIELD check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["EFIELD"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["EFIELD" in reason for reason in temp_validation_doc.reasons])

    # ENCUT / ENMAX check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ENMAX"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ENCUT" in reason for reason in temp_validation_doc.reasons])

    # EDIFF check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["EDIFF"] = 1e-2
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["EDIFF" in reason for reason in temp_validation_doc.reasons])

    # IALGO and ENINI checks
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["IALGO"] = 48
    temp_task_doc.input.parameters["ENINI"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ENINI" in reason for reason in temp_validation_doc.reasons])
    assert any(["IALGO" in reason for reason in temp_validation_doc.reasons])

    # NELECT check
    temp_task_doc = copy.deepcopy(task_doc)
    # must set NELECT in `incar` for NELECT checks!
    temp_task_doc.calcs_reversed[0].input.incar["NELECT"] = 9
    temp_task_doc.calcs_reversed[0].output.structure._charge = 1.0
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["NELECT" in reason for reason in temp_validation_doc.reasons])

    # NBANDS too low check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["NBANDS"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["NBANDS" in reason for reason in temp_validation_doc.reasons])

    # NBANDS too high check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["NBANDS"] = 1000
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["NBANDS" in reason for reason in temp_validation_doc.reasons])

    # LREAL check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.incar[
        "LREAL"
    ] = True  # must change `incar` and not `parameters` for LREAL checks!
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LREAL" in reason for reason in temp_validation_doc.reasons])

    # LMAXPAW check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LMAXPAW"] = 0  # should be -100
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LMAXPAW" in reason for reason in temp_validation_doc.reasons])

    # NLSPLINE check for non-NMR calcs
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["NLSPLINE"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["NLSPLINE" in reason for reason in temp_validation_doc.reasons])

    # FFT grid check (NGX, NGY, NGZ, NGXF, NGYF, NGZF)
    # Must change `incar` *and* `parameters` for NG_ checks!
    ng_keys = []
    for direction in ["X", "Y", "Z"]:
        for mod in ["", "F"]:
            ng_keys.append(f"NG{direction}{mod}")

    for key in ng_keys:
        temp_task_doc = copy.deepcopy(task_doc)
        temp_task_doc.calcs_reversed[0].input.incar[key] = 1
        temp_task_doc.input.parameters[key] = 1

        temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
        assert any([key in reason for reason in temp_validation_doc.reasons])

    # ADDGRID check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ADDGRID"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ADDGRID" in reason for reason in temp_validation_doc.reasons])

    # LHFCALC check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LHFCALC"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LHFCALC" in reason for reason in temp_validation_doc.reasons])

    # AEXX check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["AEXX"] = 1.0  # should never be set to this
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["AEXX" in reason for reason in temp_validation_doc.reasons])

    # AGGAC check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["AGGAC"] = 0.5  # should never be set to this
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["AGGAC" in reason for reason in temp_validation_doc.reasons])

    # AGGAX check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["AGGAX"] = 0.5  # should never be set to this
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["AGGAX" in reason for reason in temp_validation_doc.reasons])

    # ALDAX check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ALDAX"] = 0.5  # should never be set to this
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ALDAX" in reason for reason in temp_validation_doc.reasons])

    # AMGGAX check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["AMGGAX"] = 0.5  # should never be set to this
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["AMGGAX" in reason for reason in temp_validation_doc.reasons])

    # ALDAC check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ALDAC"] = 0.5  # should never be set to this
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ALDAC" in reason for reason in temp_validation_doc.reasons])

    # AMGGAC check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["AMGGAC"] = 0.5  # should never be set to this
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["AMGGAC" in reason for reason in temp_validation_doc.reasons])

    # IBRION check
    ### TODO: add check for an MP input set that uses an IBRION other than [-1, 1, 2]
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["IBRION"] = 3
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["IBRION" in reason for reason in temp_validation_doc.reasons])

    # ISIF check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISIF"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ISIF" in reason for reason in temp_validation_doc.reasons])

    # PSTRESS check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["PSTRESS"] = 1.0
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["PSTRESS" in reason for reason in temp_validation_doc.reasons])

    # POTIM check #1 (checks parameter itself)
    ### TODO: add in second check for POTIM that checks for large energy changes between ionic steps
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["POTIM"] = 10
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["POTIM" in reason for reason in temp_validation_doc.reasons])

    # POTIM check #2 (checks energy change between steps)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["IBRION"] = 2
    temp_ionic_step_1 = copy.deepcopy(temp_task_doc.calcs_reversed[0].output.ionic_steps[0])
    temp_ionic_step_2 = copy.deepcopy(temp_ionic_step_1)
    temp_ionic_step_1.e_fr_energy = 0
    temp_ionic_step_2.e_fr_energy = 10000
    temp_task_doc.calcs_reversed[0].output.ionic_steps = [temp_ionic_step_1, temp_ionic_step_2]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["POTIM" in reason for reason in temp_validation_doc.reasons])

    # SCALEE check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["SCALEE"] = 0.9
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["SCALEE" in reason for reason in temp_validation_doc.reasons])

    # EDIFFG energy convergence check (this check should not raise any invalid reasons)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["CONVERGENCE" in reason for reason in temp_validation_doc.reasons])

    # EDIFFG energy convergence check (this check SHOULD error)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_ionic_step_1 = copy.deepcopy(temp_task_doc.calcs_reversed[0].output.ionic_steps[0])
    temp_ionic_step_2 = copy.deepcopy(temp_ionic_step_1)
    temp_ionic_step_1.e_0_energy = -1
    temp_ionic_step_2.e_0_energy = -2
    temp_task_doc.calcs_reversed[0].output.ionic_steps = [temp_ionic_step_1, temp_ionic_step_2]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["CONVERGENCE" in reason for reason in temp_validation_doc.reasons])

    # EDIFFG / force convergence check (the MP input set for R2SCAN has force convergence criteria)
    # (the below test should NOT fail, because final forces are 0)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "R2SCAN"
    temp_task_doc.output.forces = [[0, 0, 0], [0, 0, 0]]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["CONVERGENCE" in reason for reason in temp_validation_doc.reasons])

    # EDIFFG / force convergence check (the MP input set for R2SCAN has force convergence criteria)
    # (the below test SHOULD fail, because final forces are high)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "R2SCAN"
    temp_task_doc.output.forces = [[10, 10, 10], [10, 10, 10]]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["CONVERGENCE" in reason for reason in temp_validation_doc.reasons])

    # ISMEAR wrong for nonmetal check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISMEAR"] = 1
    temp_task_doc.output.bandgap = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ISMEAR" in reason for reason in temp_validation_doc.reasons])

    # ISMEAR wrong for metal relaxation check
    temp_task_doc = copy.deepcopy(task_doc)
    # make ionic_steps be length 2, making this be classified as a relaxation calculation
    temp_task_doc.calcs_reversed[0].output.ionic_steps = 2 * temp_task_doc.calcs_reversed[0].output.ionic_steps
    temp_task_doc.input.parameters["ISMEAR"] = -5
    temp_task_doc.output.bandgap = 0
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ISMEAR" in reason for reason in temp_validation_doc.reasons])

    # SIGMA too high for nonmetal with ISMEAR = 0 check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISMEAR"] = 0
    temp_task_doc.input.parameters["SIGMA"] = 0.2
    temp_task_doc.output.bandgap = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["SIGMA" in reason for reason in temp_validation_doc.reasons])

    # SIGMA too high for nonmetal with ISMEAR = -5 check (should not error)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISMEAR"] = -5
    temp_task_doc.input.parameters["SIGMA"] = 1000  # should not matter
    temp_task_doc.output.bandgap = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["SIGMA" in reason for reason in temp_validation_doc.reasons])

    # SIGMA too high for metal check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISMEAR"] = 1
    temp_task_doc.input.parameters["SIGMA"] = 0.5
    temp_task_doc.output.bandgap = 0
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["SIGMA" in reason for reason in temp_validation_doc.reasons])

    # SIGMA too large check (i.e. eentropy term is > 1 meV/atom)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].output.ionic_steps[0].electronic_steps[-1].eentropy = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["The entropy term (T*S)" in reason for reason in temp_validation_doc.reasons])

    # LMAXMIX check for SCF calc
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LMAXMIX"] = 0
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    # should not invalidate SCF calcs based on LMAXMIX
    assert not any(["LMAXMIX" in reason for reason in temp_validation_doc.reasons])
    # rather should add a warning
    assert any(["LMAXMIX" in warning for warning in temp_validation_doc.warnings])

    # LNONCOLLINEAR check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LNONCOLLINEAR"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LNONCOLLINEAR" in reason for reason in temp_validation_doc.reasons])

    # LSORBIT check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LSORBIT"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LSORBIT" in reason for reason in temp_validation_doc.reasons])

    # LSORBIT check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LSORBIT"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LSORBIT" in reason for reason in temp_validation_doc.reasons])

    # DEPER check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["DEPER"] = 0.5
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["DEPER" in reason for reason in temp_validation_doc.reasons])

    # EBREAK check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["EBREAK"] = 0.1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["EBREAK" in reason for reason in temp_validation_doc.reasons])

    # GGA_COMPAT check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["GGA_COMPAT"] = False
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["GGA_COMPAT" in reason for reason in temp_validation_doc.reasons])

    # ICORELEVEL check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ICORELEVEL"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ICORELEVEL" in reason for reason in temp_validation_doc.reasons])

    # IMAGES check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["IMAGES"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["IMAGES" in reason for reason in temp_validation_doc.reasons])

    # IVDW check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["IVDW"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["IVDW" in reason for reason in temp_validation_doc.reasons])

    # LBERRY check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LBERRY"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LBERRY" in reason for reason in temp_validation_doc.reasons])

    # LCALCEPS check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LCALCEPS"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LCALCEPS" in reason for reason in temp_validation_doc.reasons])

    # LCALCPOL check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LCALCPOL"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LCALCPOL" in reason for reason in temp_validation_doc.reasons])

    # LHYPERFINE check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LHYPERFINE"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LHYPERFINE" in reason for reason in temp_validation_doc.reasons])

    # LKPOINTS_OPT check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LKPOINTS_OPT"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LKPOINTS_OPT" in reason for reason in temp_validation_doc.reasons])

    # LKPROJ check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LKPROJ"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LKPROJ" in reason for reason in temp_validation_doc.reasons])

    # LMP2LT check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LMP2LT"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LMP2LT" in reason for reason in temp_validation_doc.reasons])

    # LOCPROJ check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LOCPROJ"] = "1 : s : Hy"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LOCPROJ" in reason for reason in temp_validation_doc.reasons])

    # LRPA check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LRPA"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LRPA" in reason for reason in temp_validation_doc.reasons])

    # LSMP2LT check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LSMP2LT"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LSMP2LT" in reason for reason in temp_validation_doc.reasons])

    # LSPECTRAL check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LSPECTRAL"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LSPECTRAL" in reason for reason in temp_validation_doc.reasons])

    # LSUBROT check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LSUBROT"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LSUBROT" in reason for reason in temp_validation_doc.reasons])

    # ML_LMLFF check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ML_LMLFF"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ML_LMLFF" in reason for reason in temp_validation_doc.reasons])

    # WEIMIN check too high (invalid)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["WEIMIN"] = 0.01
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["WEIMIN" in reason for reason in temp_validation_doc.reasons])

    # WEIMIN check too low (valid)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["WEIMIN"] = 0.0001
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["WEIMIN" in reason for reason in temp_validation_doc.reasons])

    # EFERMI check (does not matter for VASP versions before 6.4)
    # must check EFERMI in the *incar*, as it is saved as a numerical value after VASP
    # guesses it in the vasprun.xml `parameters`
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].vasp_version = "5.4.4"
    temp_task_doc.calcs_reversed[0].input.incar["EFERMI"] = 5
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["EFERMI" in reason for reason in temp_validation_doc.reasons])

    # EFERMI check (matters for VASP versions 6.4 and beyond)
    # must check EFERMI in the *incar*, as it is saved as a numerical value after VASP
    # guesses it in the vasprun.xml `parameters`
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].vasp_version = "6.4.0"
    temp_task_doc.calcs_reversed[0].input.incar["EFERMI"] = 5
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["EFERMI" in reason for reason in temp_validation_doc.reasons])

    # IWAVPR check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.incar["IWAVPR"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["IWAVPR" in reason for reason in temp_validation_doc.reasons])

    # LASPH check too low (valid)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LASPH"] = False
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LASPH" in reason for reason in temp_validation_doc.reasons])

    # LCORR check (checked when IALGO != 58) (should be invalid in this case)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["IALGO"] = 38
    temp_task_doc.input.parameters["LCORR"] = False
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LCORR" in reason for reason in temp_validation_doc.reasons])

    # LCORR check (checked when IALGO != 58) (should be valid in this case)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["IALGO"] = 58
    temp_task_doc.input.parameters["LCORR"] = False
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["LCORR" in reason for reason in temp_validation_doc.reasons])

    # LORBIT check (should have magnetization values for ISPIN=2)
    # Should be valid for this case, as no magmoms are expected for ISPIN = 1
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISPIN"] = 1
    temp_task_doc.calcs_reversed[0].output.outcar["magnetization"] = []
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["LORBIT" in reason for reason in temp_validation_doc.reasons])

    # LORBIT check (should have magnetization values for ISPIN=2)
    # Should be valid in this case, as magmoms are present for ISPIN = 2
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISPIN"] = 2
    temp_task_doc.calcs_reversed[0].output.outcar["magnetization"] = (
        {"s": -0.0, "p": 0.0, "d": 0.0, "tot": 0.0},
        {"s": -0.0, "p": 0.0, "d": 0.0, "tot": -0.0},
    )
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["LORBIT" in reason for reason in temp_validation_doc.reasons])

    # LORBIT check (should have magnetization values for ISPIN=2)
    # Should be invalid in this case, as no magmoms are present for ISPIN = 2
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISPIN"] = 2
    temp_task_doc.calcs_reversed[0].output.outcar["magnetization"] = []
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LORBIT" in reason for reason in temp_validation_doc.reasons])

    # RWIGS check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["RWIGS"] = [1]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["RWIGS" in reason for reason in temp_validation_doc.reasons])

    # VCA check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["VCA"] = [0.5]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["VCA" in reason for reason in temp_validation_doc.reasons])

    # PREC check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["PREC"] = "NORMAL"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["PREC" in reason for reason in temp_validation_doc.reasons])

    # ROPT check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ROPT"] = [-0.001]
    temp_task_doc.calcs_reversed[0].input.incar["LREAL"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ROPT" in reason for reason in temp_validation_doc.reasons])

    # ICHARG check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ICHARG"] = 11
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ICHARG" in reason for reason in temp_validation_doc.reasons])

    # INIWAV check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["INIWAV"] = 0
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["INIWAV" in reason for reason in temp_validation_doc.reasons])

    # ISTART check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISTART"] = 3
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ISTART" in reason for reason in temp_validation_doc.reasons])

    # ISYM check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISYM"] = 3
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ISYM" in reason for reason in temp_validation_doc.reasons])

    # ISYM check (should not error with ISYM = 3 for hybrid calcs)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISYM"] = 3
    temp_task_doc.input.parameters["LHFCALC"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["ISYM" in reason for reason in temp_validation_doc.reasons])

    # SYMPREC check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["SYMPREC"] = 1e-2
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["SYMPREC" in reason for reason in temp_validation_doc.reasons])

    # LDAUU check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LDAU"] = True
    temp_task_doc.calcs_reversed[0].input.incar["LDAUU"] = [5, 5]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LDAUU" in reason for reason in temp_validation_doc.reasons])

    # LDAUJ check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LDAU"] = True
    temp_task_doc.calcs_reversed[0].input.incar["LDAUJ"] = [5, 5]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LDAUJ" in reason for reason in temp_validation_doc.reasons])

    # LDAUL check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LDAU"] = True
    temp_task_doc.calcs_reversed[0].input.incar["LDAUL"] = [5, 5]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LDAUL" in reason for reason in temp_validation_doc.reasons])

    # LDAUTYPE check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LDAU"] = True
    temp_task_doc.input.parameters["LDAUTYPE"] = [1]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LDAUTYPE" in reason for reason in temp_validation_doc.reasons])

    # NWRITE check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["NWRITE"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["NWRITE" in reason for reason in temp_validation_doc.reasons])

    # LEFG check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LEFG"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LEFG" in reason for reason in temp_validation_doc.reasons])

    # LOPTICS check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LOPTICS"] = True
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LOPTICS" in reason for reason in temp_validation_doc.reasons])

    # LMAXTAU check for METAGGA calcs (A value of 4 should fail for the `La` chemsys (has f electrons))
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.chemsys = "La"
    temp_task_doc.calcs_reversed[0].input.structure = Structure(
        lattice=[[2.9, 0, 0], [0, 2.9, 0], [0, 0, 2.9]], species=["La", "La"], coords=[[0, 0, 0], [0.5, 0.5, 0.5]]
    )
    temp_task_doc.calcs_reversed[0].input.incar["LMAXTAU"] = 4
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "R2SCAN"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LMAXTAU" in reason for reason in temp_validation_doc.reasons])

    # LMAXTAU check for METAGGA calcs (A value of 2 should fail for the `Si` chemsys)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.incar["LMAXTAU"] = 2
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "R2SCAN"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LMAXTAU" in reason for reason in temp_validation_doc.reasons])

    # LMAXTAU should always pass for non-METAGGA calcs
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.incar["LMAXTAU"] = 0
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "None"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["LMAXTAU" in reason for reason in temp_validation_doc.reasons])

    # ENAUG check for r2SCAN calcs
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ENAUG"] = 1
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "R2SCAN"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["ENAUG" in reason for reason in temp_validation_doc.reasons])


@pytest.mark.parametrize(
    "object_name",
    [
        pytest.param("SiNonSCFUniform", id="SiNonSCFUniform"),
    ],
)
def test_nscf_incar_checks(test_dir, object_name):
    test_object = get_test_object(object_name)
    dir_name = test_dir / "vasp" / test_object.folder
    task_doc = TaskDoc.from_directory(dir_name)
    task_doc.calcs_reversed[0].output.structure._charge = 0.0  # patch for old test files

    # ICHARG check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ICHARG"] = 11
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["ICHARG" in reason for reason in temp_validation_doc.reasons])

    # LMAXMIX check for NSCF calc
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["LMAXMIX"] = 0
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    # should invalidate NSCF calcs based on LMAXMIX
    assert any(["LMAXMIX" in reason for reason in temp_validation_doc.reasons])
    # and should *not* create a warning for NSCF calcs
    assert not any(["LMAXMIX" in warning for warning in temp_validation_doc.warnings])


@pytest.mark.parametrize(
    "object_name",
    [
        pytest.param("SiNonSCFUniform", id="SiNonSCFUniform"),
    ],
)
def test_nscf_kpoints_checks(test_dir, object_name):
    test_object = get_test_object(object_name)
    dir_name = test_dir / "vasp" / test_object.folder
    task_doc = TaskDoc.from_directory(dir_name)
    task_doc.calcs_reversed[0].output.structure._charge = 0.0  # patch for old test files

    # Explicit kpoints for NSCF calc check (this should not raise any flags for NSCF calcs)
    temp_task_doc = copy.deepcopy(task_doc)
    _update_kpoints_for_test(
        temp_task_doc,
        {
            "kpoints": [[0, 0, 0], [0, 0, 0.5]],
            "nkpoints": 2,
            "kpts_weights": [0.5, 0.5],
            "labels": ["Gamma", "X"],
            "style": "line_mode",
            "generation_style": "line_mode",
        },
    )
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["INPUT SETTINGS --> KPOINTS: explicitly" in reason for reason in temp_validation_doc.reasons])


@pytest.mark.parametrize(
    "object_name",
    [
        pytest.param("SiOptimizeDouble", id="SiOptimizeDouble"),
        # pytest.param("SiStatic", id="SiStatic"),
    ],
)
def test_common_error_checks(test_dir, object_name):
    test_object = get_test_object(object_name)
    dir_name = test_dir / "vasp" / test_object.folder
    task_doc = TaskDoc.from_directory(dir_name)
    task_doc.calcs_reversed[0].output.structure._charge = 0.0  # patch for old test files

    # METAGGA and GGA tag check (should never be set together)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "R2SCAN"
    temp_task_doc.calcs_reversed[0].input.incar["GGA"] = "PE"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["KNOWN BUG" in reason for reason in temp_validation_doc.reasons])

    # METAGGA and GGA tag check (should not flag any reasons when METAGGA set to None)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "None"
    temp_task_doc.calcs_reversed[0].input.incar["GGA"] = "PE"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["KNOWN BUG" in reason for reason in temp_validation_doc.reasons])

    # No electronic convergence check (i.e. more electronic steps than NELM)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["NELM"] = 1
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["CONVERGENCE --> Did not achieve electronic" in reason for reason in temp_validation_doc.reasons])

    # Drift forces too high check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].output.outcar["drift"] = [[1, 1, 1]]
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["CONVERGENCE --> Excessive drift" in reason for reason in temp_validation_doc.reasons])

    # Final energy too high check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.output.energy_per_atom = 100
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["LARGE POSITIVE FINAL ENERGY" in reason for reason in temp_validation_doc.reasons])

    # Excessive final magmom check (no elements Gd or Eu present)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISPIN"] = 2
    temp_task_doc.calcs_reversed[0].output.outcar["magnetization"] = (
        {"s": 9.0, "p": 0.0, "d": 0.0, "tot": 9.0},
        {"s": 9.0, "p": 0.0, "d": 0.0, "tot": 9.0},
    )
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["MAGNETISM" in reason for reason in temp_validation_doc.reasons])

    # Excessive final magmom check (elements Gd or Eu present)
    # Should pass here, as it has a final magmom < 10
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISPIN"] = 2
    temp_task_doc.calcs_reversed[0].input.structure = Structure(
        lattice=[[2.9, 0, 0], [0, 2.9, 0], [0, 0, 2.9]], species=["Gd", "Eu"], coords=[[0, 0, 0], [0.5, 0.5, 0.5]]
    )
    temp_task_doc.calcs_reversed[0].output.outcar["magnetization"] = (
        {"s": 9.0, "p": 0.0, "d": 0.0, "tot": 9.0},
        {"s": 9.0, "p": 0.0, "d": 0.0, "tot": 9.0},
    )
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["MAGNETISM" in reason for reason in temp_validation_doc.reasons])

    # Excessive final magmom check (elements Gd or Eu present)
    # Should not pass here, as it has a final magmom > 10
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.input.parameters["ISPIN"] = 2
    temp_task_doc.calcs_reversed[0].input.structure = Structure(
        lattice=[[2.9, 0, 0], [0, 2.9, 0], [0, 0, 2.9]], species=["Gd", "Eu"], coords=[[0, 0, 0], [0.5, 0.5, 0.5]]
    )
    temp_task_doc.calcs_reversed[0].output.outcar["magnetization"] = (
        {"s": 11.0, "p": 0.0, "d": 0.0, "tot": 11.0},
        {"s": 11.0, "p": 0.0, "d": 0.0, "tot": 11.0},
    )
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["MAGNETISM" in reason for reason in temp_validation_doc.reasons])

    # Element Po present
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.chemsys = "Po"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["COMPOSITION" in reason for reason in temp_validation_doc.reasons])

    # Elements Am present check
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.chemsys = "Am"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["COMPOSITION" in reason for reason in temp_validation_doc.reasons])


def _update_kpoints_for_test(task_doc: TaskDoc, kpoints_updates: dict):
    if isinstance(task_doc.calcs_reversed[0].input.kpoints, Kpoints):
        kpoints = task_doc.calcs_reversed[0].input.kpoints.as_dict()
    elif isinstance(task_doc.calcs_reversed[0].input.kpoints, dict):
        kpoints = task_doc.calcs_reversed[0].input.kpoints.copy()
    kpoints.update(kpoints_updates)
    task_doc.calcs_reversed[0].input.kpoints = Kpoints.from_dict(kpoints)


@pytest.mark.parametrize(
    "object_name",
    [
        pytest.param("SiOptimizeDouble", id="SiOptimizeDouble"),
    ],
)
def test_kpoints_checks(test_dir, object_name):
    test_object = get_test_object(object_name)
    dir_name = test_dir / "vasp" / test_object.folder
    task_doc = TaskDoc.from_directory(dir_name)
    task_doc.calcs_reversed[0].output.structure._charge = 0.0  # patch for old test files

    # Valid mesh type check (should flag HCP structures)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.structure = Structure(
        lattice=[[0.5, -0.866025403784439, 0], [0.5, 0.866025403784439, 0], [0, 0, 1.6329931618554521]],
        coords=[[0, 0, 0], [0.333333333333333, -0.333333333333333, 0.5]],
        species=["H", "H"],
    )  # HCP structure
    _update_kpoints_for_test(temp_task_doc, {"generation_style": "monkhorst"})
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["INPUT SETTINGS --> KPOINTS or KGAMMA:" in reason for reason in temp_validation_doc.reasons])

    # Valid mesh type check (should flag FCC structures)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.structure = Structure(
        lattice=[[0.0, 0.5, 0.5], [0.5, 0.0, 0.5], [0.5, 0.5, 0.0]], coords=[[0, 0, 0]], species=["H"]
    )  # FCC structure
    _update_kpoints_for_test(temp_task_doc, {"generation_style": "monkhorst"})
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["INPUT SETTINGS --> KPOINTS or KGAMMA:" in reason for reason in temp_validation_doc.reasons])

    # Valid mesh type check (should *not* flag BCC structures)
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].input.structure = Structure(
        lattice=[[2.9, 0, 0], [0, 2.9, 0], [0, 0, 2.9]], species=["H", "H"], coords=[[0, 0, 0], [0.5, 0.5, 0.5]]
    )  # BCC structure
    _update_kpoints_for_test(temp_task_doc, {"generation_style": "monkhorst"})
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert not any(["INPUT SETTINGS --> KPOINTS or KGAMMA:" in reason for reason in temp_validation_doc.reasons])

    # Too few kpoints check
    temp_task_doc = copy.deepcopy(task_doc)
    _update_kpoints_for_test(temp_task_doc, {"kpoints": [[3, 3, 3]]})
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["INPUT SETTINGS --> KPOINTS or KSPACING:" in reason for reason in temp_validation_doc.reasons])

    # Explicit kpoints for SCF calc check
    temp_task_doc = copy.deepcopy(task_doc)
    _update_kpoints_for_test(
        temp_task_doc,
        {
            "kpoints": [[0, 0, 0], [0, 0, 0.5]],
            "nkpoints": 2,
            "kpts_weights": [0.5, 0.5],
            "style": "reciprocal",
            "generation_style": "Reciprocal",
        },
    )
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["INPUT SETTINGS --> KPOINTS: explicitly" in reason for reason in temp_validation_doc.reasons])

    # Shifting kpoints for SCF calc check
    temp_task_doc = copy.deepcopy(task_doc)
    _update_kpoints_for_test(temp_task_doc, {"usershift": [0.5, 0, 0]})
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["INPUT SETTINGS --> KPOINTS: shifting" in reason for reason in temp_validation_doc.reasons])


@pytest.mark.parametrize(
    "object_name",
    [
        pytest.param("SiOptimizeDouble", id="SiOptimizeDouble"),
    ],
)
def test_vasp_version_check(test_dir, object_name):
    test_object = get_test_object(object_name)
    dir_name = test_dir / "vasp" / test_object.folder
    task_doc = TaskDoc.from_directory(dir_name)
    task_doc.calcs_reversed[0].output.structure._charge = 0.0  # patch for old test files

    # Check VASP versions < 5.4.4
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].vasp_version = "5.4.0"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["VASP VERSION" in reason for reason in temp_validation_doc.reasons])

    # Check VASP versions < 5.4
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].vasp_version = "5.0.0"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["VASP VERSION" in reason for reason in temp_validation_doc.reasons])

    # Check VASP versions < 5
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].vasp_version = "4.0.0"
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["VASP VERSION" in reason for reason in temp_validation_doc.reasons])

    # Check for obscure VASP 5 bug with spin-polarized METAGGA calcs
    temp_task_doc = copy.deepcopy(task_doc)
    temp_task_doc.calcs_reversed[0].vasp_version = "5.0.0"
    temp_task_doc.calcs_reversed[0].input.incar["METAGGA"] = "R2SCAN"
    temp_task_doc.input.parameters["ISPIN"] = 2
    temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
    assert any(["POTENTIAL BUG --> We believe" in reason for reason in temp_validation_doc.reasons])


# def test_nscf_incar_checks():
#     test_files_path = Path(__file__).parent.parent.parent.parent.joinpath("test_files").resolve()

#     import json
#     with open(test_files_path / "test_GGA_NSCF_calc.json", 'r') as f:
#         task_doc = json.load(f)

#     # Explicit kpoints for NSCF calc check (this should not raise any flags)
#     temp_task_doc = copy.deepcopy(task_doc)
#     temp_task_doc.calcs_reversed[0].input.kpoints["kpoints"] = [[0,0,0], [0,0,0.5]]
#     temp_validation_doc = ValidationDoc.from_task_doc(temp_task_doc)
#     assert not any(["INPUT SETTINGS --> KPOINTS: explicitly" in reason for reason in temp_validation_doc.reasons])
