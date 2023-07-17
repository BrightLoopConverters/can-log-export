This Python utility is distributed as a project for the PyCharm IDE.

### Data Source Filtering

If the `DbcFilter` object is constructed by passing `accept_all=True` to its constructor, then all signals from all messages listed in the DBC file will be extracted from the source file.

Conversely, if `accept_all` is `False`, then only signals that are:

 - Individually specified in the dictionary passed via the `partly_accepted` argument will be extracted from the source file.
 - Contained in one of the messages listed via the `fully_accepted` argument.

### Relative Timestamping

If the variable `RELATIVE_TIME` is `True`, then the CAN frames will be timestamped relative to the oldest in the file.

However, if `RELATIVE_TIME` is `False`, then the CAN frames will be timestamped as completely as possible based on the information contained in the source file.
