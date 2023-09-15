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

# iterators to template (create template files for) various qiime2 components
__all__ = ['template_plugin_iter', 'template_builtins_iter',
           'template_all_iter']


def _collect_test_data_iter(action, test_dir, templater_lib):
    for idx, example in enumerate(action.examples.values()):
        use = templater_lib.COLLECTABLE_TEST_USAGE(
            example_path=(action, idx), write_dir=test_dir)
        example(use)
        yield from use.created_files


def _create_dir_iter(directory, templater_lib):
    if not os.path.exists(directory):
        os.mkdir(directory)
        yield {'status': 'created', 'type': 'directory', 'path': directory}


def _store_action_template_str_iter(action_template_str, path, templater_lib):
    is_existing = os.path.exists(path)

    templater_lib.store_action_template_str(action_template_str, path)

    if not is_existing:
        yield {'status': 'created', 'type': 'file', 'path': path}
    else:
        yield {'status': 'updated', 'type': 'file', 'path': path}


def _template_action_iter(plugin, action, directory, templater_lib, settings):
    settings = _add_env_meta_to_settings(settings)

    filename = templater_lib.make_action_template_id(
        plugin.id, action.id) + templater_lib.get_extension()
    filepath = os.path.join(directory, filename)
    test_dir = os.path.join(directory, 'test-data', '')

    action_template_str = None
    try:
        # generate a string holding the action template in the relevant language
        action_template_str = templater_lib.make_action_template_str(
            plugin, action, settings=settings)
    except Exception as ex:  # noqa E722
        yield {'status': 'error', 'type': 'file',
               'path': plugin.id + "_" + action.id}

    if action_template_str:
        # write out the action template string to the filepath specified;
        # the enclosing dirs will be created if they don't exist yet
        yield from _store_action_template_str_iter(
            action_template_str, filepath, templater_lib)

        # TODO: does this test dir actually need to be created if
        #  COLLECTABLE_TEST_USAGE is not true?
        yield from _create_dir_iter(test_dir, templater_lib)
        if templater_lib.COLLECTABLE_TEST_USAGE:
            yield from _collect_test_data_iter(action, test_dir, templater_lib)


def template_plugin_iter(plugin, directory, templater_lib_name, settings):
    templater_lib = importlib.import_module(templater_lib_name)

    suite_name = f'suite_qiime2_{plugin.id.replace("_", "-")}'
    suite_dir = os.path.join(directory, suite_name, '')

    # if there are any actions, make a dir to hold their templates
    if plugin.actions:
        yield from _create_dir_iter(suite_dir, templater_lib)

    # generate and store a template string for each action
    for action in plugin.actions.values():
        yield from _template_action_iter(
            plugin, action, suite_dir, templater_lib, settings)


def template_builtins_iter(directory, templater_lib_name, settings):
    templater_lib = importlib.import_module(templater_lib_name)

    settings = _add_env_meta_to_settings(settings)

    # create a dir to store the templates for the builtin actions
    suite_name = 'suite_qiime2_tools'
    suite_dir = os.path.join(directory, suite_name, '')
    yield from _create_dir_iter(suite_dir, templater_lib)

    for action_template_id, action_template_str_maker in \
            templater_lib.BUILTIN_MAKERS.items():
        # generate string holding the action template in the relevant language
        action_template_str = action_template_str_maker(
            action_template_id, settings)

        # write out the tool template string to the filepath specified;
        # the enclosing dirs will be created if they don't exist yet
        filepath = os.path.join(
            suite_dir, action_template_id + templater_lib.get_extension())
        yield from _store_action_template_str_iter(
            action_template_str, filepath, templater_lib)


def template_all_iter(directory, templater_lib_name, settings):
    pm = _sdk.PluginManager()
    for plugin in pm.plugins.values():
        yield from template_plugin_iter(
            plugin, directory, templater_lib_name, settings)

    yield from template_builtins_iter(directory, templater_lib_name, settings)


def _add_env_meta_to_settings(settings):
    if settings is None:
        settings = {}
    settings["conda_meta"] = _environment.find_conda_meta()
    return settings