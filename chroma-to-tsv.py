import click
import csv
import chromadb
from chromadb.config import Settings
from tqdm import tqdm
import logging

# Use colorful logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger()
# Create a list of colors for different levels
colors = ["purple", "cyan", "blue", "green", "yellow", "red"]
for level, color in zip(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], colors):
    logging.addLevelName(
        getattr(logging, level),
        f"\033[{color}m%s\033[0m" % logging.getLevelName(getattr(logging, level)),
    )

# Initialize chroma client and create collection
chroma_client = chromadb.Client(
    Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma.db")
)
collection = chroma_client.get_or_create_collection(name="aquarium-co-op-youtube")


@click.command()
@click.argument("embeddings_output")
@click.argument("metadata_output")
def export(embeddings_output, metadata_output):
    """
    This function exports all embeddings and corresponding metadata from
    a ChromaDB collection into two TSV files. The embeddings are exported
    into `embeddings_output` and the metadata into `metadata_output`.

    Parameters:
    embeddings_output (str): The output file path for the embeddings.
    metadata_output (str): The output file path for the metadata.
    """
    logging.info("Starting export process...")
    with open(embeddings_output, "w", newline="") as embeddings_file, open(
        metadata_output, "w", newline=""
    ) as metadata_file:
        embeddings_writer = csv.writer(embeddings_file, delimiter="\t")
        metadata_writer = csv.writer(metadata_file, delimiter="\t")

        # Write the headers for metadata.tsv
        metadata_writer.writerow(
            ["id", "document", "title", "video_id", "thumbnail", "url"]
        )
        logging.info("Metadata headers written.")

        # Initialize offset
        offset = 0
        while True:
            logging.info(f"Fetching batch starting from offset {offset}...")
            # Query the batch of embeddings and metadata from the ChromaDB collection
            data = collection.get(
                limit=1000,
                offset=offset,
                include=["documents", "metadatas", "embeddings"],
            )
            # If the query returned no data, we've reached the end of the collection
            if not data["ids"]:
                break

            logging.info(f"Writing data to files...")
            for id, embedding, document, metadata in tqdm(
                zip(
                    data["ids"],
                    data["embeddings"],
                    data["documents"],
                    data["metadatas"],
                )
            ):
                # Write the embeddings
                embeddings_writer.writerow(embedding)

                # Write the metadata
                metadata_writer.writerow(
                    [
                        id,
                        document,
                        metadata["title"],
                        metadata["video_id"],
                        metadata["thumbnail"],
                        metadata["url"],
                    ]
                )

            # Increment the offset for the next batch
            offset += 1000
            logging.info(f"Batch written. Updating offset to {offset}...")
        logging.info("Export process completed successfully.")


if __name__ == "__main__":
    export()
