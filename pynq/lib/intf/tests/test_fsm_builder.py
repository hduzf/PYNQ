#   Copyright (c) 2016, Xilinx, Inc.
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#
#   1.  Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#
#   2.  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#   3.  Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
#   AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#   THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#   PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
#   CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#   EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#   PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
#   OR BUSINESS INTERRUPTION). HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
#   WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
#   OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#   ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


from random import randint
import numpy as np
import pytest
from pynq import Overlay
from pynq.tests.util import user_answer_yes
from pynq.lib.intf.pattern_builder import bitstring_to_int
from pynq.lib.intf.pattern_builder import wave_to_bitstring
from pynq.lib.intf import FSMBuilder
from pynq.lib.intf import ARDUINO
from pynq.lib.intf import PYNQZ1_DIO_SPECIFICATION
from pynq.lib.intf import MAX_NUM_TRACE_SAMPLES
from pynq.lib.intf import FSM_MIN_STATE_BITS
from pynq.lib.intf import FSM_MAX_STATE_BITS
from pynq.lib.intf import FSM_MIN_NUM_STATES
from pynq.lib.intf import FSM_MAX_NUM_STATES
from pynq.lib.intf import FSM_MIN_INPUT_BITS
from pynq.lib.intf import FSM_MAX_INPUT_BITS
from pynq.lib.intf import FSM_MAX_STATE_INPUT_BITS
from pynq.lib.intf import FSM_MAX_OUTPUT_BITS


__author__ = "Yun Rock Qu"
__copyright__ = "Copyright 2016, Xilinx"
__email__ = "pynq_support@xilinx.com"


try:
    _ = Overlay('interface.bit')
    flag0 = True
except IOError:
    flag0 = False
flag1 = user_answer_yes("\nTest Finite State Machine (FSM) builder?")
if flag1:
    if_id = ARDUINO
flag = flag0 and flag1


@pytest.mark.skipif(not flag, reason="need interface overlay to run")
def test_fsm_builder():
    """Test for the Finite State Machine Builder class.

    The 1st test is doing the following:
    The pattern generated by the FSM will be compared with the one specified.
    fsm_0 will test maximum number of samples.
    
    The 2nd test is similar to the first test, but in this test,
    fsm_1 will test a minimum number of (FSM period + 1) samples. Here the 
    period of the FSM is the same as the number of states.
    
    The 3rd test is similar to the first test, but in this test,
    fsm_2 will test the case when no analyzer is specified.

    The 4th test will check 1 and (MAX_NUM_STATES + 1) states. 
    These cases should raise exceptions. For these tests, we use the minimum 
    number of input and output pins.

    The 5th test will check 2 and MAX_NUM_STATES states. 
    These cases should be able to pass random tests. 
    For these tests, we use the minimum number of input and output pins.

    The 6th test will test when maximum number of inputs and 
    outputs are used. At the same time, the largest available number of 
    states will be implemented. For example, on PYNQ-Z1, if 
    FSM_MAX_INPUT_BITS = 8, and FSM_MAX_STATE_INPUT_BITS = 13, we will 
    implement 2**(13-8) = 32 states. This is the largest number of states 
    available for this setup.

    The 7th test will examine a special scenario where no inputs are given.
    In this case, the FSM is a free running state machine. Since the FSM 
    specification requires at least 1 input pin to be specified,  1 pin can 
    be used as `don't care` input, while all the other pins are used as 
    outputs. A maximum number of states are deployed.

    """
    ol = Overlay('interface.bit')
    ol.download()
    pin_dict = PYNQZ1_DIO_SPECIFICATION['traceable_outputs']
    interface_width = PYNQZ1_DIO_SPECIFICATION['interface_width']

    # Test 1: running at 10MHz
    first_3_pins = [k for k in list(pin_dict.keys())[:3]]
    out = first_3_pins[0]
    rst, direction = first_3_pins[1:3]
    test_string1 = test_string2 = test_string3 = \
        test_string4 = test_string5 = ''
    fsm_spec = {'inputs': [('rst', rst), ('direction', direction)],
                'outputs': [('test', out)],
                'states': ['S0', 'S1', 'S2', 'S3'],
                'transitions': [['00', 'S0', 'S1', '0'],
                                ['01', 'S0', 'S3', '0'],
                                ['00', 'S1', 'S2', '0'],
                                ['01', 'S1', 'S0', '0'],
                                ['00', 'S2', 'S3', '0'],
                                ['01', 'S2', 'S1', '0'],
                                ['00', 'S3', 'S0', '1'],
                                ['01', 'S3', 'S2', '1'],
                                ['1-', '*', 'S0', '']]}
    max_num_samples = MAX_NUM_TRACE_SAMPLES
    period = len(fsm_spec['states'])
    min_num_samples = period + 1
    fsm_0 = FSMBuilder(if_id, fsm_spec,
                       use_analyzer=True,
                       num_analyzer_samples=max_num_samples)

    print("\nConnect {} to GND, and {} to VCC.".format(rst, direction))
          
    input("Hit enter after done ...")

    fsm_0.config(frequency_mhz=10)
    assert 'bram_data_buf' not in fsm_0.intf.buffers, \
        'bram_data_buf is not freed after use.'
    fsm_0.arm()
    fsm_0.start()
    fsm_0.show_waveform()
    fsm_0.stop()

    for wavegroup in fsm_0.waveform.waveform_dict['signal']:
        if wavegroup and wavegroup[0] == 'analysis':
            for wavelane in wavegroup[1:]:
                if wavelane['name'] == 'test':
                    test_string1 = wavelane['wave']
    test_array1 = np.array(bitstring_to_int(wave_to_bitstring(test_string1)))

    tile1 = np.array([1, 0, 0, 0])
    matched = False
    for delay in range(4):
        tile2 = np.roll(tile1, delay)
        candidate_array = np.tile(tile2, int(max_num_samples / 4))
        if np.array_equal(candidate_array[1:], test_array1[1:]):
            matched = True
            break
    assert matched, 'Analysis not matching the generated pattern.'

    # Test 1: running again at 100MHz
    fsm_0.config(frequency_mhz=100)
    assert 'bram_data_buf' not in fsm_0.intf.buffers, \
        'bram_data_buf is not freed after use.'
    fsm_0.arm()
    fsm_0.start()
    fsm_0.show_waveform()
    fsm_0.stop()

    for wavegroup in fsm_0.waveform.waveform_dict['signal']:
        if wavegroup and wavegroup[0] == 'analysis':
            for wavelane in wavegroup[1:]:
                if wavelane['name'] == 'test':
                    test_string2 = wavelane['wave']
    test_array2 = np.array(bitstring_to_int(wave_to_bitstring(test_string2)))

    matched = False
    for delay in range(4):
        tile2 = np.roll(tile1, delay)
        candidate_array = np.tile(tile2, int(max_num_samples / 4))
        if np.array_equal(candidate_array[1:], test_array2[1:]):
            matched = True
            break
    assert matched, 'Analysis not matching the generated pattern.'

    # Test 2: running at 10MHz
    print("Connect both {} and {} to GND.".format(rst, direction))
    
    input("Hit enter after done ...")
    fsm_1 = FSMBuilder(if_id, fsm_spec,
                       use_analyzer=True,
                       use_state_bits=True,
                       num_analyzer_samples=min_num_samples)
    fsm_1.config(frequency_mhz=10)
    fsm_1.arm()
    fsm_1.start()
    fsm_1.show_waveform()
    fsm_1.stop()

    for wavegroup in fsm_1.waveform.waveform_dict['signal']:
        if wavegroup and wavegroup[0] == 'analysis':
            for wavelane in wavegroup[1:]:
                if wavelane['name'] == 'test':
                    test_string3 = wavelane['wave']
                if wavelane['name'] == 'state_bit0':
                    test_string4 = wavelane['wave']
                if wavelane['name'] == 'state_bit1':
                    test_string5 = wavelane['wave']
    test_array3 = np.array(bitstring_to_int(wave_to_bitstring(test_string3)))
    test_array4 = np.array(bitstring_to_int(wave_to_bitstring(test_string4)))
    test_array5 = np.array(bitstring_to_int(wave_to_bitstring(test_string5)))

    tile3 = np.array([0, 0, 0, 1])
    tile4 = np.array([0, 1, 0, 1])
    tile5 = np.array([0, 0, 1, 1])
    matched = False
    for delay in range(period):
        tile6 = np.roll(tile3, delay)
        tile7 = np.roll(tile4, delay)
        tile8 = np.roll(tile5, delay)
        candidate_array3 = np.tile(tile6, 1)
        candidate_array4 = np.tile(tile7, 1)
        candidate_array5 = np.tile(tile8, 1)

        if np.array_equal(candidate_array3, test_array3[1:]):
            assert np.array_equal(candidate_array4, test_array4[1:]), \
                'state_bit0 not synchronized with output.'
            assert np.array_equal(candidate_array5, test_array5[1:]), \
                'state_bit1 not synchronized with output.'
            matched = True
            break
    assert matched, 'Analysis result not matching the generated pattern.'

    # Test 2: running again at 100MHz
    fsm_1.config(frequency_mhz=100)
    fsm_1.arm()
    fsm_1.start()
    fsm_1.show_waveform()
    fsm_1.stop()

    for wavegroup in fsm_1.waveform.waveform_dict['signal']:
        if wavegroup and wavegroup[0] == 'analysis':
            for wavelane in wavegroup[1:]:
                if wavelane['name'] == 'test':
                    test_string3 = wavelane['wave']
                if wavelane['name'] == 'state_bit0':
                    test_string4 = wavelane['wave']
                if wavelane['name'] == 'state_bit1':
                    test_string5 = wavelane['wave']
    test_array3 = np.array(bitstring_to_int(wave_to_bitstring(test_string3)))
    test_array4 = np.array(bitstring_to_int(wave_to_bitstring(test_string4)))
    test_array5 = np.array(bitstring_to_int(wave_to_bitstring(test_string5)))

    matched = False
    for delay in range(period):
        tile6 = np.roll(tile3, delay)
        tile7 = np.roll(tile4, delay)
        tile8 = np.roll(tile5, delay)
        candidate_array3 = np.tile(tile6, 1)
        candidate_array4 = np.tile(tile7, 1)
        candidate_array5 = np.tile(tile8, 1)

        if np.array_equal(candidate_array3, test_array3[1:]):
            assert np.array_equal(candidate_array4, test_array4[1:]), \
                'state_bit0 not synchronized with output.'
            assert np.array_equal(candidate_array5, test_array5[1:]), \
                'state_bit1 not synchronized with output.'
            matched = True
            break
    assert matched, 'Analysis result not matching the trace-only pattern.'

    # Test 3
    fsm_2 = FSMBuilder(if_id, fsm_spec, use_analyzer=False)
    exception_raised = False
    try:
        fsm_2.show_waveform()
    except ValueError:
        exception_raised = True
    assert exception_raised, 'Should raise exception for show_waveform().'

    fsm_0.intf.reset_buffers()
    fsm_1.intf.reset_buffers()
    fsm_2.intf.reset_buffers()
    del fsm_0, fsm_1, fsm_2

    # Test 4: test a single state
    input_pin = list(pin_dict.keys())[0]
    output_pin = list(pin_dict.keys())[1]

    exception_raised = False
    fsm_0 = None
    try:
        fsm_spec_state = {'inputs': [('rst', input_pin)],
                          'outputs': [('test', output_pin)],
                          'states': ['S0'],
                          'transitions': [['1', '*', 'S0', '']]}
        max_num_samples = MAX_NUM_TRACE_SAMPLES
        fsm_0 = FSMBuilder(if_id, fsm_spec_state,
                           use_analyzer=True,
                           num_analyzer_samples=max_num_samples)
        fsm_0.config(frequency_mhz=10)
        fsm_0.arm()
        fsm_0.start()
        fsm_0.show_waveform()
        fsm_0.stop()
    except ValueError:
        exception_raised = True
    finally:
        if fsm_0:
            fsm_0.intf.reset_buffers()
            del fsm_0
    assert exception_raised, 'Should raise exception for less than ' \
                             '{} states.'.format(FSM_MIN_NUM_STATES)

    # Test 4: test more than the maximum number of states
    exception_raised = False
    fsm_0 = None
    try:
        fsm_spec_state = {'inputs': [('rst', input_pin)],
                          'outputs': [('test', output_pin)],
                          'states': [],
                          'transitions': [['1', '*', 'S0', '']]}
        for i in range(FSM_MAX_NUM_STATES+1):
            current_state = 'S{}'.format(i)
            next_state = 'S{}'.format((i+1)%(FSM_MAX_NUM_STATES+1))
            fsm_spec_state['states'].append(current_state)
            output_pattern = '{}'.format(randint(0,1))
            transition = ['0', current_state, next_state, output_pattern]
            fsm_spec_state['transitions'].append(transition)
        fsm_0 = FSMBuilder(if_id, fsm_spec_state,
                           use_analyzer=True,
                           num_analyzer_samples=MAX_NUM_TRACE_SAMPLES)
        fsm_0.config(frequency_mhz=10)
        fsm_0.arm()
        fsm_0.start()
        fsm_0.show_waveform()
        fsm_0.stop()
    except ValueError:
        exception_raised = True
    finally:
        if fsm_0:
            fsm_0.intf.reset_buffers()
            del fsm_0
    assert exception_raised, 'Should raise exception for more than ' \
                             '{} states.'.format(FSM_MAX_NUM_STATES)

    # Test 5: test two or maximum number of states
    input_pin = list(pin_dict.keys())[0]
    output_pin = list(pin_dict.keys())[1]

    print("Connect {} to GND, and disconnect "
          "other pins.".format(input_pin))
    input("Hit enter after done ...")

    for num_states in [2, FSM_MAX_NUM_STATES]:
        fsm_spec_state = {'inputs': [('rst', input_pin)],
                          'outputs': [('test', output_pin)],
                          'states': [],
                          'transitions': [['1', '*', 'S0', '']]}
        test_pattern = []
        for i in range(num_states):
            current_state = 'S{}'.format(i)
            next_state = 'S{}'.format((i+1)% num_states)
            fsm_spec_state['states'].append(current_state)
            output_pattern = '{}'.format(randint(0,1))
            transition = ['0', current_state, next_state, output_pattern]
            fsm_spec_state['transitions'].append(transition)
            test_pattern.append(int(output_pattern))

        fsm_0 = FSMBuilder(if_id, fsm_spec_state,
                           use_analyzer=True,
                           num_analyzer_samples=MAX_NUM_TRACE_SAMPLES)
        fsm_0.config(frequency_mhz=10)
        fsm_0.arm()
        fsm_0.start()
        fsm_0.show_waveform()
        fsm_0.stop()

        test_string1 = ''
        for wavegroup in fsm_0.waveform.waveform_dict['signal']:
            if wavegroup and wavegroup[0] == 'analysis':
                for wavelane in wavegroup[1:]:
                    if wavelane['name'] == 'test':
                        test_string1 = wavelane['wave']
        test_array1 = np.array(bitstring_to_int(
                        wave_to_bitstring(test_string1)))

        period = len(test_pattern)
        tile1 = np.array(test_pattern)

        max_num_samples = MAX_NUM_TRACE_SAMPLES
        matched = False
        for delay in range(period):
            tile2 = np.roll(tile1, delay)
            candidate_array = np.tile(tile2, int(max_num_samples / period))
            if np.array_equal(candidate_array[1:], test_array1[1:]):
                matched = True
                break
        assert matched, 'Analysis not matching the generated pattern.'

        fsm_0.intf.reset_buffers()
        del fsm_0

    # Test 6: test maximum number of inputs and outputs
    all_pins = list(pin_dict.keys())[:interface_width]
    input_pins = all_pins[:FSM_MAX_INPUT_BITS]
    output_pins = all_pins[FSM_MAX_INPUT_BITS:]

    print("Connect {} to GND.".format(input_pins))
    print("Disconnect all other pins.")
    input("Hit enter after done ...")
    fsm_spec_inout = {'inputs': [],
                      'outputs': [],
                      'states': [],
                      'transitions': [['1'*len(input_pins), '*', 'S0', '']]}
    test_lanes = [[] for _ in range(len(output_pins))]
    num_states = 2**(FSM_MAX_STATE_INPUT_BITS - FSM_MAX_INPUT_BITS)
    # prepare the input pins
    for i in range(len(input_pins)):
        fsm_spec_inout['inputs'].append(('input{}'.format(i),
                                         input_pins[i]))

    # prepare the output pins
    for i in range(len(output_pins)):
        fsm_spec_inout['outputs'].append(('output{}'.format(i),
                                          output_pins[i]))

    # prepare the states and transitions
    for i in range(num_states):
        current_state = 'S{}'.format(i)
        next_state = 'S{}'.format((i+1)% num_states)
        fsm_spec_inout['states'].append(current_state)
        output_pattern = ''
        for test_lane in test_lanes:
            random_1bit = '{}'.format(randint(0,1))
            output_pattern += random_1bit
            test_lane += random_1bit
        transition = ['0'*len(input_pins), current_state, next_state,
                      output_pattern]
        fsm_spec_inout['transitions'].append(transition)

    fsm_0 = FSMBuilder(if_id, fsm_spec_inout,
                       use_analyzer=True,
                       num_analyzer_samples=MAX_NUM_TRACE_SAMPLES)
    fsm_0.config(frequency_mhz=10)
    fsm_0.arm()
    fsm_0.start()
    fsm_0.show_waveform()
    fsm_0.stop()

    test_patterns = []
    for i in range(len(output_pins)):
        temp_string = ''.join(test_lanes[i])
        test_patterns.append(np.array(bitstring_to_int(
            wave_to_bitstring(temp_string))))

    test_strings = ['' for _ in range(len(output_pins))]
    test_arrays = [[] for _ in range(len(output_pins))]
    for wavegroup in fsm_0.waveform.waveform_dict['signal']:
        if wavegroup and wavegroup[0] == 'analysis':
            for wavelane in wavegroup[1:]:
                for j in range(len(output_pins)):
                    if wavelane['name'] == 'output{}'.format(j):
                        test_strings[j] = wavelane['wave']
                        test_arrays[j] = np.array(bitstring_to_int(
                                        wave_to_bitstring(test_strings[j])))
                        break

    period = num_states
    max_num_samples = MAX_NUM_TRACE_SAMPLES
    matched = False
    tiles = [[] for _ in range(len(output_pins))]
    candidate_arrays = [[] for _ in range(len(output_pins))]
    for delay in range(period):
        for i in range(len(output_pins)):
            tiles[i] = np.roll(test_patterns[i], delay)
            candidate_arrays[i] = np.tile(tiles[i],
                                          int(max_num_samples / period))

        if np.array_equal(candidate_arrays[0][1:], test_arrays[0][1:]):
            for i in range(1, len(output_pins)):
                assert np.array_equal(candidate_arrays[i][1:],
                                      test_arrays[i][1:]), \
                    'output{} not synchronized with other outputs.'.format(i)
            matched = True
            break
    assert matched, 'Analysis not matching the generated pattern.'

    fsm_0.intf.reset_buffers()
    del fsm_0

    # Test 7: 1 don't care input
    all_pins = list(pin_dict.keys())[:interface_width]
    input_pin = all_pins[0]
    output_pins = all_pins[1:]

    print("Disconnect all the pins.")
    input("Hit enter after done ...")
    fsm_spec_inout = {'inputs': [],
                      'outputs': [],
                      'states': [],
                      'transitions': []}
    test_lanes = [[] for _ in range(len(output_pins))]
    num_states = 2 ** FSM_MAX_STATE_BITS
    # prepare the input pins
    fsm_spec_inout['inputs'].append(('input0', input_pin))

    # prepare the output pins
    for i in range(len(output_pins)):
        fsm_spec_inout['outputs'].append(('output{}'.format(i), 
                                          output_pins[i]))

    # prepare the states and transitions
    for i in range(num_states):
        current_state = 'S{}'.format(i)
        next_state = 'S{}'.format((i+1)% num_states)
        fsm_spec_inout['states'].append(current_state)
        output_pattern = ''
        for test_lane in test_lanes:
            random_1bit = '{}'.format(randint(0,1))
            output_pattern += random_1bit
            test_lane += random_1bit
        transition = ['-', current_state, next_state, output_pattern]
        fsm_spec_inout['transitions'].append(transition)

    period = num_states
    fsm_0 = FSMBuilder(if_id, fsm_spec_inout,
                       use_analyzer=True,
                       num_analyzer_samples=period)
    fsm_0.config(frequency_mhz=100)
    fsm_0.arm()
    fsm_0.start()
    fsm_0.show_waveform()
    fsm_0.stop()

    test_patterns = []
    for i in range(len(output_pins)):
        temp_string = ''.join(test_lanes[i])
        test_patterns.append(np.array(bitstring_to_int(
            wave_to_bitstring(temp_string))))

    test_strings = ['' for _ in range(len(output_pins))]
    test_arrays = [[] for _ in range(len(output_pins))]
    for wavegroup in fsm_0.waveform.waveform_dict['signal']:
        if wavegroup and wavegroup[0] == 'analysis':
            for wavelane in wavegroup[1:]:
                for j in range(len(output_pins)):
                    if wavelane['name'] == 'output{}'.format(j):
                        test_strings[j] = wavelane['wave']
                        test_arrays[j] = np.array(bitstring_to_int(
                            wave_to_bitstring(test_strings[j])))
                        break

    matched = False
    tiles = [[] for _ in range(len(output_pins))]
    candidate_arrays = [[] for _ in range(len(output_pins))]
    for delay in range(period):
        for i in range(len(output_pins)):
            tiles[i] = np.roll(test_patterns[i], delay)
            candidate_arrays[i] = np.tile(tiles[i], 1)

        if np.array_equal(candidate_arrays[0][1:], test_arrays[0][1:]):
            for i in range(1, len(output_pins)):
                assert np.array_equal(candidate_arrays[i][1:],
                                      test_arrays[i][1:]), \
                    'output{} not synchronized with other outputs.'.format(i)
            matched = True
            break
    assert matched, 'Analysis not matching the generated pattern.'

    fsm_0.intf.reset_buffers()
    del fsm_0

    # All the tests are finished
    ol.reset()
