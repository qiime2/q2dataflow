# q2dataflow

## Installation of WIP package

`q2dataflow` requires installation of the following packages:

* `qiime2`, including `qiime2.sdk`
* `click`
* `pytest`

Additionally, the WDL-related tests require:

1. an installation of the WDL emulator [`miniwdl`](https://github.com/chanzuckerberg/miniwdl)
2. a docker environment containing an installation of`q2dataflow` and `qiime2`

If running on a Mac, it is very important for #1 to follow the Mac-specific
install instructions described in [https://github.com/chanzuckerberg/miniwdl/issues/145](https://github.com/chanzuckerberg/miniwdl/issues/145); 
`miniwdl` will fail in somewhat inscrutable ways if the `export TMPDIR=/tmp` step near the end is not performed.

For #2, a dockerfile is provided that will install `q2dataflow` and also the latest
`qiime2` distribution available on [quay.io/repository/qiime2/core](https://quay.io/repository/qiime2/core?tab=tags).
Note that when a new release becomes available, it is currently necessary to update the qiime2 environment name used in the 
dockerfile (e.g., changing `RUN echo "conda activate qiime2-2022.8"` to `RUN echo "conda activate qiime2-2023.2"`)

Using this dockerfile, a docker image can be built from the command line in the top `q2dataflow` directory using the command

```docker build docker/ --build-arg CACHEBUST=$(date +%s) --tag testq2dataflow```

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