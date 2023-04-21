# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import json
import click

import qiime2.sdk as sdk

from q2dataflow.core.description_language.drivers import \
    action_runner, builtin_runner, get_version
from q2dataflow.core.description_language import \
    (template_plugin_iter, template_all_iter, template_builtins_iter)

OUTPUT_DIR = click.Path(file_okay=False, dir_okay=True, exists=True)


def _echo_status(status):
    line = json.dumps(status)
    if status['status'] == 'error':
        click.secho(line, fg='red', err=True)
    elif status['status'] == 'created':
        click.secho(line, fg='green')
    else:
        click.secho(line, fg='yellow')


def plugin(plugin, output, templater_lib_name):
    pm = sdk.PluginManager()
    plugin = pm.get_plugin(id=plugin)

    for status in template_plugin_iter(plugin, output, templater_lib_name):
        _echo_status(status)


def builtins(output, templater_lib_name):
    for status in template_builtins_iter(output, templater_lib_name):
        _echo_status(status)


def all(output, templater_lib_name):
    for status in template_all_iter(output, templater_lib_name):
        _echo_status(status)


def run(plugin, action, config, parse_primitives=False):
    if plugin == 'tools':
        # TODO does this also need to parse primitives?
        builtin_runner(action, config)
    else:
        action_runner(plugin, action, config, parse_primitives=parse_primitives)


def version(plugin):
    print('%s version %s' % (plugin, get_version(plugin)))
