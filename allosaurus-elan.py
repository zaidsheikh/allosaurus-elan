#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# A short script invokes Allosaurus phoneme recognizer via
# the CMU Linguistic Annotation Backend API. Adapted from:
# github.com/coxchristopher/persephone-elan/blob/master/persephone-elan.py

import atexit
import os
import os.path
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata

import requests
import json
import traceback
from utils.create_dataset import create_dataset_from_eaf
from credentials import ask_for_authtoken
import tkinter.messagebox


# The set of annotations (dicts) parsed out of the given ELAN tier.
annotations = []

# The parameters provided by the user via the ELAN recognizer interface
# (specified in CMDI).
params = {}

@atexit.register
def cleanup():
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


# Read in all of the parameters that ELAN passes to this local recognizer on
# standard input.
for line in sys.stdin:
    match = re.search(r'<param name="(.*?)".*?>(.*?)</param>', line)
    if match:
        params[match.group(1)] = match.group(2).strip()

lang_code = params.get("lang_code", "eng").strip()
input_tier = params.get('input_tier', '')
pretrained_model = params.get("pretrained_model", "eng2102").strip()

print("input_tier: " + input_tier)

server_url = params['server_url'].strip().rstrip('/')
auth_token = params.get("auth_token", "").strip()
if not auth_token:
    auth_token_file = os.path.join(os.path.expanduser("~"), ".allosaurus_elan")
    if os.path.exists(auth_token_file):
        with open(auth_token_file) as fin:
            auth_token = fin.read().strip()
    else:
        auth_token = ask_for_authtoken(server_url)

eaf_for_finetuning = params.get("eaf_for_finetuning", "None").strip()
if eaf_for_finetuning and eaf_for_finetuning != "None":
    print("PROGRESS: 0.1 Generating dataset...", flush = True)
    tier_name = params.get("tier_for_finetuning", "Allosaurus").strip()
    tmpdirname = tempfile.TemporaryDirectory()
    print('creating temporary directory', tmpdirname)
    dataset_dir = os.path.join(tmpdirname.name, "dataset")
    train_dir = os.path.join(dataset_dir, "train")
    validate_dir = os.path.join(dataset_dir, "validate")
    create_dataset_from_eaf(eaf_for_finetuning, train_dir, tier_name)
    shutil.copytree(train_dir, validate_dir)
    dataset_archive = shutil.make_archive(dataset_dir, 'zip', dataset_dir)
    shutil.copytree(tmpdirname.name, tmpdirname.name + "_copy") # TODO: delete this
    print("PROGRESS: 0.5 Fine-tuning allosaurus...", flush = True)
    with open(dataset_archive,'rb') as zip_file:
        files = {'file': zip_file}
        url = params['server_url'].rstrip('/') + "/annotator/segment/1/annotate/4/"
        try:
            if lang_code == "ipa":
                tkinter.messagebox.showerror(title="'ipa' lang code not supported",
                                             message="'ipa' lang code is not supported by allosaurus for fine-tuning!")
                sys.exit(1)
            allosaurus_params = {"lang": lang_code, "epoch": 2, "pretrained_model": pretrained_model}
            headers = {}
            if params.get('auth_token'):
                headers["Authorization"] = params["auth_token"].strip()
            r = requests.post(url, files=files, data={"params": json.dumps(allosaurus_params)}, headers=headers)
        except:
            sys.stderr.write("Error connecting to backend server " + params['server_url'] + "\n")
            traceback.print_exc()
        print("Response from CMULAB server " + params['server_url'] + ": " + r.text)
    print('RESULT: DONE.', flush = True)
    sys.exit(0)


# grab the 'input_tier' parameter, open that
# XML document, and read in all of the annotation start times, end times,
# and values.
# Note: Tiers for the recognizers are in the AVATech tier format, not EAF
print("PROGRESS: 0.1 Loading annotations on input tier", flush = True)
if os.path.exists(input_tier):
    with open(input_tier, 'r', encoding = 'utf-8') as input_tier_file:
        for line in input_tier_file:
            match = re.search(r'<span start="(.*?)" end="(.*?)"><v>(.*?)</v>', line)
            if match:
                annotation = { \
                    'start': int(float(match.group(1)) * 1000.0), \
                    'end' : int(float(match.group(2)) * 1000.0), \
                    'value' : match.group(3) }
                annotations.append(annotation)


print("PROGRESS: 0.9 Transcribing clips", flush = True)
with open(params['source'],'rb') as audio_file:
    files = {'file': audio_file}
    url = params['server_url'].rstrip('/') + "/annotator/segment/1/annotate/2/"
    try:
        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token
        allosaurus_params = {"lang": lang_code, "model": pretrained_model}
        r = requests.post(url, files=files, data={"segments": json.dumps(annotations), "params": json.dumps(allosaurus_params)}, headers=headers)
    except:
        sys.stderr.write("Error connecting to backend server " + params['server_url'] + "\n")
        traceback.print_exc()
    print("Response from CMULAB server " + params['server_url'] + ": " + r.text)
    transcribed_annotations = json.loads(r.text)

# Then open 'output_tier' for writing, and return all of the new phoneme
# strings produced by Allosaurus as the contents of <span> elements

print("PROGRESS: 0.95 Preparing output tier", flush = True)
with open(params['output_tier'], 'w', encoding = 'utf-8') as output_tier:
    # Write document header.
    output_tier.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    output_tier.write('<TIER xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" ' +
                      'xsi:noNamespaceSchemaLocation="file:avatech-tier.xsd" columns="Allosaurus">\n')

    for annotation in transcribed_annotations:
        output_tier.write('    <span start="%s" end="%s"><v>%s</v></span>\n' %
                          (annotation['start'], annotation['end'], annotation['transcription']))

    output_tier.write('</TIER>\n')

# Finally, tell ELAN that we're done.
print('RESULT: DONE.', flush = True)
