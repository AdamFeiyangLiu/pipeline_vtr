# VTR Pipeline Flow

This project provides a simple pipeline for running the VTR (Verilog-to-Routing) flow.

## Prerequisites

Before running the flow, you must have the VTR toolchain installed and the `VTR_ROOT` environment variable set to your VTR installation path.

```bash
source setup.sh
```

## Project Structure

- `hdl/`: Contains the Verilog source files.
- `arch/`: Contains the VTR architecture description files (XML).
- `scripts/`: Contains the main Python script for the flow.
- `temp/`: Temporary directory for intermediate and output files. Created automatically.
- `Makefile`: For easy execution of the flow.

## Running the Flow

The easiest way to run the flow is by using the `Makefile`.

```bash
make run
```

This will run the complete flow using the default settings specified in the `Makefile`.

### Customizing the Flow

You can customize the input files and parameters by passing variables to the `make` command.

- `HDL`: Path to the Verilog file.
- `ARCH`: Path to the architecture XML file.
- `ROUTE_CHAN_WIDTH`: The routing channel width.

**Example:**

To run the flow with a different Verilog file and architecture file:

1. Place your Verilog file in the `hdl/` directory (e.g., `hdl/my_design.v`).
2. Place your architecture file in the `arch/` directory (e.g., `arch/my_arch.xml`).
3. Run the flow with the following command:

```bash
make run HDL=hdl/my_design.v ARCH=arch/my_arch.xml ROUTE_CHAN_WIDTH=100
```

## Cleaning Up

To remove the temporary files and clean the project directory, run:

```bash
make clean
```
