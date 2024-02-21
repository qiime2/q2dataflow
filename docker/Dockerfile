FROM quay.io/qiime2/core

# Custom cache invalidation
ARG CACHEBUST=1

# TODO: remove WIP branch specification once WIP goes into main
RUN git clone --branch collections_support https://github.com/qiime2/q2dataflow.git

RUN pip install -e ./q2dataflow

# TODO ask Evan re options for auto-detecting qiime env name
RUN echo "conda activate qiime2-2023.7" >> ~/.profile

ENV MYSTERY_STEW=1
RUN qiime dev refresh-cache
