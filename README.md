# igpost

Instagram video uploader CLI using instagrapi.

## Prerequisites
- Python 3.9+
- `uv` installed

## Install dependencies
```bash
uv sync
```

## Usage
```bash
uv run igpost -v /path/to/video.mp4 -d "Your caption here" -s "<session_id>"
```

Arguments:
- `-v, --video`: Path to the video file to upload
- `-d, --description`: Caption/description for the post
- `-s, --session`: Instagram `sessionid` cookie value

Notes:
- This uses `Client.login_by_sessionid` and posts via private API from `instagrapi`.
- Library reference: https://github.com/subzeroid/instagrapi
