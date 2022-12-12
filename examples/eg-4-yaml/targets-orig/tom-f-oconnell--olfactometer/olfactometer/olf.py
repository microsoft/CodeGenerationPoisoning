"""
Core functions to run experiments on the olfactometer. Also functions for top-level
config handling and communication with the firmware.
"""

import binascii
from datetime import datetime, timedelta
import glob
import importlib.util
import os
from os.path import split, join, exists, isdir, splitext, isfile
from pprint import pprint
import time
import warnings
from typing import Dict, Any

import serial
import pyperclip
import yaml
# TODO try to find a way of accessing this type without any prefix '_'s
from google.protobuf.internal.encoder import _VarintBytes

from olfactometer import config_io, util, upload, validation, flow
from olfactometer.generators import common, basic, pair_concentration_grid
from olfactometer import IN_DOCKER, _DEBUG


# TODO TODO (a bit hacky, but...) maybe i could atexit make a new connection to the same
# port to reset the Arduino? assuming it does reset on serial connection initiation, and
# there isn't some other call i could be making to signal to the arduino similarly, in a
# way that wouldn't require making a connection with no intention of using it

# TODO implement preprocessing of config from intermediate (dict probably? yaml
# and json loaders can be configured to give comprable output?) to infer keys
# that aren't really necessary (like pinGroups / pins) (and maybe allow 'pins'
# to be used in place of pinSequence? could be a mess for maintainability
# though...
# TODO maybe try nesting the PinGroup object into the other message type, and
# see if that changes the json syntax? (would have to adapt C code a bit though,
# AND might prevent nanopb from optimizing as much from the *.options)
# TODO and also probably allow seconds / ms units for PulseTiming fields
# (already have some of this stuff in generator stuff, though not sure if i want
# to also expose it here...)

# TODO depending on how i check for the 'generator' tag in the config, if i'm
# still going to use that, might want to validate json and yaml equally to check
# they don't have that tag, if in docker, since what that would trigger
# currently wouldn't work in docker (since can't write files, as-is)

# TODO TODO also have python parse the "trial: <n>, pins(s): ..." messages from
# arduino (when sent?) and check that timing is at least roughly right, in the
# pulse timing case


# TODO use elsewhere / check I'm only ever using str as (top-level) keys
# Replace with TypeAlias if I ever switch to python >= 3.10
ConfigDict = Dict[str, Any]


# Using an 8 bit, unsigned type to represent this on the Arduino side.
MAX_MSG_NUM = 255
curr_msg_num = 0
def write_message(ser, msg, verbose=False, use_message_nums=True,
    arduino_debug_prints=True, ignore_ack=False):
    """
    Args:
    ser (serial.Serial): serial device to receive the message

    msg (protobuf generated class): must have a `SerializeToString` method

    use_message_nums (bool, default=True): matches the USE_MESSAGE_NUMS
        preprocessor flag in the sketch. will number messages so the Arduino
        side can check it is not missing any.

    arduino_debug_prints (bool, default=False): if True, reads all bytes in
        buffer before writing message num, to try to ensure the next byte we
        get back is just the message num.
    """
    # Since we are updating it in here, this is required.
    global curr_msg_num

    serialized = msg.SerializeToString()
    assert type(serialized) is bytes

    # TODO check this calculation is still correct for stuff with "repeated"
    # things in them
    # https://www.datadoghq.com/blog/engineering/protobuf-parsing-in-python/
    size = len(serialized)
    varint_size = _VarintBytes(size)

    def print_bytes(bs):
        s = bs.hex()
        print(' '.join([a+b for a,b in zip(s[::2], s[1::2])]))

    def write_bytes(bs):
        assert type(bs) is bytes
        n_bytes_written = ser.write(bs)
        assert n_bytes_written == len(bs)

    def crc16_0x1021(bs):
        # This uses polynomial 0x1021 (same as what I'm using on Arduino side)
        crc = binascii.crc_hqx(varint_size + serialized, 0xFFFF)

        # TODO also check input size (...why?) / that output of crc *should* fit
        # into 2 bytes?

        # This 'big' [Endian] byte order works for comparing on Arduino side,
        # with current code there.
        crc_bytes = crc.to_bytes(2, 'big')
        assert type(crc_bytes) is bytes and len(crc_bytes) == 2
        return crc_bytes

    # TODO add unit tests where random parts of data and / or crc are changed
    # (after crc calculation, but before sending) (-> verify failure)
    crc_bytes = crc16_0x1021(varint_size + serialized)

    '''
    if verbose:
        print('size: ', end='')
        print_bytes(varint_size)
        print('serialized: ', end='')
        print_bytes(serialized)
    '''

    n_bytes = len(varint_size) + len(serialized) + 2
    if use_message_nums:
        n_bytes += 1

    if verbose:
        print(f'writing {n_bytes} bytes to arduino...', flush=True, end='')

    # TODO TODO TODO need to check we don't write more than arduino's buffer
    # size (until acked)? just 64 bytes, right? assert to fail if single
    # messages exceed? or what? can't just ack at end of message then, if i
    # really need ack's to tell python it's ok to send more of one message...
    # SEEMS SO!!!

    # TODO how to get it to fail in this case / wait for other bytes for
    # decoding? (it currently does, w/ delimited, but add unit tests for both
    # under and over size)
    #write_bytes(serialized[:12])

    write_bytes(varint_size)
    write_bytes(serialized)
    write_bytes(crc_bytes)

    if use_message_nums:
        # TODO maybe do this between write and flush? does that guarantee it
        # won't be flushed earlier (probably not...)? (didn't seem to work there
        # anyway... though ser.out_waiting was zero all around it...)
        # This doesn't seem sufficient to prevent other prints from the Arduino
        # from obscuring the byte we want...
        if not ignore_ack and arduino_debug_prints:
            # TODO now that this is working with this hack, maybe delete
            # ignore_ack option?

            # At 115200 baud, seems we need to sleep at least about this long
            # for the any previous debug prints to all arrive. This is with an
            # Arduino-side flush right before the Arduino read for curr_msg_num
            # below. 0.005 did not work. Tested on Ubuntu 18.04 w/ USB3 port and
            # Arduino Mega.
            # TODO figure out fix that does not involve sleeping...
            time.sleep(0.008)
            n_input_bytes_discarded = ser.in_waiting
            # TODO maybe actually read them and format as below?
            ser.reset_input_buffer()

        # TODO this is unsigned if positive? arduino agrees on value for whole 8
        # bit range?
        before_sending_msg_num = time.time()
        write_bytes(curr_msg_num.to_bytes(1, 'big'))
        ser.flush()

        if not ignore_ack:
            # TODO should i just block for acknowledgement here, or make some
            # non-blocking interface?

            # TODO maybe keep track of times-to-ack, and maybe save as
            # experiment data even

            # Since the read has a timeout (not changeable by parameters to
            # read, it seems), we need to loop until we get the byte we want.
            while True:
                # TODO implement some timeout where we assume, beyond that, that
                # the arduino is in an error state? or otherwise, should i have
                # the arduino send a separate message with that state? maybe
                # before discussing msg num with it?
                arduino_msg_num_byte = ser.read()
                if len(arduino_msg_num_byte) > 0:
                    break

            time_to_msgnum_ack = time.time() - before_sending_msg_num

            arduino_msg_num = int.from_bytes(arduino_msg_num_byte, 'big')
            if arduino_msg_num != curr_msg_num:
                raise RuntimeError('arduino sent wrong message num. '
                    f'expected {curr_msg_num}, got {arduino_msg_num}.'
                )

        # TODO test wraparound behavior (+ w/ arduino)
        curr_msg_num = (curr_msg_num + 1) % MAX_MSG_NUM
    else:
        ser.flush()

    if verbose:
        print(' done')
        if use_message_nums and not ignore_ack:
            if arduino_debug_prints and n_input_bytes_discarded > 0:
                print(f'Discarded {n_input_bytes_discarded} bytes in input '
                    'buffer (before sending msg num)'
                )
            print(f'Time to msg num ack: {time_to_msgnum_ack:.3f}')


# TODO rename to preprocess_config_if_need or something
# TODO create accurate type hint for `config` (it can be more than just ConfigDict...)
def check_need_to_preprocess_config(config, hardware_config=None, verbose=False):
    # TODO update doc to indicate directory case if i'm going to support that
    """Returns input or new pre-processed config, if it input requests it.

    If a line like 'generator: <generator-py-file-prefix>' is in the YAML file
    `olfactometer/generators/<generator-py-file-prefix>.py:make_config_dict`
    will be used to pre-process the input YAML into a YAML that can be used
    directly to control a stimulus program.

    See `load_hardware_config` for meaning of `hardware_config` argument.
    """
    # We need to save the generated YAML in this case, because otherwise we
    # would lose metadata crucial for analyzing corresponding data, and I
    # haven't yet figured out a way to do it in Docker (options seem to
    # exist, but I'd need to provide instructions, test it, etc). So for
    # now, I'm just not supporting this case. Could manually run generators
    # in advance (maybe provide instructions for that? or **maybe** have
    # that be the norm?)
    if IN_DOCKER:
        # TODO after refactoring main/run to work with w/ `dict` config input
        # (rather than just files), could probably relax this restriction, and
        # just use a `dict` in docker case (there is still the issue of not
        # being able to save generated outputs, but perhaps that error should be
        # triggered in the function that would do that)

        # We can't read it to check, because that would read to end of stdin,
        # which is the input in that case. Would need to do some other trick,
        # which would probably require some light refactoring.
        warnings.warn('not checking for need to pre-process config, because not'
            ' currently supported from Dockerized deployment'
        )
        return config

    # It should be a path to a .json/.yaml config file in this case.
    if type(config) is str:
        # TODO refactor so json case isn't left out from generator handling
        # (or just drop json support, which might make more sense...)
        if config.endswith('.json'):
            warnings.warn('not checking for need to pre-process config, '
                'because not currently support in the JSON input case'
            )
            return config

        # Not making an error here just to avoid duplicating validation in input
        # done in load(...)
        if not config.endswith('.yaml'):
            return config

        # TODO so that i don't need to worry about preventing these errors if
        # the yaml has equivalent data, just always err if one of these things
        # is set and the config tries to override it? (which errors/things?)

        with open(config, 'r') as f:
            generator_yaml_dict = yaml.safe_load(f)

    elif type(config) is dict:
        generator_yaml_dict = config

    elif config is None:
        raise NotImplementedError

    else:
        # TODO TODO refactor all this config type validation to one fn to
        # generate this [type of] error
        raise ValueError('config type not recognized')

    # TODO TODO provide way of listing available generators and certain
    # documentation about each, like required[/optional] keys, what each does,
    # as well as maybe printing docstring for each?

    # This means that the protobuf message(s) we define will cause problems if
    # it ever also would correspond to YAML/JSON with this 'generator' key at
    # the same level.
    if 'generator' not in generator_yaml_dict:
        # Intentionally not erring in the case where the default is set, because
        # that would be too annoying. Currently just silently doing nothing (in
        # here) if no generator and if the only indication we should use the
        # hardware config is the default specified in that env var.
        if hardware_config is not None:
            raise ValueError('hardware_config only valid if using a generator '
                "(specified via 'generator: <generator-name>' line in YAML "
                'config)'
            )

        return config

    if verbose:
        print('generator_yaml_dict:')
        pprint(generator_yaml_dict)
        print()

    # Now assuming that if we are using a generator, we also must be using a separate
    # hardware configuration.

    hardware_yaml_dict = config_io.load_hardware_config(hardware_config)

    # TODO why is this not just in the generator.common fn that is supposed to
    # validate hardware config dicts?
    #
    # assumes all hardware specific keys can be detected at the top level
    # (so far the case, i believe, at least for expected inputs to
    # preprocessors)
    if any([k in common.hardware_specific_keys for k in generator_yaml_dict
        ]):
        # so that there is no ambiguity as to which should take precedence
        # TODO maybe actually embed path to offending config in this case
        raise ValueError('some of hardware_specific_keys='
            f'{common.hardware_specific_keys} are defined in config. '
            'this is invalid when hardware_config is specified.'
        )

    if verbose:
        print('hardware_yaml_dict:')
        pprint(hardware_yaml_dict)
        print()

    generator_yaml_dict.update(hardware_yaml_dict)

    generator = generator_yaml_dict['generator']

    # TODO enumerate modules under generators/ that have a make_config_dict fn?
    if generator == 'basic':
        generator_fn = basic.make_config_dict

    elif generator == 'pair_concentration_grid':
        generator_fn = pair_concentration_grid.make_config_dict

    elif generator.endswith('.py'):

        spec = importlib.util.spec_from_file_location('generator', generator)
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)

        generator_fn = generator.make_config_dict

    else:
        raise NotImplementedError(f"generator '{generator}' not supported")

    # TODO TODO TODO add something like 'generated_from: <input YAML name>' to outputs
    # YAML, so analysis can group stuff that was randomized from the same input data
    # (assuming the file hadn't changed at least...)
    # TODO maybe also w/ commit hash of any containing repo, if it tracks the file?
    # probably not worth the extra complication, esp. if including handling for
    # non-committed stuff...

    # TODO maybe just pprint the dict? or don't print this line at all in that
    # case?
    config_str = config if type(config) is str else 'passed dict'
    print(f"Using the '{generator}' generator configured with "
        f"{config_str}"
    )
    # Output will be either a dict or a list of dicts. In the latter case,
    # each should be written to their own YAML file.
    generated_config = generator_fn(generator_yaml_dict)

    # TODO refactor so addresses can also be used w/o generators
    if flow.safe_usb_ids_key in hardware_yaml_dict:
        safe_vid_pid_pairs = hardware_yaml_dict[flow.safe_usb_ids_key]

        # TODO move to hardware config validation
        for pair in safe_vid_pid_pairs:
            assert len(pair) == 2
            for x in pair:
                assert type(x) is int

        flow.safe_usb_ids_to_check_for_mfcs = {tuple(p) for p in safe_vid_pid_pairs}

        if _DEBUG:
            print('USB (vid, pid) whitelist, to allow searching for MFCs:')
            pprint(flow.safe_usb_ids_to_check_for_mfcs)

    # TODO if i ever refactor "generators" to OOP rather than mostly independent
    # make_config_dict fns, include this as a default step that happens after pinlist is
    # populated
    try:
        generated_config = flow.generate_flow_setpoint_sequence(generator_yaml_dict,
            hardware_yaml_dict, generated_config
        )

    except flow.FlowHardwareNotConfiguredError as err:
        if generator_yaml_dict.get('require_flow_controllers', False):
            raise
        else:
            # TODO test formatting is what i want
            warnings.warn(str(err))

    save_generator_output = generator_yaml_dict.get(
        'save_generator_output', True
    )
    if not save_generator_output:
        if type(generated_config) is dict:
            # TODO maybe a less jargony message here?
            warnings.warn("not saving generator output (because "
                "'save_generator_output: False' in config)!"
            )
            return generated_config
        else:
            raise ValueError("save_generator_output must be True (the default) "
                'in case where generator produces a sequence of configuration '
                'files'
            )

    # TODO probably want to save the config + version of the code in the
    # case when a generator isn't used regardless (or at least have the
    # option to do so...) (not sure i do want this...)
    # TODO might want to use a zipfile to include the extra generator
    # information in that case. or just always a zipfile then for
    # consistency?

    # TODO TODO allow configuration of path these are saved at? at CLI, in
    # yaml, env var, or where? default to `generated_stimulus_configs` or
    # something, if not just zipping with other stuff, then maybe call it
    # something else?

    # TODO probably want to save generator_yaml_dict (and generator too, if
    # user defined...)? maybe as part of a zip file? or copy alongside w/
    # diff suffix or something?
    # (though aren't keys from that in generated yaml anyway? or no?)

    # TODO might want to refactor so this function can also just return the
    # file contents it just wrote (to not need to re-read them), but then
    # again, that's probably pretty trivial...

    # TODO should i be using safe_dump instead? (modify SafeDumper instead
    # of Dumper if so)
    # So that there are not aliases (references) within the generated YAML
    # (they make it less readable).
    # https://stackoverflow.com/questions/13518819
    yaml.Dumper.ignore_aliases = lambda *args : True

    # TODO what is default_style kwarg to pyyaml dump? docs don't seem to
    # say...
    # TODO maybe i want to make a custom dumper that just uses this style
    # for pin groups though? right now it's pretty ugly when everything is
    # using this style...
    # Setting this to True would make lists single-line by default, which I
    # want for terminal stuff, but I don't like what this flow style does
    # elsewhere.
    default_flow_style = False

    # TODO maybe refactor two branches of this conditional to share a bit
    # more code?
    if type(generated_config) is dict:
        yaml_dict = generated_config

        generated_yaml_fname = datetime.now().strftime('%Y%m%d_%H%M%S_stimuli.yaml')
        print(f'Writing generated YAML to {generated_yaml_fname}')
        assert not exists(generated_yaml_fname)
        with open(generated_yaml_fname, 'w') as f:
            yaml.dump(yaml_dict, f, default_flow_style=default_flow_style)
        print()

        return generated_yaml_fname

    # TODO what type(s) is/are generated_config here? a list of dicts, right?
    else:
        # TODO TODO TODO squeeze list to single element if only one file would be in dir

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        generated_config_dir = timestamp_str + '_stimuli'
        # TODO maybe also print each filename that is saved?
        print(f'Writing generated YAML under ./{generated_config_dir}/')
        assert not exists(generated_config_dir)
        os.mkdir(generated_config_dir)

        for i, yaml_dict in enumerate(generated_config):
            assert type(yaml_dict) is dict
            generated_yaml_fname = join(
                generated_config_dir, f'{timestamp_str}_stimuli_{i}.yaml'
            )
            assert not exists(generated_yaml_fname)
            with open(generated_yaml_fname, 'w') as f:
                yaml.dump(yaml_dict, f, default_flow_style=default_flow_style)

        del generated_yaml_fname
        print()

        # TODO test this case (as well as previous branch of this
        # conditional)
        return generated_config_dir


# TODO TODO maybe add a block=True flag to allow (w/ =False) to return, to not
# need to start this function in a new thread or process when trying to run the
# olfactometer and other code from one python script. not needed as a command
# line arg, cause already a separate process at that point.
# (or would this just make debugging harder, w/o prints from arduino?)
# TODO TODO make sure version_mismatch checks that installed version is the used
# version, if/when doing things that way (e.g. catch the case where the version
# of util.py from the cwd, if cwd=~/src/olfactometer) has changes not reflected
# in the version of the installed `olf` script)
baud_rate = None
def run(config, port=None, fqbn=None, do_upload=False, timeout_s=2.0,
    pause_before_start=True, check_set_flows=False, allow_version_mismatch=False,
    ignore_ack=False, try_parse=False, speed_factor=None, verbose=False,
    _first_run=True):
    """Runs a single configuration file on the olfactometer.

    Args:
    config (str|dict|None): path to YAML or JSON file with settings
        defining the olfactometer behavior. If `None` is passed, the config is
        read from stdin.
    """
    global curr_msg_num
    global baud_rate
    # We want to reset this at the beginning of each run of a single config
    # file. If there are multiple, the Arduino sketch should reset between them.
    curr_msg_num = 0

    # TODO rename all_required_data to indicate it is the protobuf message(s)?
    all_required_data, config_dict = config_io.load(config)

    if speed_factor is not None:
        warnings.warn('speeding up valve off periods by a factor of '
            f'{speed_factor} for testing faster'
        )
        timing = all_required_data.settings.timing
        timing.pre_pulse_us = int(round(timing.pre_pulse_us / speed_factor))
        timing.pulse_us = int(round(timing.pulse_us / speed_factor))
        timing.post_pulse_us = int(round(timing.post_pulse_us / speed_factor))

        timing.pulse_train_on_us = int(round(timing.pulse_train_on_us / speed_factor))
        timing.pulse_train_off_us = int(round(timing.pulse_train_off_us / speed_factor))

    settings = all_required_data.settings
    pin_sequence = all_required_data.pin_sequence

    # TODO i thought there wasn't optional stuff? so how come it doesn't fail
    # w/o balance_pin, etc passed? (it also doesn't print them, which i might
    # expect if they just defaulted to 0...) idk...
    # (if defaults to 0, remove my reimplementation of that logic in basic
    # generator)

    # TODO especially if i print the YAML name before each in a sequence (when
    # running a sequence of YAML files), also print it here
    if verbose or try_parse:
        print('Config data used by microcontroller:')
        print(all_required_data)
        # Stuff that would be behind the 'settings' / 'pin_sequence' keys should
        # be printed in the line above.
        extra_config = {k: v for k, v in config_dict.items()
            if k not in ('settings', 'pin_sequence')
        }
        # TODO maybe print this circa check_need_to_preprocess... call, to also
        # print 'generator:', and other keys that might not make it to generator
        # output? or i guess it's fine here as long as most keys (just
        # 'generator' and maybe a couple other specific exceptions) are just
        # transferred directly to generator output (by default)....
        # (or print the stuff that doesn't make it to this, in that case, and if
        # verbose / try_parse?)
        if len(extra_config) > 0:
            print('Additional config data:')
            pprint(extra_config)

    # TODO TODO make the function named `validate` work on config_dict, and
    # rename current `validate` to something more specific, indicating it should
    # be used w/ the AllRequiredData object (the settings that get communicated
    # to the firmware)
    warn = True
    validation.validate_config_dict(config_dict, warn=warn)
    validation.validate_protobuf(all_required_data, warn=warn)

    if check_set_flows and flow.flow_setpoints_sequence_key not in config_dict:
        raise ValueError('check_set_flows=True only valid if '
            f'{flow.flow_setpoints_sequence_key} is appropriately populated in '
            'config'
        )

    if try_parse:
        return

    if check_set_flows:
        # TODO maybe just err if not _DEBUG then?
        warnings.warn('check_set_flows should only be used for debugging')

    if ignore_ack:
        if _first_run:
            warnings.warn('ignore_ack should only be used for debugging')

        # Default is False
        settings.no_ack = True

    port, fqbn = upload.get_port_and_fqbn(port=port, fqbn=fqbn)

    # TODO maybe factor all this first_run stuff into its own fn and call before
    # first run() call in sequence case, so the first "Config file: ..." doesn't
    # have the warnings and baud rate between it and the rest (for consistency)?
    if _first_run:
        if allow_version_mismatch:
            # TODO maybe just err if not _DEBUG then?
            warnings.warn('allow_version_mismatch should only be used for '
                'debugging!'
            )

        # TODO maybe move this function in here...
        py_version_str = upload.version_str()
        # update check not working yet
        '''
        py_version_str = upload.version_str(update_check=True,
            update_on_prompt=True
        )
        '''

        if do_upload:
            # TODO save file modification time at upload and check if it has
            # changed before re-uploading with this flag... (just to save
            # program memory life...) (docker couldn't use...)

            # TODO maybe refactor back and somehow have a new section of
            # argparser filled in without flags here, indicating they are upload
            # specific flags. idiomatic way to do that? subcommand?

            # This raises a RuntimeError if the compilation / upload returns a
            # non-zero exit status, stopping further steps here, as intended.
            upload.main(port=port, fqbn=fqbn, verbose=verbose)

        # TODO TODO also lookup latest hash on github and check that it's not in
        # any of the hashes in our history (git log), and warn / prompt about
        # update if github version is newer

        if (not allow_version_mismatch and
            py_version_str == upload.no_clean_hash_str):

            # TODO try to move this error to before upload would happen
            # (if upload is requested)
            raise ValueError('can not run with uncommitted changes without '
                'allow_version_mismatch (-a), which is only for debugging. '
                'please commit and re-upload.'
            )

        validation.validate_port(port)

        # This is set into a global variable, so that on subsequent config files
        # in the same run of this script, it doesn't need to be parsed / printed
        # again.
        baud_rate = util.parse_baud_from_sketch()
        if verbose:
            print(f'Baud rate (parsed from Arduino sketch): {baud_rate}\n')

    expected_duration_s = util.time_config_will_take_s(all_required_data, print_=True)

    # It's a file in this case, and we are copying the file path to the clipboard.
    if type(config) is str:
        # TODO allow disabling this with env var (appropriately set)
        pyperclip.copy(config)
        print(f'Copied {config} to clipboard\n')

    util.print_pins2odors(config_dict)
    print()

    # TODO maybe have option to try to save clipboard before filling it w/ pyperclip and
    # here (just since we should have pasted by here), maybe fill w/ old contents?
    if pause_before_start:
        # TODO or maybe somehow have this default to True if a generator is
        # being used (especially if i don't add some way to have that re-use
        # pins, or if i do and it's disabled)
        # TODO maybe warn if no pins2odors, in this case
        # TODO maybe prompt user to connect arduino if after Enter is pressed
        # here, the serial device would fail to be found in the next line
        input('Press Enter once the odors are connected')

    # Opening flow controllers and setting initial flows.
    # Want this to happen after Enter press for the same reason as below.
    flow_setpoints_sequence = None
    if flow.flow_setpoints_sequence_key in config_dict:

        mfc_id2flow_controller, are_flows_constant = flow.open_alicat_controllers(
            config_dict, verbose=verbose
        )
        flow_setpoints_sequence = config_dict[flow.flow_setpoints_sequence_key]

        if not verbose:
            print('Initial ', end='')

        flow.set_flow_setpoints(mfc_id2flow_controller,
            flow_setpoints_sequence[0], verbose=verbose
        )

        # TODO TODO replace w/ checking flows and continuing once they get within some
        # tolerance
        # TODO skip if current flows (read before Enter) are same as requested?
        mfc_settling_wait_s = 2.0
        print(f'Waiting {mfc_settling_wait_s:.1f}s for MFCs to reach set points...',
            end='', flush=True
        )
        time.sleep(mfc_settling_wait_s)
        print('done', flush=True)

    # Want this to happen after we press Enter (when we do), so that we can show the
    # pins -> odors for a few (started in parallel), but only re-run the config we were
    # actually trying to run.
    if type(config) is str:
        util.write_last_attempted_config_file(config)

    if not settings.follow_hardware_timing:
        # TODO factor this + above calculation of duration into separate CLI util
        expected_finish = \
            datetime.now() + timedelta(seconds=expected_duration_s)

        finish_str = expected_finish.strftime('%I:%M%p').lstrip('0')
        print(f'Will finish at: {finish_str}')
        #

    pins2odors = util.get_pins2odors(config_dict)

    n_trials = util.number_of_trials(all_required_data)
    one_trial_s = util.seconds_per_trial(all_required_data)

    # TODO TODO define some class that has its own context manager that maybe
    # essentially wraps the Serial one? (just so people don't need that much
    # boilerplate, including explicit calls to pyserial, when using this in
    # other python code)
    with serial.Serial(port, baud_rate, timeout=0.1) as ser:
        print('Connected')
        connect_time_s = time.time()

        while True:
            version_line = ser.readline()
            if len(version_line) > 0:
                arduino_version_str = version_line.decode().strip()
                break

            if time.time() - connect_time_s > timeout_s:
                raise RuntimeError('arduino did not respond within '
                    f'{timeout_s:.1f} seconds. have you uploaded the code? '
                    're-run with -u if not.'
                )

        if _first_run:
            if not allow_version_mismatch:
                    if arduino_version_str == upload.no_clean_hash_str:
                        raise ValueError('arduino code came from dirty git'
                            ' state. please commit and re-upload.'
                        )
                    if py_version_str != arduino_version_str:
                        raise ValueError('version mismatch (Python: '
                            f'{py_version_str}, Arduino: {arduino_version_str}'
                            ')! please re-upload (add the -u flag)!'
                        )

            elif verbose:
                # TODO make sure this doesn't cause windows case to fail
                # (because these are not defined) if verbose=True. might need to
                # move things around a bit.
                print('Python version:', py_version_str)
                print('Arduino version:', arduino_version_str)

        write_message(ser, settings, ignore_ack=ignore_ack, verbose=verbose)

        write_message(ser, pin_sequence, ignore_ack=ignore_ack, verbose=verbose)

        # TODO maybe use:
        # if settings.WhichOneof('control') == 'follow_hardware_timing':
        # here? seems to work though...
        if settings.follow_hardware_timing:
            print('Ready (waiting for hardware triggers)')
        else:
            print('Starting')
            seen_trial_indices = set()
            last_trial_idx = None

        # TODO err in not settings.follow_hardware_timing case, if enough time
        # has passed before we get first trial status print?

        start_time_s = time.time()

        readline_times = []

        while True:
            if not settings.follow_hardware_timing:
                # Couldn't parse output of readline() below in
                # follow_hardware_timing case, because those prints come at [I
                # believe] the odor pulse offsets there, so we would at least
                # need to hardcode some delays or something.
                trial_idx = util.curr_trial_index(start_time_s, one_trial_s,
                    n_trials
                )

                # If there were much worry that some of the `ser.readline()`
                # calls below (the only other thing in this loop that should be
                # slow) could take long, we might want to set these flow
                # setpoints in some parallel thread/process / use non-blocking
                # IO in place of this readline() call. However, when I measured
                # these delays they seemed stable around ~0.10[1-3]s. Most are
                # right on 0.100s, but maybe slightly longer if actually reading
                # data?

                # possible that trial_idx could be returned as None very briefly
                # at the end
                if trial_idx != last_trial_idx and trial_idx is not None:
                    trial_pins = util.get_trial_pins(pin_sequence, trial_idx)

                    # TODO maybe also suffix w/ pins in parens if verbose

                    # TODO get rid of '(s)' and just make plural when approp
                    # TODO fix how in case where using flow controllers + no
                    # pins2odors, printing order / spacing is diff on the first one
                    # (wrt the 'trial: ...' line)
                    if pins2odors is not None:
                        # p not in pins2odors when it's an explicit balance pin
                        print(f'trial: {trial_idx + 1}/{n_trials}, odor(s):',
                            util.format_mixture_pins(pins2odors, trial_pins,
                                show_abbrevs=False
                            )
                        )
                        # TODO maybe try to suffix w/ coarse tqdm progress
                        # within each trial, to get an indication of when next
                        # one is up.
                        # https://stackoverflow.com/questions/62048408
                        # maybe even visually change / mark odor region/onset
                        # on progress bar?

                    # for the most part, this seemed to get printed some
                    # *roughly* 0.1-0.5s after the old print passed through from
                    # the arduino. could be consistent w/ just the ~0.1s i
                    # observed for max_readline_s
                    #print('trial_idx:', trial_idx)

                    if flow_setpoints_sequence is not None:
                        # TODO even if not verbose, should print something if flow is
                        # anything other than either default or initial flows when MFCs
                        # were turned on. or just always. just fit in the same line? or
                        # one line after?
                        flow.set_flow_setpoints(
                            mfc_id2flow_controller,
                            flow_setpoints_sequence[trial_idx],
                            check_set_flows=check_set_flows,
                            silent=are_flows_constant,
                            verbose=verbose,
                        )
                        if not are_flows_constant:
                            print()

                    last_trial_idx = trial_idx
                    seen_trial_indices.add(trial_idx)

            readline_t0 = time.time()

            line = ser.readline()

            readline_t1 = time.time()
            readline_s = readline_t1 - readline_t0
            readline_times.append(readline_s)

            if len(line) > 0:
                try:
                    line = line.decode()
                    # still letting arduino do printing in this case for now,
                    # cause way i'm doing it in !follow_hardware_timing case
                    # relies on the known timing info.
                    if pins2odors is None or settings.follow_hardware_timing:
                        print(line, end='')

                    if line.strip() == 'Finished':
                        finish_time_s = time.time()
                        break

                    # TODO mayyybe could parse trial pins reported and compare
                    # to expected. a bit paranoid though...
                    # (might be useful to print odors in follow_hardware_timing
                    # case too, but not sure i care that much about that case
                    # anymore)
                    #pins = [
                    #    int(p) for p in line.split(':')[-1].strip().split(',')
                    #]

                # Docs say decoding errors will be a ValueError or a subclass.
                # UnicodeDecodeError, for instance, is a subclass.
                except ValueError as e:
                    print(e)
                    print(line)

        max_readline_s = max(readline_times)
        # Were all right around 0.1s last I measured
        if flow_setpoints_sequence is not None and max_readline_s > 0.11:
            warnings.warn('max readline time might have been long enough to '
                'cause problems setting flow rates in a timely manner '
                f'({max_readline_s:.3f}s)'
            )

        duration_s = finish_time_s - start_time_s

        # If we are just triggering off of input pulses, as in
        # follow_hardware_timing case, we don't know how long trials will be.
        if not settings.follow_hardware_timing:
            max_duration_diff_s = 0.5
            duration_diff_s = duration_s - expected_duration_s
            if abs(duration_diff_s) > max_duration_diff_s:
                # TODO maybe log regardless of _DEBUG?
                if _DEBUG:
                    warnings.warn('experiment duration differed from expectation by'
                        f'{duration_diff_s:.3f} (or communication with something '
                        'took longer than normal to finish up at the end)'
                    )

            expected_seen_trials_indices = set(range(n_trials))
            if not seen_trial_indices == expected_seen_trials_indices:
                missing = expected_seen_trials_indices - seen_trial_indices
                warnings.warn('flow controller updating might have missed '
                    'some trials!'
                )

            # i haven't yet seen this actually None, cause for whatever reason,
            # duration_s is usually something like ~0.008s less than
            # expected_duration_s. i guess because the time it takes to intiate
            # stuff at the start, so None actually may never practically be
            # reached.
            '''
            trial_idx_after_finished = curr_trial_index(
                start_time_s, one_trial_s, n_trials
            )
            if trial_idx_after_finished is not None:
                warnings.warn('expected curr_trial_index to return None after '
                'microcontroller reports being finished'
                )
            '''


# TODO maybe add a flag like verbose but just for this fn?
# TODO maybe this should also call load and yield (all_required_data, config_dict)
# (to avoid duplicating logic testing what type config is and branching on that)
def config_iter(config, hardware_config=None, _skip_config_preprocess_check=False,
    verbose=False):
    """Generates a sequences of config (str | dict), each as `run` input

    config (str|dict|None): str can be a path to a config file or a directory containing
        a sequence of them (must be numbered following convention)
    """
    if IN_DOCKER and config is not None:
        # TODO reword to be inclusive of directory case?
        raise ValueError('passing filenames to docker currently not supported. '
            'instead, redirect stdin from that file. see README for examples.'
        )

    if config is None:
        # TODO probably still want to fail if 'generator' key *is* there in this case
        warnings.warn('setting _skip_config_preprocess_check=True as '
            'check_need_to_preprocess_config currently does not support '
            'case where config is read from stdin.'
        )
        _skip_config_preprocess_check = True

    # TODO TODO if i'm going to allow config to be either a list of files
    # or a directory with config files, make type consistent (make `config`
    # a list in nargs=1 case)? + don't check for need to preprocess if input is
    # a list (only support terminal config files in that case)
    # TODO maybe do support a sequence of config files though (also require to
    # have suffix ordering them), to generate full diagnostic -> pair ->
    # diagnostic for my pair experiments? probably not, cause # of pairs i can
    # actually do will probably vary a lot from fly-to-fly...
    # TODO add CLI flag to prevent this from saving anything (for testing)
    # (maybe have the flag also just print the YAML(s) the generator creates
    # then?)
    if not _skip_config_preprocess_check:
        # TODO TODO fix so config==None (->stdin input) (used in docker case) works with
        # this too.
        config = check_need_to_preprocess_config(config,
            hardware_config=hardware_config, verbose=verbose
        )

    # TODO maybe refactor so that run no longer takes None for config (-> using
    # sys.stdin in load call early in run), or even only take a dict. might make it
    # easier to compose with other functions...
    if config is None or type(config) is dict or (
        type(config) is str and isfile(config)):

        yield config

    elif type(config) is str and isdir(config):
        config_files = glob.glob(join(config, '*'))

        # We expect each config file to follow this naming convention:
        # <x>_<n>.[yaml/json], where <x> can be anything (including containing
        # underscores, if you wish), and <n> is an integer used to order the
        # config files. Lower numbers will be executed first.
        order_nums = []
        for f in config_files:
            num_part = splitext(split(f)[1])[0].split('_')[-1]
            try:
                n = int(num_part)
                order_nums.append(n)
            except ValueError:
                raise ValueError(f'{config} had at least one file ({f}) that '
                    'did not have a number right before the extension, to '
                    'indicate order. exiting.'
                )

        config_files = [f for _, f in sorted(zip(order_nums, config_files),
            key=lambda x: x[0]
        )]

        if len(config_files) > 1:
            all_configs_pins2odors_delim = '#' * 80

            print(all_configs_pins2odors_delim)

            # could refactor so load only happens once but whatever
            for i, config_file in enumerate(config_files):

                all_required_data, config_dict = config_io.load(config_file)

                print(f'{config_file} ({i+1}/{len(config_files)})')
                util.print_pins2odors(config_dict, header=False)
                print()

            print(all_configs_pins2odors_delim)
            print()

        for i, config_file in enumerate(config_files):
            # TODO maybe (in addition to some abstractions / standards for
            # formatting odors in trials (rather than pins)) also have some
            # faculties for summarizing config files, and print that alongside /
            # in place of the file name? (e.g. the odors in the pair, for the
            # pair conc grid experiments)?
            print(f'Config file: {config_file} ({i+1}/{len(config_files)})')

            yield config_file

            if i < len(config_files) - 1:
                print()

    else:
        # TODO TODO does this break docker stdin based config specification? fix
        # if so.
        raise ValueError(f'config type {type(config)} not recognized. must be '
            'str path to file/directory, dict, or None to use stdin.'
        )


def main(config, hardware_config=None, _skip_config_preprocess_check=False,
    verbose=False, **kwargs):
    """Runs one or several configuration inputs on the olfactometer.

    config (str|dict|None): str can be a path to a config file or a directory containing
        a sequence of them (must be numbered following convention)
    """

    # TODO add arg for excluding pins (e.g. for running basic.py configured w/
    # tom_olfactometer_configs/one_odor.yaml after already hooking up odors from the
    # same generator configured w/ ""/glomeruli_diagnostics.yaml). accept either yaml
    # file w/ pins2odors (or just pins in pin_sequence?) or just a comma separated list
    # of pins on the command line. thread through to command line interfaces.  and
    # should i have an option for just automatically finding the last generated thing
    # and excluding the pins in that? might want to set up an env var for output
    # directory first...

    first_run = True

    for single_run_config in config_iter(config, hardware_config=hardware_config,
        verbose=verbose, _skip_config_preprocess_check=False):

        run(single_run_config, _first_run=first_run, verbose=verbose, **kwargs)

        if first_run:
            first_run = False

