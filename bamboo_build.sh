#!/bin/bash -xe

rm -rf prebuilts build
test -d .pip/wheels && find .pip/wheels -type f ! -name '*none-any.whl' -print -delete || true

BLASR=tarballs/blasr.tgz
BLASR_LIBCPP=tarballs/blasr_libcpp.tgz
PBBAM=tarballs/pbbam.tgz

NX3PBASEURL=http://nexus/repository/unsupported/pitchfork/gcc-6.4.0
export PATH=$PWD/build/bin:/mnt/software/a/anaconda2/4.2.0/bin:$PATH
export PYTHONUSERBASE=$PWD/build
export CFLAGS="-I/mnt/software/a/anaconda2/4.2.0/include"
PIP="pip --cache-dir=$bamboo_build_working_directory/.pip"

mkdir -p build/bin build/lib build/include build/share
tar zxf $BLASR_LIBCPP -C build
tar zxf $BLASR        -C build
tar zxf $PBBAM        -C build
curl -s -L $NX3PBASEURL/samtools-1.3.1.tgz | tar zxf - -C build
curl -s -L $NX3PBASEURL/ncurses-6.0.tgz | tar zxf - -C build

type module >& /dev/null || . /mnt/software/Modules/current/init/bash
module load gcc
module load git
module load hdf5-tools
module load htslib
$PIP install --user \
  $NX3PBASEURL/pythonpkgs/pysam-0.13-cp27-cp27mu-linux_x86_64.whl \
  $NX3PBASEURL/pythonpkgs/xmlbuilder-1.0-cp27-none-any.whl \
  $NX3PBASEURL/pythonpkgs/avro-1.7.7-cp27-none-any.whl \
  iso8601 \
  $NX3PBASEURL/pythonpkgs/tabulate-0.7.5-cp27-none-any.whl \
  cram
ln -sfn ../data repos/PacBioTestData/pbtestdata/data
$PIP install --user -e repos/PacBioTestData
$PIP install --user -e repos/pbcore
$PIP install --user -e repos/pbcommand
$PIP install --user -e repos/pbalign

rm -rf test-reports
mkdir test-reports
module load bamtools/2.4.1
export LD_LIBRARY_PATH=$PWD/build/lib:$LD_LIBRARY_PATH:/mnt/software/a/anaconda2/4.2.0/lib
cd repos/pbalign
nosetests  \
    --verbose --with-xunit \
    --xunit-file=${bamboo_build_working_directory}/test-reports/pbalign_xunit.xml \
    tests/unit/*.py || true
cram \
    --xunit-file=${bamboo_build_working_directory}/test-reports/pbalign_cramunit.xml \
    tests/cram || true
chmod +w -R .
