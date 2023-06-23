import json
import os
from collections import deque
import click
import tiktoken

# Constants for token limits
CHUNK_TOKEN_LIMIT = 80
OVERLAP_TOKEN_LIMIT = 20

tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")


def _best_thumbnail_url(thumbnails):
    if "maxres" in thumbnails:
        return thumbnails["maxres"]["url"]

    if "standard" in thumbnails:
        return thumbnails["standard"]["url"]
    return thumbnails["default"]["url"]


@click.command()
@click.argument("input_dir")
@click.argument("output_dir")
def chunk_transcripts(input_dir, output_dir):
    """
    Breaks down transcripts into smaller chunks.

    Args:
        input_dir: The directory containing the input files.
        output_dir: The directory where the output files will be written.
    """
    for filename in os.listdir(input_dir):
        filepath = os.path.join(input_dir, filename)
        if not filepath.endswith(".json"):
            continue

        try:
            with open(filepath) as file:
                video_data = json.load(file)

                # Clean up metadata
                video_data["thumbnail"] = _best_thumbnail_url(video_data["thumbnails"])
                video_data["video_id"] = video_data["resourceId"]["videoId"]
                video_data.pop("thumbnails", None)
                video_data.pop("resourceId", None)
                video_data.pop("videoOwnerChannelTitle", None)
                video_data.pop("videoOwnerChannelId", None)

        except json.JSONDecodeError:
            print(f"Skipping file {filepath} due to invalid JSON.")
            continue

        transcript = video_data.get("transcript")
        if transcript is None:
            print(f"Skipping file {filepath} due to missing 'transcript' key.")
            continue

        chunks = []
        current_chunk = []
        chunk_start = 0.0
        chunk_end = 0.0
        overlap_buffer = deque(maxlen=OVERLAP_TOKEN_LIMIT)

        for entry in transcript:
            tokens = tokenizer.encode(entry["text"])
            for token in tokens:
                if len(current_chunk) < CHUNK_TOKEN_LIMIT:
                    current_chunk.append(token)
                    if len(current_chunk) == 1:
                        chunk_start = entry["start"]
                    chunk_end = entry["start"] + entry["duration"]
                else:
                    overlap_buffer.append(token)

                if (
                    len(current_chunk) >= CHUNK_TOKEN_LIMIT
                    and len(overlap_buffer) >= OVERLAP_TOKEN_LIMIT
                ):
                    add_chunk(
                        chunks, current_chunk, overlap_buffer, chunk_start, chunk_end
                    )
                    current_chunk = list(overlap_buffer)
                    chunk_start = chunk_end
                    overlap_buffer.clear()

        if current_chunk:
            add_chunk(chunks, current_chunk, overlap_buffer, chunk_start, chunk_end)

        video_data["chunks"] = chunks
        with open(os.path.join(output_dir, filename), "w") as file:
            json.dump(video_data, file, indent=2)


def add_chunk(chunks, current_chunk, overlap_buffer, chunk_start, chunk_end):
    """
    Adds a chunk to the list of chunks.

    Args:
        chunks: The list of chunks.
        current_chunk: The current chunk to be added.
        overlap_buffer: The buffer containing overlapping tokens.
        chunk_start: The start time of the chunk.
        chunk_end: The end time of the chunk.
    """
    current_chunk.extend(list(overlap_buffer))
    chunks.append(
        {
            "text": tokenizer.decode(current_chunk),
            "start": chunk_start,
            "end": chunk_end,
            "duration": chunk_end - chunk_start,
        }
    )


if __name__ == "__main__":
    chunk_transcripts()
