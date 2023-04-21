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


@root.group()
@click.pass_context
def q2wdl(ctx):
    ctx.obj = {MODULE_NAME: "q2dataflow.languages.wdl"}


@q2wdl.group()
@click.pass_context
def template(ctx):
    pass


@template.command()
@click.argument('plugin', type=str)
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def plugin(ctx, plugin, output):
    clickin.plugin(plugin, output, ctx.obj[MODULE_NAME])


@template.command()
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def builtins(ctx, output):
    clickin.builtins(output, ctx.obj[MODULE_NAME])


@template.command()
@click.argument('output', type=clickin.OUTPUT_DIR)
@click.pass_context
def all(ctx, output):
    clickin.all(output, ctx.obj[MODULE_NAME])


@q2wdl.command()
@click.argument('plugin', type=str)
@click.argument('action', type=str)
@click.argument('inputs', type=click.Path(file_okay=True, dir_okay=False,
                                          exists=True))
def run(plugin, action, inputs):
    with open(inputs, 'r') as fh:
        config = json.load(fh)

    config = _reformat_q2wdl_params(config)

    clickin.run(plugin, action, config, parse_primitives=True)


@root.command()
@click.argument('plugin', type=str)
def version(plugin):
    clickin.version(plugin)


if __name__ == '__main__':
    root()
