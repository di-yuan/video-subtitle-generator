"""
SRT & FCPXML CONVERTER
REQUIREMENT: OpenCC (pip install opencc-python-reimplemented)
AUTHOR: MICHAEL HONG
"""

import xml.etree.ElementTree as ET
import re
import copy
import argparse
import os

parser = argparse.ArgumentParser(
    description="Convert between .srt and .fcpxml files."
)
parser.add_argument(
    '-i', '--input', required=True,
    help="name for the input file (.srt or .fcpxml)")
parser.add_argument(
    '-o', '--output', required=True,
    help="name for the output file (.srt or .fcpxml)")
parser.add_argument(
    '-c', '--convert',
    help="(optional) to use OpenCC to convert between Simplified/Traditional Chinese. Please specify the OpenCC configurations (e.g., s2t, t2s)")
parser.add_argument(
    '-t', '--template', default='Template.xml',
    help="(optional) to use a user-specific template file to generate .fcpxml. Default to 'Template.xml'")
parser.add_argument(
    '-fr', '--framerate', default=29.97, type=float,
    help='(optional) framerate should be set in the template. This argument provides a sanity check. Default to 29.97fps')
parser.add_argument(
    '--offset', type=float,
    help='(optional) move the entire timeline forward/backward from input to output. In seconds')
parser.add_argument(
    '-e', '--event_name', default='CC_XML', type=str)
args = parser.parse_args()

FILE_IN = args.input
FILE_OUT = args.output
XML_TEMPLATE = args.template

cc = None
if args.convert:
    from opencc import OpenCC
    cc = OpenCC(args.convert)

framerate_tuple = (1001, 30000)  # default to 29.97fps


# TIME STAMP CONVERSION METHODS

def convert_xml_t(s, return_tuple=False):
    if '/' not in s:  # whole seconds
        return float(s[:-1])
    components = s.split('/')
    x = float(components[0])
    y = float(components[1][:-1])
    if return_tuple:  # convert to int
        return int(components[0]), int(components[1][:-1])
    return x / y


def convert_t_xml(t):
    multiplier, denominator = framerate_tuple
    x = int(int(int(t * denominator) / multiplier)) * multiplier
    if x % denominator == 0:
        return '%ds' % (x / denominator)  # whole number
    return f'{x}/{denominator}s'


def convert_t_srt(t):
    t_int = int(t)
    ms = int((t - t_int) * 1000)
    s = t_int % 60
    m = int(t_int / 60) % 60
    h = int(t_int / 3600)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'


def convert_srt_t(arr):
    return float(arr[0]) * 3600. + float(arr[1]) * 60. + float(arr[2]) + float(arr[3]) / 1000.


def convert_text(__str):
    if cc:
        return cc.convert(__str)
    return __str


# INPUT CONVERSION METHODS

def process_input_srt():
    with open(FILE_IN, 'r', encoding='utf-8-sig') as f:
        lines = f.read().splitlines()[:-1]

    total_rows = len(lines)
    i = 0
    data = []

    while i < total_rows:
        i += 1
        m = re.match(
            r'(\d+):(\d+):(\d+),(\d+) --> (\d+):(\d+):(\d+),(\d+)', lines[i])
        t_start = convert_srt_t(m.groups()[0:4])
        t_end = convert_srt_t(m.groups()[4:8])
        data.append((t_start, t_end, lines[i + 1]))

        i += 3

    return data


def process_input_fcpxml():
    xml = ET.parse(FILE_IN)
    root = xml.getroot()
    n_library = root[1]
    n_event = n_library[0]
    n_project = n_event[0]
    n_sequence = n_project[0]
    n_spine = n_sequence[0]

    data = []
    for node in n_spine:
        if node.tag == 'title':
            n_text = node.find('text')[0].text
            if n_text == 'Title':
                continue  # remove bad frames

            offset = convert_xml_t(node.get('offset'))
            duration = convert_xml_t(node.get('duration'))
            end = offset + duration
            data.append((offset, end, n_text))

    return data


def process_output_srt(data):
    with open(FILE_OUT, 'w') as f:
        counter = 1
        for line in data:
            t_start, t_end, text = line
            f.write(f'{counter}\n')
            f.write(
                convert_t_srt(t_start) + ' --> ' + convert_t_srt(t_end) + '\n')
            f.write(convert_text(text) + '\n')
            f.write('\n')
            counter += 1


def process_output_fcpxml(data):
    xml = ET.parse(XML_TEMPLATE)
    root = xml.getroot()

    # check if template frameDuration is consistent with specified frame rate
    n_resources = root[0]
    xml_framerate = n_resources.find('format').get('frameDuration')
    xml_framerate_fps = 1 / convert_xml_t(xml_framerate)
    if abs(args.framerate - xml_framerate_fps) > 0.005:
        raise Exception(
            f'template framerate {xml_framerate_fps:.2f}fps is inconsistent'
            'with specified framerate {args.framerate:.2f}fps.'
            ' Please set the correct framerate using flag -fr.')

    global framerate_tuple
    framerate_tuple = convert_xml_t(xml_framerate, return_tuple=True)

    n_library = root[1]
    n_event = n_library[0]
    n_event.set('name', event_name)
    n_project = n_event[0]
    n_project.set('name', project_name)

    n_sequence = n_project[0]
    n_spine = n_sequence[0]

    n_gap = n_spine[0]
    n_gap.set('duration', convert_t_xml(data[-1][1] - data[0][0]))
    title_proto = n_gap.find('title')  # find the first title as template
    # add a divider between template and content
    n_gap.append(ET.Element('divider'))

    counter = 1
    for line in data:
        t_start, t_end, text = line
        title_new = copy.deepcopy(title_proto)

        offset = convert_t_xml(t_start)
        duration = convert_t_xml(t_end - t_start)
        output_text = convert_text(text)  # apply conversion

        title_new.set('name', f'{{{counter}}} {output_text}')
        title_new.set('lane', '1')
        title_new.set('offset', offset)
        title_new.set('duration', duration)
        title_new.set('start', offset)

        title_new.find('text')[0].text = output_text
        title_new.find('text')[0].set('ref', f'ts{counter}')
        title_new.find('text-style-def').set('id', f'ts{counter}')

        n_gap.append(title_new)
        counter += 1

    while n_gap[0].tag != 'divider':
        n_gap.remove(n_gap[0])
    n_gap.remove(n_gap[0])  # remove divider

    with open(FILE_OUT, 'w') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE fcpxml>\n\n')
        f.write(ET.tostring(
            root, encoding='UTF-8', xml_declaration=False).decode('utf-8'))


project_name = ''

# convert input file to internal representation
if FILE_IN.endswith('.srt'):
    data = process_input_srt()
elif FILE_IN.endswith('.fcpxml'):
    data = process_input_fcpxml()
else:
    raise Exception(f'unsupported input file type: {FILE_IN}')

filename = os.path.basename(FILE_IN)
event_name = args.event_name
project_name, _ = os.path.splitext(filename)

# apply global offset (if applicable)
if args.offset:
    data = [(x[0] + args.offset, x[1] + args.offset, x[2]) for x in data]

# convert internal representation to output
if FILE_OUT.endswith('.srt'):
    process_output_srt(data)
elif FILE_OUT.endswith('.fcpxml'):
    process_output_fcpxml(data)
else:
    raise Exception(f'unsupported output file type: {FILE_OUT}')
