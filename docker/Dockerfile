FROM quay.io/qiime2/amplicon

# Custom cache invalidation
ARG CACHEBUST=1
ARG REF

RUN git clone $REF https://github.com/qiime2/q2dataflow.git \
  && cd q2dataflow && git fetch origin $REF && git checkout FETCH_HEAD && cd ..

RUN pip install -e ./q2dataflow

ENV MYSTERY_STEW=1
RUN qiime dev refresh-cache
