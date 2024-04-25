# q2dataflow - QIIME 2 Dataflow Interface
Automatic generator of dataflow descriptor languages.

The purpose of this interface is to enable the use of QIIME 2 plugins in
environments which support [Dockstore](https://dockstore.org) tools/workflows.

To see rendered tools, visit:

[qiime2/dockstore-tools](https://github.com/qiime2/dockstore-tools) (in progress)


### Currently supported:

  * [Workflow Description Language](https://openwdl.org/)
  * [Common Workflow Lanauage](https://www.commonwl.org/) 

### Future work:
  * [Automatic .dockstore.yml registration](https://docs.dockstore.org/en/stable/getting-started/github-apps/github-apps.html#example-yml-files)
  * [NextFlow](https://www.nextflow.io/) (TBD)


A similar interface exists for Galaxy Tool definitions called [q2galaxy](https://github.com/qiime2/q2galaxy),
which may be integrated into q2dataflow as well (although publication of these tools to Dockstore is not currently possible as only `.ga` files (not tools) are supported).

## Usage

```
q2dataflow {cwl | wdl} template {all | builtins} {output directory}
```

or

```
q2dataflow {cwl | wdl} template plugin {plugin_id} {output directory}
```

## Installation instructions (WDL)

`q2dataflow` requires installation of the following packages:

* `qiime2`, most conveniently installed via a distro
* `click`
* `pytest`

Then to install `q2wdl`, activate an environment with QIIME 2 and run:
```
pip install 'q2dataflow @ git+https://github.com/qiime2/q2dataflow.git'
```

Additionally, the WDL-related tests require:

1. an installation of the WDL emulator [`miniwdl`](https://github.com/chanzuckerberg/miniwdl)
2. a docker environment containing an installation of`q2dataflow` and `qiime2`

If running on a Mac, it is very important for #1 to follow the Mac-specific
install instructions described in [https://github.com/chanzuckerberg/miniwdl/issues/145](https://github.com/chanzuckerberg/miniwdl/issues/145);
`miniwdl` will fail in somewhat inscrutable ways if the `export TMPDIR=/tmp` step near the end is not performed.

For #2, a dockerfile is provided that will install `q2dataflow` and also the latest
`qiime2` distribution available on [quay.io/repository/qiime2/amplicon](https://quay.io/repository/qiime2/amplicon?tab=tags).

Using this dockerfile, a docker image can be built from the command line in the top `q2dataflow` directory using the command

```docker build docker/ --build-arg CACHEBUST=$(date +%s) REF=main --tag testq2dataflow```

The name of the image, `testq2dataflow`, is important: it is used in generating
the test commands in `q2dataflow\languages\wdl\usage.py`.  Currently, it is set
in a variable in this module and should presumably be refactored to elsewhere.

The tests generate wdl files and parameter files and then run each wdl file (using
the parameters in the associated parameters file) through `miniwdl` on the `testq2dataflow`
docker image.  If the tests hang, go to a terminal, enter the conda environment
containing `miniwdl`, and run `miniwdl run_self_test`.  If *this* hangs due to
errors stating "error while loading TLS certificate in
/var/lib/docker/swarm/certificates/swarm-node.crt", then run
`docker swarm leave --force` and try again.

