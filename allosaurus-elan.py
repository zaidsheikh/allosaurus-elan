#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# A short script to that wraps the Allosaurus phoneme recognition system to
# act as a local recognizer in ELAN.
#

import atexit
import os
import os.path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

# from allosaurus.app import read_recognizer
# allosaurus_model = read_recognizer()


import pydub
import requests
import json
import traceback
import tkinter as tk
from tkinter import simpledialog


# The set of annotations (dicts) parsed out of the given ELAN tier.
annotations = []

# The parameters provided by the user via the ELAN recognizer interface
# (specified in CMDI).
params = {}

# The parameters that were originally used to load the training corpus and
# train the Allosaurus model being used for transcription here.
model_parameters = {}

# root = tk.Tk()
# root.withdraw()
# user_inp = simpledialog.askstring(title="Credentials", prompt="Username:")
# print("Hello", user_inp)

@atexit.register
def cleanup():
    # When this recognizer ends (whether by finishing successfully or when
    # cancelled), run through all of the available annotations and remove
    # each temporary audio clip, its corresponding '.npy' feature file, and
    # all associated symlinks.
    for annotation in annotations:
        if 'wav_symlink' in annotation:
            os.unlink(annotation['wav_symlink'])
            del(annotation['wav_symlink'])

        if 'feat_symlink' in annotation:
            os.unlink(annotation['feat_symlink'])
            del(annotation['feat_symlink'])

        if 'clip' in annotation:
            annotation['clip'].close()
            del(annotation['clip'])

        if 'npy_symlink' in annotation:
            os.unlink(annotation['npy_symlink'])
            del(annotation['npy_symlink'])

        if 'npy' in annotation:
            os.remove(annotation['npy'])
            del(annotation['npy'])

    # Remove 'untranscribed_prefixes.txt' if it exists.
    if params.get('corpus_dir', None) and \
       os.path.exists(os.path.join(params['corpus_dir'], \
                      'untranscribed_prefixes.txt')):
        os.remove(os.path.join(params['corpus_dir'], \
                  'untranscribed_prefixes.txt'))

    # All other temporary files and directories created by 'tempfile' methods
    # will be removed automatically.

def to_tsuutina_orth(s):
    """ Convert Persephone phoneme strings to Tsuut'ina orthographic forms. """
    # Remove utterance-initial glottal stops (not part of the current
    # orthography).
    s = re.sub(r'^ʔ', '', s)

    # Turn two-vowel sequences with contour tones ("aa HM") into simpler
    # sequences of vowels followed by tones ("a H a M")
    s = re.sub(r'([aiouAIOU])([aiouAIOU]) ([LMH])([LMH])', '\\1 \\3 \\2 \\4', s)

    # Turn long vowels with level tones ("aa H") into simpler sequences of
    # vowels followe by tones  ("a H a H")
    s = re.sub(r'([aiouAIOU])([aiouAIOU]) ([LMH])( |$)', \
        '\\1 \\3 \\2 \\3\\4', s)

    # Temporarily turn tone markers into combining diacritics.
    s = s.replace(' H', u'\u0301')
    s = s.replace(' M', '')
    s = s.replace(' L', u'\u0300')

    # Remove all spaces between phonemes.
    s = s.replace(' ', '')

    # Turn vowel-plus-combining-accent combinations into single, composed
    # characters.
    s = unicodedata.normalize('NFC', s)
    return s

def to_sauk_orth_separate(s):
    """ Convert Persephone phoneme strings from vowel plus length to regular
        Sauk orthographic forms (where circumflexes mark vowel length."""

    # Remove short vowel markers altogether.
    s = s.replace(' S', '')

    # Turn long vowel markers into combining circumflexes, then make sure
    # we never end up with more than one circumflex in a row.
    s = re.sub(' L', u'\N{COMBINING CIRCUMFLEX ACCENT}', s)
    s = re.sub('\N{COMBINING CIRCUMFLEX ACCENT}+', \
        '\N{COMBINING CIRCUMFLEX ACCENT}', s)

    return to_sauk_orth_integrated(s)

def to_sauk_orth_integrated(s):
    """ Convert Persephone phoneme strings that use circumflex accents to mark
        vowel length back into the regular Sauk orthogrphy. """

    # Remove all spaces between phonemes.
    s = s.replace(' ', '')

    # Re-expand filled pauses and interjections.
    s = s.replace('UHHUH', ' uh-huh, ')
    s = s.replace('MHM', ' mhm, ')
    s = s.replace('UH', ' uh, ')
    s = s.replace('UM', ' um, ')

    # Turn vowel-plus-combining-accent combinations into single, composed
    # characters.
    s = unicodedata.normalize('NFC', s)
    return s.strip()



# Read in all of the parameters that ELAN passes to this local recognizer on
# standard input.
for line in sys.stdin:
    match = re.search(r'<param name="(.*?)".*?>(.*?)</param>', line)
    if match:
        params[match.group(1)] = match.group(2).strip()

# Prepare to convert Persephone phoneme strings back into the given community
# orthography, if requested.
#
# TODO: Fix this to look at the label type (e.g., 'phonemes_len_separate'),
# then automatically choose the right orthographic conversion routine. That
# should let us keep the language list to language names only. FIXME
to_orth = None
# if 'orthography' in params:
    # if params['orthography'] == 'Tsuut&apos;ina':
        # to_orth = to_tsuutina_orth
    # elif params['orthography'] == 'Sauk-Separate':
        # to_orth = to_sauk_orth_separate
    # elif params['orthography'] == 'Sauk-Circumflex':
        # to_orth = to_sauk_orth_integrated

# Read in the parameters that were originally used to read the training corpus
# and configure the model that will be used for transcription here.
# with open(os.path.join(params['exp_dir'], 'model_description.txt'), 'r', \
     # encoding = 'utf-8') as f:
    # for line in f:
        # match = re.search(\
            # r'(num_train|batch_size|num_layers|hidden_size)=(\d+)', line)
        # if match:
            # model_parameters[match.group(1)] = int(match.group(2))


# With those parameters in hand, grab the 'input_tier' parameter, open that
# XML document, and read in all of the annotation start times, end times,
# and values.
# Note: Tiers for the recognizers are in the AVATech tier format, not EAF
print("PROGRESS: 0.1 Loading annotations on input tier", flush = True)
if os.path.exists(params.get('input_tier', '')):
    with open(params['input_tier'], 'r', encoding = 'utf-8') as input_tier:
        for line in input_tier:
            match = re.search(r'<span start="(.*?)" end="(.*?)"><v>(.*?)</v>', line)
            if match:
                annotation = { \
                    'start': int(float(match.group(1)) * 1000.0), \
                    'end' : int(float(match.group(2)) * 1000.0), \
                    'value' : match.group(3) }
                annotations.append(annotation)

# Then use ffmpeg(1) to convert the 'source' audio file into a temporary 16-bit
# mono 16KHz WAV, then load that temp file into pydub for easier exporting of
# audio clips in the format that Allosaurus expects. 

ffmpeg = shutil.which('ffmpeg')
# TODO: move this to the backend
if False and ffmpeg and not params['source'].endswith('.wav'):
    print("PROGRESS: 0.2 Converting source audio", flush = True)
    converted_audio_file = tempfile.NamedTemporaryFile(suffix = '.wav')
    subprocess.call([ffmpeg, '-y', '-v', '0', \
        '-i', params['source'], \
        '-ac', '1',
        '-ar', '16000',
        '-sample_fmt', 's16',
        '-acodec', 'pcm_s16le', \
        converted_audio_file.name])
else:
    # Assume it's in the right format, allosaurus will let us know if it isn't
    converted_audio_file = open(params['source'], mode='rb')

print(converted_audio_file.name)
converted_audio = pydub.AudioSegment.from_file(converted_audio_file, format = 'wav')
if not annotations:
    annotations.append({'start': 0, 'end': len(converted_audio), 'value': ""})

# Create a set of WAV clips for each of the annotations specified in
# 'input_tier' in the format that Allosaurus expects

print("PROGRESS: 0.3 Creating temporary clips", flush = True)

# TODO: use tempfile.TemporaryDirectory()
tmp_dir = tempfile.mkdtemp(prefix="allosaurus-elan-")
print(tmp_dir)

for annotation in annotations:
    annotation['clip'] = tempfile.NamedTemporaryFile(suffix = '.wav', dir = tmp_dir, delete=False)
    clip = converted_audio[annotation['start']:annotation['end']]
    clip.export(annotation['clip'], format = 'wav')


print("PROGRESS: 0.9 Transcribing clips", flush = True)
# allosaurus_transcription = allosaurus_model.recognize(params['source'])
if not annotations:
    # allosaurus_transcriptions = allosaurus_model.recognize(converted_audio_file.name, timestamp=True).split('\n')
    pass
else:
    for annotation in annotations:
        # annotation['transcription'] = allosaurus_model.recognize(annotation['clip'].name)
        with open(annotation['clip'].name,'rb') as audio_file:
            files = {'file': audio_file}
            # url="http://localhost:8000/annotator/segment/1/annotate/2/"
            url = params['server_url'].rstrip('/') + "/annotator/segment/1/annotate/2/"
            try:
                r = requests.post(url, files=files, data={})
            except:
                sys.stderr.write("Error connecting to backend server " + params['server_url'] + "\n")
                traceback.print_exc()
            print("Response from CMULAB server " + params['server_url'] + ": " + r.text)
            annotation['transcription'] = json.loads(r.text)["transcription"]
        # print(annotations['transcription'])

converted_audio_file.close()


# Then open 'output_tier' for writing, and return all of the new phoneme
# strings produced by Allosaurus as the contents of <span> elements

print("PROGRESS: 0.95 Preparing output tier", flush = True)
with open(params['output_tier'], 'w', encoding = 'utf-8') as output_tier:
    # Write document header.
    output_tier.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    output_tier.write('<TIER xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' +
                      'xsi:noNamespaceSchemaLocation="file:avatech-tier.xsd" columns="Allosaurus">\n')

    if not annotations:
        start = allosaurus_transcriptions[0].split()[0]
        end = str(float(allosaurus_transcriptions[-1].split()[0]) +
                  float(allosaurus_transcriptions[-1].split()[1]))
        allosaurus_transcription = ''
        for transcription in allosaurus_transcriptions:
            allosaurus_transcription = allosaurus_transcription + ' ' + transcription.split()[-1]
        output_tier.write('    <span start="%s" end="%s"><v>%s</v></span>\n' %
                          (start, end, allosaurus_transcription))
    else:
        for annotation in annotations:
            output_tier.write('    <span start="%s" end="%s"><v>%s</v></span>\n' %
                              (annotation['start'], annotation['end'], annotation['transcription']))

    # start = allosaurus_transcriptions[0].split()[0]
    # prev_start = start
    # allosaurus_transcription = ''
    # for transcription in allosaurus_transcriptions:
        # _start, _length, _phone = transcription.split()
        # if float(_start) - float(prev_start) > 0.1:
            # output_tier.write('    <span start="%s" end="%s"><v>%s</v></span>\n' % (start, prev_start, allosaurus_transcription))
            # start = _start
            # allosaurus_transcription = _phone
        # else:
            # allosaurus_transcription = allosaurus_transcription + ' ' + _phone
        # prev_start = _start

    # prev_start, prev_length, prev_value = allosaurus_transcriptions[0].split()
    # for annotation in allosaurus_transcriptions:
        # start, length, value = annotation.split()
        # end = str(float(start) + float(length))
        # output_tier.write('    <span start="%s" end="%s"><v>%s</v></span>\n' % (start, end, value))

    output_tier.write('</TIER>\n')

# Finally, tell ELAN that we're done.
print('RESULT: DONE.', flush = True)
