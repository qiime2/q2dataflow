# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from datetime import datetime
from qiime2 import __version__ as q2_version
import qiime2.sdk as sdk
import warnings


def get_copyright():
    copyright = f"""
Copyright (c) {datetime.now().year}, QIIME 2 development team.

Distributed under the terms of the Modified BSD License. (SPDX: BSD-3-Clause)
"""
    return copyright


def get_q2_version():
    return q2_version


def get_mystery_stew(desired_filters=None):
    from q2_mystery_stew.plugin_setup import create_plugin
    from q2_mystery_stew.generators import FILTERS

    try:
        pm = sdk.PluginManager.reuse_existing()
    except sdk.UninitializedPluginManagerError:
        pm = sdk.PluginManager(add_plugins=False)

        if desired_filters is not None:
            _check_filters(desired_filters, FILTERS)
        else:
            desired_filters = {filter_: True for filter_ in FILTERS}

        test_plugin = create_plugin(**desired_filters)

        pm.add_plugin(test_plugin)

    return pm.get_plugin(id='mystery_stew')


def _check_filters(specified_filters, all_filter_types):
    missing_filter_types = []
    for curr_filter_type in all_filter_types:
        if curr_filter_type not in specified_filters:
            missing_filter_types.append(curr_filter_type)

    if len(missing_filter_types) > 0:
        missing_filter_types_str = ', '.join(missing_filter_types)
        warnings.warn(f"Not performing tests for: {missing_filter_types_str}")
