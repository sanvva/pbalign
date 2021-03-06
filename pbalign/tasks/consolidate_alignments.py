
# FIXME this should probably live somewhere more general, e.g. pbdataset?

"""
Consolidate AlignmentSet .bam files
"""

import functools
import tempfile
import logging
import os.path as op
import os
import sys

from pbcommand.models import get_pbparser, FileTypes, ResourceTypes, DataStore, DataStoreFile
from pbcommand.cli import pbparser_runner
from pbcommand.utils import setup_log
from pbcore.io import openDataSet


class Constants(object):
    TOOL_ID = "pbalign.tasks.consolidate_alignments"
    VERSION = "0.2.0"
    DRIVER = "python -m pbalign.tasks.consolidate_alignments --resolved-tool-contract "
    CONSOLIDATE_ID = "pbalign.task_options.consolidate_aligned_bam"
    N_FILES_ID = "pbalign.task_options.consolidate_n_files"
    BAI_FILE_TYPES = {
        FileTypes.BAMBAI.file_type_id,
        FileTypes.I_BAI.file_type_id
    }


def get_parser(tool_id=Constants.TOOL_ID,
               file_type=FileTypes.DS_ALIGN,
               driver_exe=Constants.DRIVER,
               version=Constants.VERSION,
               description=__doc__):
    ds_type = file_type.file_type_id.split(".")[-1]
    p = get_pbparser(tool_id,
                     version,
                     "{t} consolidate".format(t=ds_type),
                     description,
                     driver_exe,
                     is_distributed=True,
                     resource_types=(ResourceTypes.TMP_DIR,))

    p.add_input_file_type(file_type,
                          "align_in",
                          "Input {t}".format(t=ds_type),
                          "Gathered {t} to consolidate".format(t=ds_type))
    p.add_output_file_type(file_type,
                           "ds_out",
                           "Alignments",
                           description="Alignment results dataset",
                           default_name="combined")
    p.add_output_file_type(FileTypes.DATASTORE,
                           "datastore",
                           "JSON Datastore",
                           description="Datastore containing BAM resource",
                           default_name="resources")
    p.add_boolean(Constants.CONSOLIDATE_ID, "consolidate",
        default=False,
        name="Consolidate .bam",
        description="Merge chunked/gathered .bam files")
    p.add_int(Constants.N_FILES_ID, "consolidate_n_files",
        default=1,
        name="Number of .bam files",
        description="Number of .bam files to create in consolidate mode")
    return p


def run_consolidate(dataset_file, output_file, datastore_file,
                    consolidate, n_files, task_id=Constants.TOOL_ID):
    datastore_files = []
    with openDataSet(dataset_file) as ds_in:
        if consolidate:
            if len(ds_in.toExternalFiles()) != 1:
                new_resource_file = op.splitext(output_file)[0] + ".bam"
                ds_in.consolidate(new_resource_file, numFiles=n_files)
            # always display the BAM/BAI if consolidation is enabled
            # XXX there is no uniqueness constraint on the sourceId, but this
            # seems sloppy nonetheless - unfortunately I don't know how else to
            # make view rule whitelisting work
            for ext_res in ds_in.externalResources:
                if ext_res.resourceId.endswith(".bam"):
                    ds_file = DataStoreFile(
                        ext_res.uniqueId,
                        task_id + "-out-2",
                        ext_res.metaType,
                        ext_res.bam)
                    datastore_files.append(ds_file)
                    for index in ext_res.indices:
                        if index.metaType in Constants.BAI_FILE_TYPES:
                            ds_file = DataStoreFile(
                                index.uniqueId,
                                task_id + "-out-3",
                                index.metaType,
                                index.resourceId)
                            datastore_files.append(ds_file)
        ds_in.newUuid()
        ds_in.write(output_file)
    datastore = DataStore(datastore_files)
    datastore.write_json(datastore_file)
    return 0


def args_runner(args, task_id=Constants.TOOL_ID):
    return run_consolidate(
        dataset_file=args.align_in,
        output_file=args.ds_out,
        datastore_file=args.datastore,
        consolidate=args.consolidate,
        n_files=args.consolidate_n_files,
        task_id=task_id)


def rtc_runner(rtc, task_id=Constants.TOOL_ID):
    tempfile.tempdir = rtc.task.tmpdir_resources[0].path
    return run_consolidate(
        dataset_file=rtc.task.input_files[0],
        output_file=rtc.task.output_files[0],
        datastore_file=rtc.task.output_files[1],
        consolidate=rtc.task.options[Constants.CONSOLIDATE_ID],
        n_files=rtc.task.options[Constants.N_FILES_ID],
        task_id=task_id)


def main(argv=sys.argv):
    logging.basicConfig(level=logging.DEBUG)
    log = logging.getLogger()
    return pbparser_runner(argv[1:],
                           get_parser(),
                           args_runner,
                           rtc_runner,
                           log,
                           setup_log)


if __name__ == '__main__':
    sys.exit(main())
