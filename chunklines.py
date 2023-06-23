import os
import json
import click


@click.command()
@click.argument("input_dir")
@click.argument("output_file")
def chunklines(input_dir, output_file):
    # Open the output file
    with open(output_file, "w") as out:
        # Walk through the input directory
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith(".json"):
                    # Open each json file
                    with open(os.path.join(root, file)) as json_file:
                        data = json.load(json_file)

                        # Remove the transcript key
                        data.pop("transcript", None)

                        # Iterate over the chunks
                        for idx, chunk in enumerate(data.get("chunks", []), start=1):
                            # Create the new chunk entry
                            new_entry = {
                                "id": f'{data["video_id"]}-{idx}',
                                "text": chunk["text"],
                                "metadata": data,
                            }
                            # Remove the 'chunks' key from metadata
                            new_entry["metadata"].pop("chunks", None)
                            # Add the start, end, and duration from chunk to metadata
                            new_entry["metadata"].update(
                                {
                                    "start": chunk["start"],
                                    "end": chunk["end"],
                                    "duration": chunk["duration"],
                                }
                            )

                            # Write the new chunk entry to the output file
                            out.write(json.dumps(new_entry))
                            out.write(
                                "\n"
                            )  # Newline separates entries in a JSON Lines file


if __name__ == "__main__":
    chunklines()
