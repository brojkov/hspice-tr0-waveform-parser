# HSpice Waveform .tr0 parser

Fast. Rips through large .tr0 files at over 900MB/s singlethreaded (AMD EPYC 9554).
I wrote this as a component of a larger framework which generates and runs spice simulations.

Does not support sweeps, though it should not be difficult to add.
Only supports binary format files. Valid output options:
.OPTION POST=1 POST_VERSION=2001 (Use when you have >9999 output variables. fp64 format)
.OPTION POST=1 POST_VERSION=9601 (Untested as of yet but should work. fp32 format)

## Usage
See the main block for an example.
You can run 'python parser.py' in a directory with a test.tr0 file and it will report the time to parse, and give you a plot of the first variable if you have matplotlib.

**Returns:**
- variables: a list of variable names. These have been snake-cased: {'v(a' or 'v(a)' ==>  'v_a'}
- data: a 2d numpy array with shape (num_variables, num_points)

## Notes
Observations in addition to what is reported in Resources.
- I have seen PrimeSim SPICE output v(a) where HSPICE gives v(a.
- It seems safe to assume that all data blocks are the same size until the last one. This parser does not rely on that assumption: it starts by jumping block to bock until the end of the file, checking each block size individually.

## Future Plans:
**Support files larger than you can realize in memory:**
This should provide an interface to request a list of signals for a range of time.
1. Read the header. Format, variables, etc.
2. Rewrite the file without headers and tails. This step is optional but makes queries much faster. To eliminate the time penalty, do it as the simulation is running.
   - If you want to get fancy about it, cast the fp64 to fp32 and write two copies with no disk space penalty. One with the same interleaved pattern as the tr0 and one deinterleaved.
3. Build a timescale from 'TIME'. The timescale will let you query by time rather than index. You can use np.searchsorted() your timescale to get indices quickly.
4. Performantly extracting values will depend on the shape of the accesses:
   - Short time range, many variables: read from the interleaved data. Pad, reshape, discard.
   - Long time range, few variables: read from the de-interleaved data.

## Resources
- Much of the knowledge needed for this was obtained here [HMC-ACE/hspiceParser](https://github.com/HMC-ACE/hspiceParser)
- More information I found after writing this [l-chang/gwave](https://github.com/l-chang/gwave/blob/slave/doc/hspice.txt)
