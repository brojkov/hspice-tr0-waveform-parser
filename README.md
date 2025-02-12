# HSpice Waveform .tr0 parser

Fast. Rips through large .tr0 files at over 900MB/s singlethreaded (AMD EPYC 9554).
Does not support sweeps, though it should not be difficult to add.

I wrote this as a component of a larger framework which generates and runs spice simulations.
Much of the knowledge needed was obtained here: [HMC-ACE/hspiceParser](https://github.com/HMC-ACE/hspiceParser)

## Usage
See the main block for an example.
You can run 'python parser.py' in a directory with a test.tr0 file and it will report the time to parse, and give you a plot of the first variable if you have matplotlib.

**Returns:**
- variables: a list of variable names. These have been snake-cased: {'v(a' or 'v(a)' ==>  'v_a'}
- data: a 2d numpy array with shape (num_variables, num_points)
