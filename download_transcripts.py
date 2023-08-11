import os
import click
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from tqdm import tqdm
from colorama import Fore, Style
import json

# You need to set up your own YouTube Data API key and insert it here
API_KEY = os.environ["YOUTUBE_API_KEY"]


def get_video_ids_from_playlist_url(url):
    """Extract video IDs from a given YouTube playlist URL."""
    youtube = build("youtube", "v3", developerKey=API_KEY)
    playlist_id = url.split("list=")[-1]
    request = youtube.playlistItems().list(
        part="snippet",
        maxResults=50,
        playlistId=playlist_id,
    )
    response = request.execute()
    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in response["items"]]
    while "nextPageToken" in response:
        request = youtube.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=playlist_id,
            pageToken=response["nextPageToken"],
        )
        response = request.execute()
        video_ids += [
            item["snippet"]["resourceId"]["videoId"] for item in response["items"]
        ]
    return video_ids


def get_video_ids_from_channel_url(url):
    """Extract video IDs from a given YouTube channel URL."""
    youtube = build("youtube", "v3", developerKey=API_KEY)

    channel_name = url.rsplit("/", 1)[-1]
    request = youtube.channels().list(part="contentDetails", forUsername=channel_name)
    response = request.execute()

    # Check if the channel was found
    if not response["items"]:
        raise ValueError(f"No channel found with name {channel_name}")

    uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"][
        "uploads"
    ]

    request = youtube.playlistItems().list(
        part="snippet",
        maxResults=50,
        playlistId=uploads_playlist_id,
    )
    response = request.execute()
    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in response["items"]]
    while "nextPageToken" in response:
        request = youtube.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=uploads_playlist_id,
            pageToken=response["nextPageToken"],
        )
        response = request.execute()
        video_ids += [
            item["snippet"]["resourceId"]["videoId"] for item in response["items"]
        ]
    return video_ids


def get_video_ids(url):
    """Determine if the URL is for a playlist or a channel, and call the appropriate function."""
    if "playlist" in url:
        return get_video_ids_from_playlist_url(url)
    elif "youtube.com/" in url:
        return get_video_ids_from_channel_url(url)
    else:
        raise ValueError(
            "Invalid YouTube URL. Please provide a URL for a playlist or a channel."
        )


def get_video_ids_and_metadata(url):
    """Determine if the URL is for a playlist or a channel, and call the appropriate function."""
    if "playlist" in url:
        return get_video_metadata_from_playlist_url(url)
    elif "youtube.com/" in url:
        return get_video_metadata_from_channel_url(url)
    else:
        raise ValueError(
            "Invalid YouTube URL. Please provide a URL for a playlist or a channel."
        )


def get_video_metadata_from_playlist_url(url):
    """Extract video metadata from a given YouTube playlist URL."""
    youtube = build("youtube", "v3", developerKey=API_KEY)
    playlist_id = url.split("list=")[-1]
    request = youtube.playlistItems().list(
        part="snippet",
        maxResults=50,
        playlistId=playlist_id,
    )
    response = request.execute()
    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in response["items"]]
    video_metadata = [item["snippet"] for item in response["items"]]
    while "nextPageToken" in response:
        request = youtube.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=playlist_id,
            pageToken=response["nextPageToken"],
        )
        response = request.execute()
        video_ids += [
            item["snippet"]["resourceId"]["videoId"] for item in response["items"]
        ]
        video_metadata += [item["snippet"] for item in response["items"]]
    return video_ids, video_metadata


def get_video_metadata_from_channel_url(url):
    """Extract video IDs and metadata from a given YouTube channel URL."""
    youtube = build("youtube", "v3", developerKey=API_KEY)

    channel_name = url.rsplit("/", 1)[-1]
    request = youtube.channels().list(part="contentDetails", forUsername=channel_name)
    response = request.execute()

    # Check if the channel was found
    if not response["items"]:
        raise ValueError(f"No channel found with name {channel_name}")

    uploads_playlist_id = response["items"][0]["contentDetails"]["relatedPlaylists"][
        "uploads"
    ]

    request = youtube.playlistItems().list(
        part="snippet",
        maxResults=50,
        playlistId=uploads_playlist_id,
    )
    response = request.execute()

    video_ids = [item["snippet"]["resourceId"]["videoId"] for item in response["items"]]
    video_metadata = [item["snippet"] for item in response["items"]]

    while "nextPageToken" in response:
        request = youtube.playlistItems().list(
            part="snippet",
            maxResults=50,
            playlistId=uploads_playlist_id,
            pageToken=response["nextPageToken"],
        )
        response = request.execute()

        video_ids += [
            item["snippet"]["resourceId"]["videoId"] for item in response["items"]
        ]
        video_metadata += [item["snippet"] for item in response["items"]]

    return video_ids, video_metadata


def download_transcripts(video_ids, video_metadata, output_path):
    """Download transcripts for a list of video IDs."""
    print(Fore.GREEN + "Downloading transcripts..." + Style.RESET_ALL)

    for video_id, metadata in zip(
        tqdm(video_ids, bar_format="{l_bar}{bar:20}{r_bar}{bar:-20b}"), video_metadata
    ):
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = transcript_list.find_generated_transcript(["en"])
            os.makedirs(output_path, exist_ok=True)
            with open(os.path.join(output_path, f"{video_id}.json"), "w") as f:
                video_info = metadata
                video_info["transcript"] = []
                video_info["url"] = f"https://youtube.com/watch?v={video_id}"

                for line in transcript.fetch():
                    video_info["transcript"].append(
                        {
                            "text": line["text"],
                            "start": line["start"],
                            "duration": line["duration"],
                        }
                    )
                json.dump(video_info, f)
        except Exception as e:
            print(
                Fore.RED
                + f"Failed to download transcript for video {video_id}: {e}"
                + Style.RESET_ALL
            )


@click.command()
@click.argument("url")
@click.argument("output_path")
def main(url, output_path):
    """Main function to be run from the command line."""
    print(Fore.GREEN + "Fetching video IDs and metadata..." + Style.RESET_ALL)
    video_ids, video_metadata = get_video_ids_and_metadata(url)
    download_transcripts(video_ids, video_metadata, output_path)
    print(Fore.GREEN + "Done!" + Style.RESET_ALL)


if __name__ == "__main__":
    main()
