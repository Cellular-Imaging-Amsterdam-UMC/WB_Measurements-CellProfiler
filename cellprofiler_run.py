"""Run the measurements pipeline headless with CellProfiler.

Called with the arguments described in config.yaml (bilayers): by the BIOMERO entrypoint
(wrapper.py) or a bilayers interface. Runs with CellProfiler's own Python (cellprofiler_core).
"""
import argparse
import shutil
import sys
import os
import csv
import tempfile
from subprocess import run
import time
import cellprofiler_core.pipeline
import cellprofiler_core.preferences

cellprofiler_core.preferences.set_headless()

NUCLEI_MASK_KEY = "_Nuclei_Mask"
AGGREGATES_MASK_KEY = "_Aggregates_Mask"
CELLS_MASK_KEY = "_Cells_Mask"

NAMES_AND_TYPES_MODULE_INDEX = 2

MASK_INDICES = {
    14: NUCLEI_MASK_KEY,
    20: AGGREGATES_MASK_KEY,
    32: CELLS_MASK_KEY
}

PARAMETER_SUFFIXES = {
    NUCLEI_MASK_KEY: "nuclei_mask_suffix",
    AGGREGATES_MASK_KEY: "aggregates_mask_suffix",
    CELLS_MASK_KEY: "cells_mask_suffix"
}


def infer_column_type(values):
    """
    Infers the data type of a column based on its values.
    
    Parameters:
    values (list): A list of strings representing the values in a column.
    
    Returns:
    str: A single character representing the inferred data type:
        'd' for DoubleColumn (floating point numbers),
        'l' for LongColumn (integer numbers),
        's' for StringColumn (text),
        'b' for BoolColumn (true/false).
    
    The function determines the type as follows:
        - If all values can be interpreted as booleans ('true' or 'false'), it returns 'b'.
        - If all values can be interpreted as integers, it returns 'l'.
        - If all values can be interpreted as floats, it returns 'd'.
        - Otherwise, it returns 's' for strings.
    
    Note:
    - Empty values are ignored in type determination.
    - The function performs case-insensitive checks for boolean values.
    """
    is_float = True
    is_int = True
    is_bool = True

    for value in values:
        # Handle empty values
        if value == '':
            continue
        
        # Check if value is boolean
        if value.lower() in ('true', 'false'):
            continue
        is_bool = False

        # Check if value is integer
        try:
            int(value)
        except ValueError:
            is_int = False

        # Check if value is float
        try:
            float(value)
        except ValueError:
            is_float = False

    if is_bool:
        return 'b'
    if is_int:
        return 'l'
    if is_float:
        return 'd'
    return 's'


def parse_cellprofiler_parameters(parameters, cppipe, tmpdir):
    """
    Very specific implementation just for this pipeline.

    Here we 'translate' the commandline args from config.yaml to cpppipe text.
    """
    print(vars(parameters), cppipe, tmpdir)

    mod_cppipe = os.path.join(tmpdir, os.path.basename(cppipe))

    # Load the cppipe
    pipeline = cellprofiler_core.pipeline.Pipeline()
    pipeline.load(cppipe)

    # Override mask names in the names_and_types module
    names_and_types_module = pipeline.modules()[NAMES_AND_TYPES_MODULE_INDEX]

    # Loop through mask indices to update the values
    for index, mask_key in MASK_INDICES.items():
        pipeline_value = names_and_types_module.setting(index).get_value()
        param_suffix = getattr(parameters, PARAMETER_SUFFIXES[mask_key])
        new_value = pipeline_value.replace(mask_key, param_suffix)
        print(f"Changing setting at index {index}: {pipeline_value} to {new_value}")
        names_and_types_module.setting(index).set_value(new_value)

    # Check if metric_channels is equal to the default value
    if parameters.metric_channels == '1,2,3':
        print("Skipping channel modification since metric_channels is equal to the default value.")
    else:
        channel_settings = pipeline.modules()[4]  # Assuming channels are in module 4
        metric_channels = [int(ch) for ch in parameters.metric_channels.split(',')] # split list
        num_channels = len(metric_channels) # total amount
        cur_channels = channel_settings.setting(20).get_value() # current configured
        print(f"Number of metric channels from parameters: {num_channels}")
        print(f"Current configured channels: {cur_channels}")
        # First, adjust the number of channels
        if num_channels > cur_channels:
            for _ in range(num_channels - cur_channels):
                channel_settings.add_channel()
            print(f"Added {num_channels - cur_channels} channels.")
        elif num_channels < cur_channels:
            for _ in range(cur_channels - num_channels):
                channel_settings.channels.remove(channel_settings.channels[-1])
            print(f"Removed {cur_channels - num_channels} channels.")
        # Then, set the values of the channels and their names
        images_list = []
        for i, value in enumerate(metric_channels):
            channel = channel_settings.channels[i]
            channel.channel_choice.set_value(value)
            channel_name = f'Channel{value}'
            channel.settings[2].set_value(channel_name)
            print(f"Set channel {i} to value {value} and name to '{channel_name}'.")
            images_list.append(channel_name)
        # Finally, adjust the images selected for measurement in Module MeasureObjectIntensity
        measure_object_intensity = pipeline.modules()[6]
        measure_object_intensity.images_list.set_value(images_list)

    # Save the modified pipeline to a new file
    with open(mod_cppipe, 'w+') as dumpfile:
        pipeline.dump(dumpfile)

    return mod_cppipe


def parse_arguments(argv):
    """The arguments in config.yaml (cli_tag of each input, output and parameter)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--infolder", required=True, help="Folder with the images and their masks")
    parser.add_argument("--outfolder", required=True, help="Folder for the CSV tables")
    parser.add_argument("--nuclei_mask_suffix", default=NUCLEI_MASK_KEY)
    parser.add_argument("--aggregates_mask_suffix", default=AGGREGATES_MASK_KEY)
    parser.add_argument("--cells_mask_suffix", default=CELLS_MASK_KEY)
    parser.add_argument("--metric_channels", default="1,2,3")
    parser.add_argument("--pipeline", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                         "FullMeasurementsNucleiCellAggregates.cppipe"))
    return parser.parse_args(argv)


def main(argv):
    """Starting point for this CellProfiler workflow.

    Args:
        argv: all the given command line arguments

    Raises:
        ValueError: If CellProfiler pipeline failed

    """
    parameters = parse_arguments(argv)
    in_path, out_path = parameters.infolder, parameters.outfolder
    os.makedirs(out_path, exist_ok=True)
    timestamp = int(time.time() * 1000)
    with tempfile.TemporaryDirectory(prefix="cellprofiler-") as tmp_path:
        # ---------------------------------------------------------------- #
        # ------------- RUN CELLPROFILER HEADLESS // START -------------- ##
        # ---------------------------------------------------------------- #
        # Parse the parameters into the pipeline
        mod_pipeline = parse_cellprofiler_parameters(parameters, parameters.pipeline, tmp_path)

        shArgs = [
            "cellprofiler", "-c", "-r", "-p", mod_pipeline,
            "-i", in_path, "-o", out_path, "-t", tmp_path,
        ]
        status = run(shArgs)

        if status.returncode != 0:
            err_desc = "Failed to execute the CellProfiler pipeline: {} (return code: {})".format(
                " ".join(shArgs), status.returncode)
            raise ValueError(err_desc)
        else:
            # Move the modified pipeline file from tmp_path to out_path
            mod_pipeline_basename = os.path.basename(mod_pipeline)
            mod_pipeline_unique_name = f"{mod_pipeline_basename[:-7]}_{timestamp}.cppipe"
            shutil.move(mod_pipeline, os.path.join(out_path, mod_pipeline_unique_name))
        # ---------------------------------------------------------------- #
        # ---------------- RUN CELLPROFILER HEADLESS // END ------------- ##
        # ---------------------------------------------------------------- #

        # ---------------------------------------------------------------- #
        # ----------------- POSTPROCESS CSV // START -------------------- ##
        # ---------------------------------------------------------------- #
        # Get a list of CSV files in the directory
        csv_files = [f for f in os.listdir(out_path) if f.endswith('.csv')]
        # Loop over each CSV file
        for csv_file in csv_files:
            csv_file_path = os.path.join(out_path, csv_file)
            temp_file_path = csv_file_path + '.temp'

            # Read the original CSV content
            with open(csv_file_path, mode='r', newline='') as infile:
                reader = csv.reader(infile)
                _ = next(reader) # skip header
                # Read up to 10 rows for type inference
                data_samples = []
                try:
                    for _ in range(10):
                        row = next(reader)
                        data_samples.append(row)
                except StopIteration:
                    pass  # End of file reached

            # Transpose the data to analyze columns
            transposed_samples = list(zip(*data_samples))
            
            # Infer type hints based on the columns' data
            type_hints = [infer_column_type(column) for column in transposed_samples]
            type_hints[0] = f'# header {type_hints[0]}'

            # Write the updated content to a new temporary file
            with open(temp_file_path, mode='w', newline='') as outfile:
                writer = csv.writer(outfile, delimiter=',')

                # Write the type hint line
                writer.writerow(type_hints)

                # Write the original data from the original CSV
                with open(csv_file_path, mode='r', newline='') as infile:
                    reader = csv.reader(infile)
                    writer.writerows(reader)  # Write remaining rows

            # Replace the original file with the updated file
            os.replace(temp_file_path, csv_file_path)
        # ---------------------------------------------------------------- #
        # ----------------- POSTPROCESS CSV // END ---------------------- ##
        # ---------------------------------------------------------------- #


if __name__ == "__main__":
    main(sys.argv[1:])
