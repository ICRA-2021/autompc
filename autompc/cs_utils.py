# Created by William Edwards (wre2@illinois.edu)

import ConfigSpace as CS
import ConfigSpace.hyperparameters as CSH
import ConfigSpace.conditions as CSC
import copy

from ConfigSpace import ConfigurationSpace
from ConfigSpace.hyperparameters import (
    Hyperparameter,
    Constant,
    FloatHyperparameter,
)
from ConfigSpace.conditions import (
    ConditionComponent,
    AbstractCondition,
    AbstractConjunction,
    EqualsCondition,
)
from ConfigSpace.forbidden import (
    AbstractForbiddenComponent,
    AbstractForbiddenClause,
    AbstractForbiddenConjunction,
)

def set_subspace_configuration(cfg, prefix, sub_cfg, delimiter=":"):
    prefix = prefix + delimiter
    for key, val in cfg.get_dictionary().items():
        if key[:len(prefix)] == prefix:
            sub_cfg[key.split(delimiter)[1]] = val

def set_parent_configuration(cfg, prefix, sub_cfg, delimiter=":"):
    prefix = prefix + delimiter
    for key, val in sub_cfg.get_dictionary().items():
        cfg[prefix+key] = val

def add_configuration_space(self,
                            prefix: str,
                            configuration_space: 'ConfigurationSpace',
                            delimiter: str = ":",
                            parent_hyperparameter: Hyperparameter = None
                            ):
    """
    Combine two configuration space by adding one the other configuration
    space. The contents of the configuration space, which should be added,
    are renamed to ``prefix`` + ``delimiter`` + old_name.

    Parameters
    ----------
    prefix : str
        The prefix for the renamed hyperparameter | conditions |
        forbidden clauses
    configuration_space : :class:`~ConfigSpace.configuration_space.ConfigurationSpace`
        The configuration space which should be added
    delimiter : str, optional
        Defaults to ':'
    parent_hyperparameter : :ref:`Hyperparameters`, optional
        Adds for each new hyperparameter the condition, that
        ``parent_hyperparameter`` is active

    Returns
    -------
    :class:`~ConfigSpace.configuration_space.ConfigurationSpace`
        The configuration space, which was added
    """
    if not isinstance(configuration_space, ConfigurationSpace):
        raise TypeError("The method add_configuration_space must be "
                        "called with an instance of "
                        "ConfigSpace.configuration_space."
                        "ConfigurationSpace.")

    new_parameters = []
    for hp in configuration_space.get_hyperparameters():
        new_parameter = copy.copy(hp)
        # Allow for an empty top-level parameter
        if new_parameter.name == '':
            new_parameter.name = prefix
        else:
            new_parameter.name = "%s%s%s" % (prefix, delimiter,
                                             new_parameter.name)
        new_parameters.append(new_parameter)
    self.add_hyperparameters(new_parameters)

    conditions_to_add = []
    for condition in configuration_space.get_conditions():
        new_condition = copy.copy(condition)
        dlcs = new_condition.get_descendant_literal_conditions()
        for dlc in dlcs:
            if dlc.child.name == prefix or dlc.child.name == '':
                dlc.child.name = prefix
            elif not dlc.child.name.startswith(
                            "%s%s" % (prefix, delimiter)):
                dlc_child_name = "%s%s%s" % (
                    prefix, delimiter, dlc.child.name)
                dlc.child = self.get_hyperparameter(dlc_child_name)
            if dlc.parent.name == prefix or dlc.parent.name == '':
                dlc.parent.name = prefix
            elif not dlc.parent.name.startswith(
                            "%s%s" % (prefix, delimiter)):
                dlc_parent_name = "%s%s%s" % (
                    prefix, delimiter, dlc.parent.name)
                dlc.parent = self.get_hyperparameter(dlc_parent_name)
        conditions_to_add.append(new_condition)
    self.add_conditions(conditions_to_add)

    forbiddens_to_add = []
    for forbidden_clause in configuration_space.forbidden_clauses:
        # new_forbidden = copy.deepcopy(forbidden_clause)
        new_forbidden = forbidden_clause
        dlcs = new_forbidden.get_descendant_literal_clauses()
        for dlc in dlcs:
            if dlc.hyperparameter.name == prefix or \
                            dlc.hyperparameter.name == '':
                dlc.hyperparameter.name = prefix
            elif not dlc.hyperparameter.name.startswith(
                            "%s%s" % (prefix, delimiter)):
                dlc.hyperparameter.name = "%s%s%s" % \
                                          (prefix, delimiter,
                                           dlc.hyperparameter.name)
        forbiddens_to_add.append(new_forbidden)
    self.add_forbidden_clauses(forbiddens_to_add)

    conditions_to_add = []
    if parent_hyperparameter is not None:
        for new_parameter in new_parameters:
            # Only add a condition if the parameter is a top-level
            # parameter of the new configuration space (this will be some
            #  kind of tree structure).
            if self.get_parents_of(new_parameter):
                continue
            condition = EqualsCondition(new_parameter,
                                        parent_hyperparameter['parent'],
                                        parent_hyperparameter['value'])
            conditions_to_add.append(condition)
    self.add_conditions(conditions_to_add)
