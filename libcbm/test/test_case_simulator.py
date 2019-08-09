# Class for running LibCBM test cases as generated by
# libcbm.test.casegeneration.  This is used for side-by-side
# comparison of simulations which can be run on the same test case format in
# CBM-CFS3 using libcbm.test.cbm3support.cbm3_simulator

import numpy as np
import pandas as pd

from libcbm.model import cbm_factory
from libcbm.model import cbm_variables
from libcbm.model import model_factory
from libcbm.configuration import cbmconfig
from libcbm.configuration.cbm_defaults_reference import CBMDefaultsReference
from libcbm.test import case_generation


def get_test_case_classifier_factory(cases, classifier_name):
    """Create a function for translating test cases into LibCBM classifiers
    configuration

    Args:
        cases (list): a list of dictionary objects specifying test cases
        classifier_name (str): the single classifier name used by the test
            case simulator

    Returns:
        func: a function that will return classifier configuration
    """
    def create_classifiers():
        """translates test cases into LibCBM classifier configuration

        Returns:
            dict: classifier configuration
        """
        classifiers_config = cbmconfig.classifier_config([
            cbmconfig.classifier(classifier_name, [
                cbmconfig.classifier_value(
                    case_generation.get_classifier_value_name(c["id"]))
                for c in cases
                ])
            ])
        return classifiers_config
    return create_classifiers


def get_test_case_merch_volume_factory(cases, db_path, cbm_defaults_ref):
    """Creates a factory function for transforming test case data into
        merchantable volume configuration input for libcbm.

    Args:
        cases (list): a list of dictionary objects specifying test cases
        db_path (str): path to a cbm_defaults database (which contains
            merchantable volume to biomass conversion parameters)
        cbm_defaults_ref (CBMDefaultsReference): class used to convert
            species names into species ids for libcbm consumption

    Returns:
        func: a factory function which produces libcbm merch volume config
    """
    def create_merch_volume_config():
        """translates test case data into merchantable volume
           configuration input for libcbm.

        Returns:
            dict: merch volume config
        """
        curves = []
        for c in cases:
            classifier_set = [
                case_generation.get_classifier_value_name(c["id"])]
            merch_volumes = []
            for component in c["components"]:
                merch_volumes.append({
                    "species_id": cbm_defaults_ref.get_species_id(
                        component["species"]),
                    "age_volume_pairs": component["age_volume_pairs"]
                })

            curve = cbmconfig.merch_volume_curve(
                classifier_set=classifier_set,
                merch_volumes=merch_volumes)
            curves.append(curve)

        merch_volume_to_biomass_config = \
            cbmconfig.merch_volume_to_biomass_config(db_path, curves)
        return merch_volume_to_biomass_config

    return create_merch_volume_config


def get_disturbances(cases, ref):
    """Transform test cases into dictionary storage for disturbance events

    Returns a dictionary of the form::

        {
            case_index_0:
            {
                time_step: disturbance_type_id,
            },
            ...
            case_index_k:
            {
                time_step: disturbance_type_id,
            }
        }

    Cases that do not have disturbance events will be omitted from the
    result, and any case that specifies more than one event on a single
    timestep will result in a ValueError

    Args:
        cases (list): a list of dictionary objects specifying test cases
        ref (CBMDefaultsReference): class used to convert a disturbance name
            string into a disturbance type id

    Raises:
        ValueError: raised if more than one event is detected for a single
            case on a given timestep

    Returns:
        dict: a nested dictionary of disturbance type ids by time step.
            For example the result for case id 5 having disturbance type 3
            on timestep 10 would look like::

                {
                    5: {
                        10: 3
                    }
                }

    """
    disturbances = {}
    for i_c, c in enumerate(cases):
        for e in c["events"]:
            time_step = e["time_step"]
            dist_type_id = ref.get_disturbance_type_id(e["disturbance_type"])
            if i_c in disturbances:
                if time_step in disturbances[i_c]:
                    raise ValueError(
                        "more than one event found for index {0}, timestep {1}"
                        .format(i_c, time_step))
                else:
                    disturbances[i_c][time_step] = dist_type_id
            else:
                disturbances[i_c] = {time_step: dist_type_id}
    return disturbances


def initialize_inventory(cbm, cases, classifier_name, ref):
    """create a CBM inventory based on the specified test cases

    Args:
        cbm (libcbm.model.CBM): instance of CBM, used here to fetch
            classifier value ids from configuration
        cases (list): list of dict defining CBM test cases
        classifier_name (str): name of the single classifier used by the
            test cases
        ref (CBMDefaultsReference): reference for transforming string names

    Returns:
        object: an object which defines a valid inventory for
            :py:class:`libcbm.model.cbm.CBM` functions
    """

    n_stands = len(cases)
    classifiers = pd.DataFrame({
        classifier_name: np.array([
            cbm.get_classifier_value_id(
                classifier_name,
                case_generation.get_classifier_value_name(c["id"])
            )
            for c in cases], dtype=np.int32)
    })

    historic_disturbance_type = np.array(
        [
            ref.get_disturbance_type_id(c["historic_disturbance"])
            for c in cases],
        dtype=np.int32)

    last_pass_disturbance_type = np.array(
        [ref.get_disturbance_type_id(c["last_pass_disturbance"])
            for c in cases],
        dtype=np.int32)

    spatial_units = np.array(
        [ref.get_spatial_unit_id(c["admin_boundary"], c["eco_boundary"])
            for c in cases],
        dtype=np.int32)

    afforestation_pre_type_ids = []
    for c in cases:
        if not c["afforestation_pre_type"] is None:
            afforestation_pre_type_ids.append(
                ref.get_afforestation_pre_type_id(c["afforestation_pre_type"]))
        else:
            afforestation_pre_type_ids.append(0)

    afforestation_pre_type_id = np.array(
        afforestation_pre_type_ids, dtype=np.int32)

    land_class = np.ones(n_stands, dtype=np.int32)
    land_class[afforestation_pre_type_id > 0] = \
        ref.get_land_class_id("UNFCCC_CL_R_CL")

    inventory = cbm_variables.initialize_inventory(
        classifiers=classifiers,
        inventory=pd.DataFrame({
            "age": np.array([c["age"] for c in cases], dtype=np.int32),
            "spatial_unit": spatial_units,
            "afforestation_pre_type_id": afforestation_pre_type_id,
            "land_class": land_class,
            "historic_disturbance_type": historic_disturbance_type,
            "last_pass_disturbance_type": last_pass_disturbance_type,
            "delay": np.array([c["delay"] for c in cases], dtype=np.int32)
        }))
    return inventory


def run_test_cases(db_path, dll_path, cases, n_steps, spinup_debug=False):
    """Run CBM simulation test cases with libcbm

    Args:
        db_path (str): path to a cbm_defaults database
        dll_path (str): path to the libcbm compiled library
        cases (list): list of test cases in the format created by
            :py:func:`libcbm.test.casegeneration.generate_scenarios`
        n_steps (int): the number of timesteps to run for every test case
        spinup_debug (bool, optional): if specified, and True extra spinup
            debugging information is generated and returned (causes
            performance drop). Defaults to False.

    Returns:
        dict: dictionary containing the following keys/values:
            - pools: pd.DataFrame of pool results by case,timestep
            - flux:  pd.DataFrame of flux results by case,timestep
            - state_variable_result: pd.DataFrame of state variable
                simulation results by case,timestep
            - spinup_debug: if enabled, addition spinup debugging output in a
                pd.DataFrame by case,timestep
    """
    ref = CBMDefaultsReference(db_path, "en-CA")
    pool_codes = ref.get_pools()
    flux_indicators = ref.get_flux_indicators()
    classifier_name = "identifier"

    cbm = cbm_factory.create(
        model_factory=model_factory.create,
        db_path=db_path,
        dll_path=dll_path,
        merch_volume_to_biomass_factory=get_test_case_merch_volume_factory(
            cases, db_path, ref),
        classifiers_factory=get_test_case_classifier_factory(
            cases, classifier_name))

    n_stands = len(cases)
    pools = cbm_variables.initialize_pools(n_stands, pool_codes)
    flux = cbm_variables.initialize_flux(n_stands, flux_indicators)

    spinup_vars = cbm_variables.initialize_spinup_variables(n_stands)
    spinup_params = cbm_variables.initialize_spinup_parameters(n_stands)

    cbm_params = cbm_variables.initialize_cbm_parameters(n_stands)
    cbm_state = cbm_variables.initialize_cbm_state_variables(n_stands)

    inventory = initialize_inventory(
        cbm, cases, classifier_name, ref)

    # run CBM spinup
    spinup_debug_output = cbm.spinup(
        inventory=inventory,
        pools=pools,
        variables=spinup_vars,
        parameters=spinup_params,
        debug=spinup_debug
    )

    # initializes the CBM variables
    cbm.init(
        inventory=inventory,
        pools=pools,
        state_variables=cbm_state)

    # the following 3 variables store timestep by timestep results for
    # pools, flux and state variables
    pool_result = None
    flux_result = None
    state_variable_result = None

    pool_result = cbm_variables.append_simulation_result(
        pool_result, pools, 0)

    state_variable_result = cbm_variables.append_simulation_result(
        state_variable_result, cbm_state, 0)

    disturbances = get_disturbances(cases, ref)

    # run CBM for n_steps
    for t in range(1, n_steps+1):

        # clear the disturbance events for this timestep
        cbm_params.disturbance_type *= 0

        # fetch the disturbance events for each index for this timestep
        for k, v in disturbances.items():
            if t in v:
                cbm_params.disturbance_type[k] = v[t]

        cbm.step(
            inventory=inventory, pools=pools, flux=flux,
            state_variables=cbm_state, parameters=cbm_params)

        pool_result = cbm_variables.append_simulation_result(
            pool_result, pools, t)
        flux_result = cbm_variables.append_simulation_result(
            flux_result, flux, t)
        state_variable_result = cbm_variables.append_simulation_result(
            state_variable_result, cbm_state, t)

    return {
        "pools": pool_result,
        "flux": flux_result,
        "state_variable_result": state_variable_result,
        "spinup_debug": spinup_debug_output
    }
