#!/bin/bash

set -x
set -e

SCRIPTDIR=$(
    cd $(dirname "$0")
    pwd
)

if [ -n ${VENV_DIR} ]; then
    source ${VENV_DIR}/bin/activate
fi

JUNIT_LOGS="/logs/tests"

PYTHONPATH=${SCRIPTDIR}/..:${PYTHONPATH}

MODULE_NAME=$(basename ${SCRIPTDIR})

if [ "x${TESTS_OUTPUT_JUNIT}" != "x1" ]; then
    pylint --output-format=colorized \
        --rcfile=${SCRIPTDIR}/tests/pylintrc \
        --exit-zero \
        ${SCRIPTDIR}
    mypy --config-file=${SCRIPTDIR}/tests/mypy.ini ${SCRIPTDIR} \
    || true
else
    mkdir -p ${JUNIT_LOGS}
    pylint --output-format=pylint2junit.JunitReporter \
        --rcfile=${SCRIPTDIR}/tests/pylintrc \
        --exit-zero \
        ${SCRIPTDIR} \
        > ${JUNIT_LOGS}/lunad_pylint.xml
    mypy --config-file=${SCRIPTDIR}/tests/mypy.ini \
        --junit-xml=/logs/tests/lunad_mypy.xml \
        ${SCRIPTDIR} \
    || true
fi
