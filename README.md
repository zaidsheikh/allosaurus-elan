## [Allosaurus](https://github.com/xinjli/allosaurus/) (universal phone recognizer) extension for [ELAN](https://archive.mpi.nl/tla/elan)

### Setup

#### Linux

1. Download the latest version of ELAN from [here](https://archive.mpi.nl/tla/elan/download) and install it:
```
wget https://www.mpi.nl/tools/elan/ELAN-XX_linux.tar.gz
tar xzf ELAN-XX_linux.tar.gz
```

2. [Download a copy of this repo](https://github.com/zaidsheikh/allosaurus-elan/archive/refs/heads/dev.zip) and unzip it. Copy the `allosaurus-elan-dev/` folder into ELAN's extensions dir (`ELAN-XX/lib/app/extensions/`).

#### Mac

1. If ELAN is not already installed on your Mac, [download the latest .dmg installer](https://archive.mpi.nl/tla/elan/download) and install it. It should be installed in the `/Applications/ELAN_XX` directory, where `XX` is the name of the version.
2. Download this [zip file](https://github.com/zaidsheikh/allosaurus-elan/archive/refs/heads/dev.zip) and unzip it. You should see a folder named `allosaurus-elan-dev` containing the contents of this repo.
3. Right-click `ELAN_XX` and click "Show Package Contents", then copy your `allosaurus-elan-dev` folder into `ELAN_XX.app/Contents/app/extensions`.


#### Windows

1. Download the latest version of ELAN from [here](https://archive.mpi.nl/tla/elan/download) and install it.
2. [Download a copy of this repo](https://github.com/zaidsheikh/allosaurus-elan/archive/refs/heads/dev.zip) and unzip it. Copy the `allosaurus-elan-dev/` folder into ELAN's extensions dir (`ELAN-XX/app/extensions/`).
3. Install [Python 3](https://www.python.org/downloads/) if it isn't already installed.


### Instructions

Start ELAN with the provided test audio file

`ELAN_6-1/bin/ELAN allosaurus-elan/test/allosaurus.wav &`

Switch to the "Recognizers" tab and then select "Allosaurus Phoneme Recognizer" from the Recognizer dropdown list at the top and then click the "Start" button.
If this is your first time using the allosaurus-elan plugin, you will be prompted to login to the [CMULAB backend server](https://github.com/neulab/cmulab) and get an access token (you can create an account or simply login with an existing Google account):

![cmulab_login](https://user-images.githubusercontent.com/2358298/144942829-052e3f45-01f2-4f93-8562-2f95b00ec24f.png)

Once the plugin has finished processing the file, ELAN will prompt you to load the output tier generated by the recognizer. You should now be able to see the phoneme transcriptions in the timeline viewer.

![image](https://user-images.githubusercontent.com/2358298/124541645-da0adf80-ddef-11eb-8bb6-4a26713545a6.png)

If the audio file is long, you can use an existing audio segmenter (for example, the "Fine audio segmentation" recognizer in ELAN) to segment the audio into utterance level segments first. Once that's done, before you run the "Allosaurus Phoneme Recognizer", in the "Parameters" section set the input tier to the audio segmenter output tier generated previously (for example: "Fine_Segmentation" tier).

![fine_segmentation_input_tier](https://user-images.githubusercontent.com/2358298/126795420-00efc527-d2b8-40c2-8122-0cb37c4c1cfb.png)


### Fine-tuning pre-trained models

The plugin also supports uploading user-corrected phoneme transcriptions in order to fine-tune the pretrained models. After you run the plugin on any audio file, you can make corrections to the generated phoneme trasnscriptions and save it to an eaf file. To fine-tune allosaurus using these corrected transcriptions, open the parameters window and select the eaf file in the "Upload EAF file to fine-tune allosaurus" section:

![allosaurus-elan_params](https://user-images.githubusercontent.com/2358298/144940955-880700ef-bdfb-4721-b935-6684f1f71782.png)

The fields relevant to fine-tuning are highlighted above. Make sure the name of the tier containing the user-corrected transcrptions matches that set in the "Tier name for fine-tuning" field. Currently due to some limitations, only fine-tuning of the "eng2102" pre-trained model is possible. Because the phonesets might differ between different models, it's best to fine-tune a model using transcriptions generated from the same model and lang code. Click on the "Report" button to get the ID of the new model (for example: `eng2102_20211207001022575724`). You can now use this model ID in the "Pretrained model" field (Parameters section) and re-run allosaurus-elan to check if the output from the new model is better (note that you will need to first clear the "Upload EAF file to fine-tune allosaurus" field otherwise the plugin will run in "fine-tuning" mode).

