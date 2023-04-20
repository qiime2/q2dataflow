# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import qiime2.sdk as sdk


def get_mystery_stew():
    from q2_mystery_stew.plugin_setup import create_plugin

    pm = sdk.PluginManager(add_plugins=False)

    test_plugin = create_plugin(
        ints=True,
        strings=True,
        bools=True,
        floats=True,
        artifacts=True,
        primitive_unions=True,
        metadata=True,
        collections=True,
        outputs=True,
        typemaps=True
    )

    pm.add_plugin(test_plugin)
    return pm.get_plugin(id='mystery_stew')
