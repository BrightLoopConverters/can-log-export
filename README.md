## Basic Usage

### 1. Place the Files

- Put the data file (`.blf`, `.trc` or `.asc`) in the `data` folder.
- Put the `.dbc` file in the `dbc` folder.

### 2. Run the Script

- Execute `main.py`.
- This script will generate a `.zip` file containing several `.csv` files.

### 3. Retrieve the Results

- The generated `.csv` files will be located in the `data` subfolder along with the container `.zip` file.

## Advanced Features

### PyCharm Support

This Python utility includes all the necessary files to run it as a project in the PyCharm IDE.

### Data Source Filtering

If the `DbcFilter` object is constructed by passing `accept_all=True` to its constructor, then all signals from all messages listed in the DBC file will be extracted from the source file.

Conversely, if `accept_all` is `False`, then only signals that are:

 - Individually specified in the dictionary passed via the `partly_accepted` argument will be extracted from the source file.
 - Contained in one of the messages listed via the `fully_accepted` argument.

### Relative Timestamping

If the `TimestampRecorder` object used is constructed by passing `use_relative_time=true`, then its `format()` method will timestamp the CAN frames relative to the oldest in the file.

Otherwise, the CAN frames will be timestamped as completely as possible based on the information contained in the source file.
