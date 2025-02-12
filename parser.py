"""
Author: Brian Rojkov
Email: brojkov@uwaterloo.ca

Copyright (c) 2025 Brian Rojkov

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import os
import numpy as np
import struct
import time

class TR0Parser:
  def __init__(self, tr0_file):
    self.file = tr0_file
    self.file_size = os.path.getsize(tr0_file)
    self.mmap = np.memmap(tr0_file, mode='r', order='C')
    
    self.format = None
    self.dtype = None
    self.bytes_per_value = None

    self.block_offsets = []          # Index of first byte in block
    self.block_sizes = []            # Size of data portion of block in bytes
    self.block_data_start_idx = []   # Index to start inserting data

    self.num_vars = None        # Number of variables 
    self.data = None            # Raw data, later reshaped to output data
    self.variables = None       # List of variable names

  def _block_head(self, idx):
    offset = self.block_offsets[idx]
    block_head = self.mmap[offset:offset+16]
    return block_head

  def _block_data(self, idx):
    offset = self.block_offsets[idx] + 16 # Skip header
    size = self.block_sizes[idx]
    return self.mmap[offset:offset+size]
  
  def _count_blocks(self):
    """
    (1) Count the number of blocks in the file
    """
    pos = 0
    while pos < self.file_size:
      block_head = self.mmap[pos:pos+16]
      if len(block_head) < 16:
        break
      data_size = struct.unpack('<i', block_head[12:16])[0]
      self.block_offsets.append(pos)
      self.block_sizes.append(data_size)
      pos += 16 + data_size + 4 # Skip header, data, tail

      # Check for data corruption. Tail contains the number of bytes in the data section and should match block_size
      tail = self.mmap[pos-4:pos]
      data_size_check = struct.unpack('<i', tail)[0]
      if data_size_check != data_size:
        raise ValueError(f'Error: Data corruption at block {len(self.block_offsets)-1}')

  def _translate_name(self, name):
    """
    v(a or v(a) -> v_a
    """
    return name.replace('(', '_').replace(')', '')

  def _parse_header(self):
    """
    (2) Parse the header of the file
    """
    # Extract all header data
    header_data = ''
    header_term_found = False
    while not header_term_found:
      new_header_data = self._block_data(0).tobytes().decode('utf-8')
      self.block_offsets = self.block_offsets[1:] # Skip header block
      self.block_sizes = self.block_sizes[1:] # Skip header block
      header_data += new_header_data
      header_term_found = '$&%#' in new_header_data

    format_part = header_data[:24]
    self.format = '9601' if '9601' in format_part else '2001'
    self.dtype = np.float32 if self.format == '9601' else np.float64
    self.bytes_per_value = 4 if self.format == '9601' else 8

    # Extract variable names
    vars_start = header_data.find('TIME')
    vars_end = header_data.find('$&%#')
    variables = header_data[vars_start:vars_end].split()
    self.variables = [v.strip() for v in variables if v.strip()]
    self.variables = [self._translate_name(v) for v in self.variables]
    self.num_vars = len(self.variables)
    
    header_info = {
      'variables': self.variables,
      'format': self.format
    }

    return header_info

  def _build_empty_data(self):
    """
    (3) Build empty data structure
        Set block start variables and indices
    """
    data_size = sum(self.block_sizes)
    num_values = data_size // self.bytes_per_value
    num_values += (-num_values) % self.num_vars # Ensure num_values is divisible by num_vars

    self.data = np.full(num_values, np.nan, dtype=self.dtype)

    # Set the start index for the NEXT block 
    self.block_data_start_idx = [0]
    for i, block_size in enumerate(self.block_sizes[:-1]):
      block_num_values = block_size // self.bytes_per_value
      if block_num_values % self.bytes_per_value != 0:
        raise ValueError(f'Error: Block size {block_size} is not divisible by bytes per value {self.bytes_per_value}')
      self.block_data_start_idx.append(self.block_data_start_idx[-1] + block_num_values)

  def _parse_block(self, idx):
    """
    (4) Parse block data
    """
    block_data = self._block_data(idx)
    block_vals = np.array(np.frombuffer(block_data, dtype=self.dtype))

    data_idx = self.block_data_start_idx[idx]
    self.data[data_idx:data_idx+len(block_vals)] = block_vals

  def _deinterleave_data(self):
    """
    (5) Deinterleave data
    """
    self.data = np.reshape(self.data, newshape=(self.num_vars, -1), order='F')

  def _cleanup_data(self):
    """
    (6) Remove padding and NaN values. Ensure all data arrays are the same length
    """
    term_val = 1e30 if self.format == '2001' else np.float32(1.0000000150474662e+30)
    shortest_len = len(self.data[0])
    for vals in self.data:
      while np.isnan(vals[shortest_len-1]) or vals[shortest_len-1] == term_val:
        shortest_len -= 1
    self.data = self.data[:,:shortest_len]

  def extract(self):
    t0 = time.time()
    self._count_blocks()
    self._parse_header()
    self._build_empty_data()
    for i in range(len(self.block_sizes)):
      self._parse_block(i)
    self._deinterleave_data()
    self._cleanup_data()
    print(f'TR0Parser parsed {self.file} of {self.file_size / 1000000000:.3f} GB in {time.time() - t0:.2f} s @ {self.file_size / (time.time() - t0) / 1000000000:.2f} GB/s')
    return self.variables, self.data
  
if __name__ == '__main__':
  tr0_file = 'test.tr0'
  parser = TR0Parser(tr0_file)
  vars, vals = parser.extract()

  # Check that 'TIME' is nice and continuous
  try:
    import matplotlib.pyplot as plt
    plt.plot(range(len(vals[0])), vals[0])
    plt.title(vars[0])
    plt.show()
  except ImportError:
    print('matplotlib not installed. Skipping plot')
