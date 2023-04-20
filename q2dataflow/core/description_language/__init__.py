# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

import os
import importlib

import qiime2.sdk as _sdk
import q2dataflow.core.description_language.environment as _environment


__all__ = ['template_plugin_iter', 'template_builtins_iter',
           'template_all_iter']


def _collect_test_data(action, test_dir, templater_lib):
    for idx, example in enumerate(action.examples.values()):
        use = templater_lib.COLLECTABLE_TEST_USAGE(
            example_path=(action, idx), write_dir=test_dir)
        example(use)
        yield from use.created_files


def _template_dir_iter(directory, templater_lib):
    if not os.path.exists(directory):
        os.mkdir(directory)
        yield {'status': 'created', 'type': 'directory', 'path': directory}


def _template_tool_iter(tool, path, templater_lib):
    is_existing = os.path.exists(path)

    templater_lib.write_tool(tool, path)

    if not is_existing:
        yield {'status': 'created', 'type': 'file', 'path': path}
    else:
        yield {'status': 'updated', 'type': 'file', 'path': path}


def _template_action_iter(plugin, action, directory, templater_lib):
    meta = _environment.find_conda_meta()

    filename = templater_lib.make_tool_id(
        plugin.id, action.id) + templater_lib.get_extension()
    filepath = os.path.join(directory, filename)
    test_dir = os.path.join(directory, 'test-data', '')

    tool = None
    try:
        tool = templater_lib.make_tool(meta, plugin, action)
    except:  # noqa E722
        yield {'status': 'error', 'type': 'file',
               'path': plugin.id + "_" + action.id}

    if tool:
        yield from _template_tool_iter(tool, filepath, templater_lib)
        yield from _template_dir_iter(test_dir, templater_lib)
        if templater_lib.COLLECTABLE_TEST_USAGE:
            yield from _collect_test_data(action, test_dir, templater_lib)


def template_plugin_iter(plugin, directory, templater_lib_name):
    templater_lib = importlib.import_module(templater_lib_name)

    suite_name = f'suite_qiime2_{plugin.id.replace("_", "-")}'
    suite_dir = os.path.join(directory, suite_name, '')

    if plugin.actions:
        yield from _template_dir_iter(suite_dir, templater_lib)
    for action in plugin.actions.values():
        yield from _template_action_iter(
            plugin, action, suite_dir, templater_lib)


def template_builtins_iter(directory, templater_lib_name):
    templater_lib = importlib.import_module(templater_lib_name)

    meta = _environment.find_conda_meta()

    suite_name = 'suite_qiime2_tools'
    suite_dir = os.path.join(directory, suite_name, '')
    yield from _template_dir_iter(suite_dir, templater_lib)

    for tool_id, tool_maker in templater_lib.BUILTIN_MAKERS.items():
        path = os.path.join(suite_dir, tool_id + templater_lib.get_extension())
        tool = tool_maker(meta, tool_id)
        yield from _template_tool_iter(tool, path, templater_lib)


def template_all_iter(directory, templater_lib_name):
    pm = _sdk.PluginManager()
    for plugin in pm.plugins.values():
        yield from template_plugin_iter(plugin, directory, templater_lib_name)

    yield from template_builtins_iter(directory, templater_lib_name)
