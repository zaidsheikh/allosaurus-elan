import argparse
import pympi
import pydub
from pathlib import Path


def create_dataset_from_eaf(eaf_file, output_dir, tier_name="Allosaurus"):
    print(eaf_file)
    print(output_dir)
    print(tier_name)
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)
    input_elan = pympi.Elan.Eaf(file_path=eaf_file)
    audio_file_path = input_elan.media_descriptors[0]["MEDIA_URL"][len("file://"):]
    full_audio = pydub.AudioSegment.from_file(audio_file_path, format = 'wav')
    for segment_id in input_elan.tiers[tier_name][0]:
        start_id, end_id, transcription, _ = input_elan.tiers[tier_name][0][segment_id]
        start = input_elan.timeslots[start_id]
        end = input_elan.timeslots[end_id]
        clip = full_audio[start:end]
        clip.export(output_dir_path / (segment_id + ".wav"), format = 'wav')
        (output_dir_path / (segment_id + ".txt")).write_text(transcription)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="convert EAF file to dataset required for fine-tuning allosaurus")
    parser.add_argument('eaf_file', type=str, help="EAF file with phone transcriptions")
    parser.add_argument('output_dir', type=str, help="output dir")
    parser.add_argument('--tier', type=str, default="Allosaurus", help="Tier containing phone transcriptions")
    args = parser.parse_args()
    create_dataset_from_eaf(args.eaf_file, args.output_dir, args.tier)
