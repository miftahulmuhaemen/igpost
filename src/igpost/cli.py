import argparse
import os
import sys
import json
import logging
from typing import Optional

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False

logger = logging.getLogger("igpost")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload a video to Instagram using saved session when valid; fallback to username/password. Also supports --profile to print account info.",
    )
    parser.add_argument(
        "-v",
        "--video",
        required=False,
        help="Path to the video file to upload",
    )
    parser.add_argument(
        "-d",
        "--description",
        required=False,
        help="Caption/description for the video",
    )
    parser.add_argument(
        "-u",
        "--username",
        required=False,
        help="Instagram username",
    )
    parser.add_argument(
        "-p",
        "--password",
        required=False,
        help="Instagram password",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="If set, prints current account info as JSON and exits",
    )
    parser.add_argument(
        "--session-file",
        default="session.json",
        help="Path to persist/restore instagrapi session settings (default: session.json)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging of steps",
    )
    return parser.parse_args(argv)


def configure_logging(verbose: bool) -> None:
    level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(level=level, format="[%(levelname)s] %(message)s")


def load_env_credentials(env_path: str = ".env") -> tuple[Optional[str], Optional[str]]:
    """Load username and password from .env file."""
    if not DOTENV_AVAILABLE:
        return None, None
    
    if not os.path.isfile(env_path):
        return None, None
    
    load_dotenv(env_path)
    username = os.getenv("IG_USERNAME") or os.getenv("USERNAME")
    password = os.getenv("IG_PASSWORD") or os.getenv("PASSWORD")
    
    return username, password


def validate_inputs_for_upload(video_path: Optional[str], caption: Optional[str]) -> None:
    if not video_path:
        raise ValueError("--video is required for upload")
    if not caption:
        raise ValueError("--description is required for upload")
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")


def try_login_with_session_then_password(client: Client, username: Optional[str], password: Optional[str], session_file: str) -> None:
    """
    Load settings from session_file if present, validate; otherwise or on failure, login via username/password.
    On success, dump updated settings to session_file.
    """
    # Be gentle to avoid detection
    client.delay_range = [1, 3]

    settings = None
    if os.path.isfile(session_file):
        try:
            logger.info("Loading session from %s", session_file)
            settings = client.load_settings(session_file)
        except Exception as e:
            logger.info("Could not load session settings: %s", e)
            settings = None

    logged_in_via_session = False
    logged_in_via_password = False

    if settings:
        try:
            logger.info("Applying loaded session settings")
            client.set_settings(settings)
            # Attempt auth using provided credentials to refresh cookies if needed
            if username and password:
                logger.info("Refreshing login with provided username/password")
                client.login(username, password)
            # Validate session
            try:
                logger.info("Validating session with timeline feed")
                client.get_timeline_feed()
            except LoginRequired:
                logger.info("Session invalid; attempting username/password login fallback")
                old_session = client.get_settings()
                client.set_settings({})
                if isinstance(old_session, dict) and "uuids" in old_session:
                    client.set_uuids(old_session["uuids"])
                if not (username and password):
                    raise LoginRequired("Session invalid and no credentials provided for fallback")
                client.login(username, password)
            logged_in_via_session = True
            logger.info("Authenticated via session")
        except Exception as e:
            logger.info("Session-based auth failed: %s", e)
            logged_in_via_session = False

    if not logged_in_via_session:
        if not (username and password):
            raise ValueError("Username and password are required when no valid session is available")
        logger.info("Attempting direct username/password login")
        client.set_settings({})
        try:
            client.set_uuids({})
        except Exception:
            # Ignore if API changes
            pass
        client.login(username, password)
        logged_in_via_password = True
        logger.info("Authenticated via username/password")

    # Persist working settings
    try:
        logger.info("Persisting session to %s", session_file)
        client.dump_settings(session_file)
    except Exception as e:
        logger.info("Failed to persist session: %s", e)


def upload_video(client: Client, video_path: str, caption: str) -> str:
    logger.info("Uploading video: %s", video_path)
    media = client.clip_upload(video_path, caption)
    media_code = getattr(media, "code", None)
    if media_code:
        url = f"https://www.instagram.com/p/{media_code}/"
        logger.info("Upload succeeded: %s", url)
        return url
    logger.info("Upload completed without code")
    return ""


def print_account_info_json(client: Client) -> None:
    info = client.account_info()
    # Prefer Pydantic v2 method; fallback to v1; final fallback to default=str
    try:
        json_text = info.model_dump_json()  # type: ignore[attr-defined]
        print(json_text)
        return
    except Exception:
        pass
    try:
        print(info.json())
        return
    except Exception:
        pass
    try:
        # As a last resort
        from pydantic.json import pydantic_encoder  # type: ignore

        print(json.dumps(info.dict(), default=pydantic_encoder, ensure_ascii=False))
        return
    except Exception:
        # Ultimate fallback: stringify unknown objects
        print(json.dumps(info.dict(), default=str, ensure_ascii=False))


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        # Load credentials with priority: .env file -> system env vars -> command line args
        username = args.username
        password = args.password
        
        # Try .env file first
        env_username, env_password = load_env_credentials()
        if env_username and env_password:
            logger.info("Using credentials from .env file")
            username, password = env_username, env_password
        elif not username and not password:
            # Try system environment variables as fallback
            username = os.getenv("IG_USERNAME")
            password = os.getenv("IG_PASSWORD")
            if username and password:
                logger.info("Using credentials from system environment variables")

        client = Client()
        logger.info("Starting authentication flow")
        try_login_with_session_then_password(
            client,
            username=username,
            password=password,
            session_file=args.session_file,
        )

        if args.profile:
            logger.info("Fetching account profile info")
            print_account_info_json(client)
            return 0

        validate_inputs_for_upload(args.video, args.description)
        post_url = upload_video(client, args.video, args.description)
        if post_url:
            print(post_url)
        else:
            print("Upload complete.")
        return 0
    except (ValueError, FileNotFoundError) as known_err:
        print(str(known_err), file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
