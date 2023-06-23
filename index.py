import click
import json
from tqdm import tqdm

import chromadb
from chromadb.config import Settings

# Initialize chroma client and create collection
chroma_client = chromadb.Client(
    Settings(chroma_db_impl="duckdb+parquet", persist_directory="./chroma.db")
)
collection = chroma_client.get_or_create_collection(name="aquarium-co-op-youtube")


@click.command()
@click.argument("input_file")
def index_file(input_file):
    # Count the lines in the file for the progress bar
    num_lines = sum(1 for _ in open(input_file))

    embeddings_batch = []
    documents_batch = []
    metadata_batch = []
    ids_batch = []
    batch_size = 1000

    with open(input_file, "r") as infile:
        for line in tqdm(infile, total=num_lines):
            entry = json.loads(line)
            embeddings_batch.append(entry["embedding"])
            documents_batch.append(entry["text"])
            metadata_batch.append(entry["metadata"])
            ids_batch.append(entry["id"])

            if len(embeddings_batch) >= batch_size:
                collection.add(
                    embeddings=embeddings_batch,
                    documents=documents_batch,
                    metadatas=metadata_batch,
                    ids=ids_batch,
                )
                embeddings_batch.clear()
                documents_batch.clear()
                ids_batch.clear()
                metadata_batch.clear()

        # add the remaining entries if they didn't reach the batch_size
        if embeddings_batch:
            collection.add(
                embeddings=embeddings_batch,
                documents=documents_batch,
                ids=ids_batch,
                metadatas=metadata_batch,
            )


if __name__ == "__main__":
    index_file()
