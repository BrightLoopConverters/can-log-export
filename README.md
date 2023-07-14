This Python utility is distributed as a project for the PyCharm IDE.

### Data Source Filtering

If the variable `ACCEPT_ALL_DATA_SOURCES` is `True`, then all signals from all messages listed in the DBC file will be extracted from the source file.

However, if `ACCEPT_ALL_DATA_SOURCES` is `False`, then only the signals specified message by message in the `DATA_SOURCES` dictionary will be extracted from the source file.

### Relative Timestamping

If the variable `RELATIVE_TIME` is `True`, then the CAN frames will be timestamped relative to the oldest in the file.

However, if `RELATIVE_TIME` is `False`, then the CAN frames will be timestamped as completely as possible based on the information contained in the source file.