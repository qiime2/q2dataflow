# ----------------------------------------------------------------------------
# Copyright (c) 2018-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
import click
import json

import q2dataflow.core.description_language.interface as clickin
from q2dataflow.languages.wdl.templaters.helpers import q2wdl_prefix, \
    metafile_synth_param_prefix, reserved_param_prefix
import q2dataflow.languages.wdl.util as wdl_util
import q2dataflow.languages.cwl.util as cwl_util

MODULE_NAME = "module_name"


def _make_metadata_param(curr_source, curr_col):
    if curr_source is None:
        return None

    curr_type = curr_source.split(".")[-1]
    if curr_type not in ["qza", "tsv"]:
        raise ValueError(f"Unexpected metadata type: '{curr_type}'")

    new_metadata_val = {'type': curr_type,
                        'source': curr_source,
                        'column': curr_col}
    return new_metadata_val


def _reformat_metadata_param(curr_metafile_key, params_dict):
    new_param_val = []
    curr_col = None

    curr_val = params_dict[curr_metafile_key]
    params_dict.pop(curr_metafile_key)

    curr_param = curr_metafile_key.replace(metafile_synth_param_prefix, "")
    if curr_val is None:
        new_param_val = None
    else:
        # if this is a metadata column param, can be only one metadata file
        if curr_param in params_dict:
            curr_col = params_dict[curr_param]
            params_dict.pop(curr_param)

            new_param_val = _make_metadata_param(curr_val, curr_col)
        else:
            # a metadata file param can have multiple files
            for curr_source in curr_val:
                curr_type = curr_source.split(".")[-1]
                if curr_type not in ["qza", "tsv"]:
                    raise ValueError(
                        f"Unexpected metadata type: '{curr_type}'")

                new_metadata_val = {'type': curr_type,
                                    'source': curr_source,
                                    'column': curr_col}
                new_param_val.append(new_metadata_val)
            # next metadata source

    params_dict[curr_param] = new_param_val
    return params_dict


def _reformat_q2wdl_params(params_dict):
    # find and deal with any "special" params inserted by q2wdl
    q2wdl_special_keys = [x for x in params_dict.keys()
                          if x.startswith(q2wdl_prefix)]
    for curr_key in q2wdl_special_keys:
        if curr_key.startswith(metafile_synth_param_prefix):
            _reformat_metadata_param(curr_key, params_dict)
        elif curr_key.startswith(reserved_param_prefix):
            native_key = curr_key.replace(reserved_param_prefix, "")
            params_dict[native_key] = params_dict[curr_key]
            params_dict.pop(curr_key)
        else:
            raise ValueError(f"Unrecognized q2wdl prefix: '{curr_key}'")

    return params_dict


@click.group()
def root():
    pass


# Q2 plugin version
@root.command()
@click.argument('plugin', type=str)
def version(plugin):
    clickin.version(plugin)


# WDL
@root.group()
@click.version_option(wdl_util.Q2_WDL_VERSION)
@click.pass_context
def wdl(ctx):
    ctx.obj = {MODULE_NAME: "q2dataflow.languages.wdl"}


@wdl.group("template", short_help="Generate WDL workflow templates from available actions")
@click.pass_context
def wdl_template(ctx):
    pass


@wdl_template.command()
@click.argument('plugin', type=str)
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def plugin(ctx, plugin, output):
    clickin.plugin(plugin, output, ctx.obj[MODULE_NAME], True)


@wdl_template.command()
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def builtins(ctx, output):
    clickin.builtins(output, ctx.obj[MODULE_NAME], True)


@wdl_template.command()
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def all(ctx, output):
    clickin.all(output, ctx.obj[MODULE_NAME], True)


@wdl.command("run", help="Do not use directly: used internally by q2dataflow wdl")
@click.argument('plugin', type=str)
@click.argument('action', type=str)
@click.argument('inputs-json', type=click.Path(file_okay=True, dir_okay=False,
                                          exists=True))
def run_wdl(plugin, action, inputs_json):
    with open(inputs_json, 'r') as fh:
        config = json.load(fh)

    config = _reformat_q2wdl_params(config)

    clickin.run(plugin, action, config, parse_primitives=True)


# CWL
@root.group()
@click.version_option(cwl_util.Q2_CWL_VERSION)
@click.pass_context
def cwl(ctx):
    ctx.obj = {MODULE_NAME: "q2dataflow.languages.cwl"}


@cwl.group(name="template", short_help="Generate CWL tool templates from available actions")
@click.pass_context
def cwl_template(ctx):
    pass


@cwl_template.command(short_help="For use within a Conda environment")
@click.option('--plugin', required=False, help='Template only a single plugin')
@click.option('--tools/--no-tools', default=True, help='Include QIIME 2 tools')
@click.option('--quiet/--no-quiet', default=False)
@click.argument('output-dir', type=click.Path(file_okay=False, writable=True))
@click.pass_context
def conda(ctx, output_dir: str, tools: bool = True, plugin: str = None,
          quiet: bool = False):

    ctx.obj["conda"] = True

    if plugin:
        clickin.plugin(plugin, output_dir, ctx.obj[MODULE_NAME],
                       quiet, settings=ctx.obj)
        if tools:
            clickin.builtins(output_dir, ctx.obj[MODULE_NAME],
                             quiet, settings=ctx.obj)
    else:
        # TODO: no good way NOT to do tools when doing all ...
        clickin.all(output_dir, ctx.obj[MODULE_NAME], quiet, settings=ctx.obj)


def _temp_inner_conda(ctx, output_dir: str, tools: bool = True,
                      plugin: str = None, quiet: bool = False):

    ctx.obj["conda"] = True

    if plugin:
        clickin.plugin(plugin, output_dir, ctx.obj[MODULE_NAME],
                       quiet, settings=ctx.obj)
        if tools:
            clickin.builtins(output_dir, ctx.obj[MODULE_NAME],
                             quiet, settings=ctx.obj)
    else:
        clickin.all(output_dir, ctx.obj[MODULE_NAME], quiet, settings=ctx.obj)


@cwl_template.command(short_help="For use within a Docker container")
# TODO: don't have an easy way to leave tools out ... ignoring for now
@click.option('--tools/--no-tools', default=True, help='Include QIIME 2 tools')
@click.option('--remote', 'availability', flag_value='remote', default=True,
              help='Image is available on hub.docker.com (default)')
@click.option('--local', 'availability', flag_value='local',
              help='Image is only available on current host.')
@click.option('--quiet/--no-quiet', default=False)
@click.argument('image-id')
@click.pass_context
def docker(ctx, image_id: str, tools: bool = True, availability: str = 'remote',
           quiet: bool = False):

    output_dir = '/tmp/cwl-tools/'
    ctx.obj["docker"] = {
        "image_id": image_id,
        "availability": availability
    }

    clickin.all(output_dir, ctx.obj[MODULE_NAME], quiet, settings=ctx.obj)


@cwl.command(name="run", help="Do not use directly: used internally by q2dataflow cwl")
@click.argument('plugin', type=str)
@click.argument('action', type=str)
@click.argument('inputs-json',
                type=click.Path(file_okay=True, dir_okay=False, exists=True))
def run_cwl(plugin, action, inputs_json):
    with open(inputs_json, 'r') as fh:
        config = json.load(fh)['inputs']

    clickin.run(plugin, action, config, parse_primitives=True)


def test_template_plugin():
    cli_runner = CliRunner()
    result = cli_runner.invoke(cwl, ['template', 'conda', '--plugin', 'composition', '~/Temp/q2cwl'])
    print(result)


if __name__ == '__main__':
    root()
