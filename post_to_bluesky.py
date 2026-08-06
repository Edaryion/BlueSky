# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime, timezone

import requests

QUOTES_FILE = "quotes.json"
STATE_FILE = "state.json"
PDS_HOST = "https://bsky.social"
MAX_LEN = 300

FOOTER = (
    "\U0001F499\U0001F4DA\U0001F4DA\U0001F440\U0001F308\U0001F4DA\U0001F411\U0001F4D6\n"
    "\U0001F4DA\U0001F30E\U0001F4E2\U0001F4DA\U000023F0\U0001F4DA\U0001F4A1\U0001F4DA\n"
    "\U0001D402\U0001D428\U0001D427\U0001D42D\U0001D41E\U0001D426\U0001D429\U0001D425"
    "\U0001D41A\U0001D42D\U0001D422\U0001D428\U0001D427\U0001D42C: \n"
    "istina.vision/b/contemplations"
)
SEPARATOR = "\n\n"


def load_json(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def format_post(quote_text):
    return f"{quote_text.strip()}{SEPARATOR}{FOOTER}"


def find_next_postable_quote(quotes, state):
    if not quotes:
        raise SystemExit("quotes.json is empty. Add at least one quote first.")

    start = state.get("next_index", 0) % len(quotes)
    for offset in range(len(quotes)):
        idx = (start + offset) % len(quotes)
        text = quotes[idx]["text"]
        full = format_post(text)
        if len(full) <= MAX_LEN:
            state["next_index"] = (idx + 1) % len(quotes)
            return full
    raise SystemExit(
        "No quote in quotes.json fits under the 300-character limit "
        "once the footer is added -- add some shorter ones."
    )


def main():
    handle = os.environ["BLUESKY_HANDLE"]
    app_password = os.environ["BLUESKY_APP_PASSWORD"]

    quotes = load_json(QUOTES_FILE, [])
    state = load_json(STATE_FILE, {"next_index": 0})

    post_text = find_next_postable_quote(quotes, state)

    session_resp = requests.post(
        f"{PDS_HOST}/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
        timeout=30,
    )
    session_resp.raise_for_status()
    session = session_resp.json()

    record = {
        "$type": "app.bsky.feed.post",
        "text": post_text,
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        + "Z",
        "langs": ["en"],
    }

    create_resp = requests.post(
        f"{PDS_HOST}/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {session['accessJwt']}"},
        json={
            "repo": session["did"],
            "collection": "app.bsky.feed.post",
            "record": record,
        },
        timeout=30,
    )
    create_resp.raise_for_status()

    save_json(STATE_FILE, state)
    print(f"Posted ({len(post_text)} chars):\n{post_text}")


if __name__ == "__main__":
    main()
