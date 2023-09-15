# ----------------------------------------------------------------------------
# Copyright (c) 2016-2022, QIIME 2 development team.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------

# NB: copied nearly wholesale from q2cli/q2cli/tests/test_mystery_stew.py

import os
import subprocess
import tempfile
from q2dataflow.core.signature_converter.util import get_mystery_stew
from q2dataflow.languages.wdl.usage import WdlTestUsage
from q2dataflow.languages.cwl.usage import CwlTestUsage
import time
import pytest


def _labeler(val, prefix=None):
    return_val = val
    if hasattr(val, 'id'):
        return_val = val.id
    if prefix is not None:
        return_val = f"{prefix}_{return_val}"
    return return_val


def get_tests():
    tests = []
    try:
        plugin = get_mystery_stew()
    except KeyError:
        return tests
    for action in plugin.actions.values():
        for name in action.examples:
            tests.append((action, name))
    return tests


def _test_mystery_stew(action, example, test_usage_factory, settings=None):
    if os.environ.get('SKIP_SLEEP') is None:
        # Prevent docker-desktop crash
        time.sleep(1)

    example_f = action.examples[example]

    # TODO: put back test usage after testing
    #with tempfile.TemporaryDirectory() as tmpdir:
    from pathlib import Path
    tmpdir = f"/Users/abirmingham/Desktop/debugging/{action.id}_{example}"
    Path(tmpdir).mkdir(exist_ok=True)

    settings = {} if settings is None else settings
    settings['working_dir'] = tmpdir
    test_usage = test_usage_factory(settings=settings)

    try:
        example_f(test_usage)

        rendered = '\n'.join(test_usage.recorder)
        for ref, data in test_usage.get_example_data():
            data.save(os.path.join(tmpdir, ref))

        test_usage.save_run_files(tmpdir)
    except NotImplementedError:
        # skip, not fail, tests for known not-implemented functionality
        pytest.skip(f"No implementation supporting {action.id} {example}")
        return

    # TODO remove debug save
    cmds_fp = f"/Users/abirmingham/Desktop/debugging/{action.id}_{example}/{action.id}_{example}.cmds"
    with open(cmds_fp, "w") as r:
        r.write(rendered)

    subprocess.run([rendered],
                   shell=True,
                   check=True,
                   cwd=tmpdir,
                   env={**os.environ})

    # TODO remove debug print
    print("done w process")


@pytest.mark.parametrize('action,example', get_tests(), ids=lambda x: _labeler(x, "wdl"))
def test_wdl_mystery_stew(action, example):
    _test_mystery_stew(action, example, WdlTestUsage)


@pytest.mark.parametrize('action,example', get_tests(), ids=lambda x: _labeler(x, "cwl"))
def test_cwl_mystery_stew(action, example):
    _test_mystery_stew(action, example, CwlTestUsage, settings={"conda": True})