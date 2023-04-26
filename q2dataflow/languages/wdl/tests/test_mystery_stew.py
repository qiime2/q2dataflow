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
import time
import pytest


def _labeler(val):
    if hasattr(val, 'id'):
        return val.id
    return val


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


@pytest.mark.parametrize('action,example', get_tests(), ids=_labeler)
def test_mystery_stew(action, example, docker_image):
    if os.environ.get('SKIP_SLEEP') is None:
        # Prevent docker-desktop crash
        time.sleep(1)

    example_f = action.examples[example]
    use = WdlTestUsage(docker_image=docker_image)
    example_f(use)
    rendered = '\n'.join(use.recorder)

    with tempfile.TemporaryDirectory() as tmpdir:
        for ref, data in use.get_example_data():
            data.save(os.path.join(tmpdir, ref))

        try:
            use.save_wdl_run_files(tmpdir)
        except NotImplementedError:
            # skip, not fail, tests for known not-implemented functionality
            pytest.skip(f"No implementation supporting {action.id} {example}")
            return

        subprocess.run([rendered],
                       shell=True,
                       check=True,
                       cwd=tmpdir,
                       env={**os.environ})
