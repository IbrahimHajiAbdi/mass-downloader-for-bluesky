# mass-downloader-for-bluesky

mass-downloader-for-bluesky (mdfb) is a Python cli application that can download large amounts of posts from bluesky from any given account.

## Installation

You will need [Python](https://www.python.org/downloads/) to be installed to use this CLI.

You can install via pip by:
```bash
pip install mdfb
```

### Manual

Have [Poetry](https://python-poetry.org/) installed. 

Then clone the project, open a poetry shell and then install all dependencies.


```bash
git clone git@github.com:IbrahimHajiAbdi/mass-downloader-for-bluesky.git
cd mdfb
poetry shell
poetry install
```

## Usage
``mdfb`` works by using the public API offered by bluesky to retrieve posts liked, reposted or posted by the desired account. 

``mdfb`` will download the information for a post and the accompanying media, video or image(s). If there is no image(s) or video, it will just download the information of the post. The information of the post will be a JSON file and have lots of accompanying data, such as the text in the post, creation time of the post and author details. Currently, the retrieved posts start from the latest post to the oldest.

You will need to be inside a poetry shell to use ``mdfb`` if installed manually

### Examples

Some example commands would be:

```bash
mdfb download --handle bsky.app -l 10 --like --threads 3 --format "{RKEY}_{HANDLE}" ./media/
```

```bash
mdfb download -d did:plc:z72i7hdynmk6r22z27h6tvur --archive --like --threads 3 --format "{DID}_{HANDLE}" ./media/
```

```bash
mdfb download --handle bsky.app --update --like --threads 3 --format "{RKEY}_{HANDLE}" ./media/
```

```bash
mdfb download --restore bsky.app --like --threads 3 --format "{RKEY}_{HANDLE}" ./media/
```

### Naming Convention
By default, ``mdfb``'s naming convention is: ``"{rkey}_{handle}_{text}"``. If it is downloading a post with multiple images then the naming will be: ``"{rkey}_{handle}_{text}_{i}"``, where "i" represents the order of the images in the post ranging from 1 - 4. In addition, the filenames are limited to 256 bytes and will be truncated down to that size. 

However, you can specify the name of the files by using the ``--format`` flag and passing a valid format string, e.g. ``"{RKEY}_{DID}"``. You can put anything in the format string **inbetween the keywords**. This is **case-sensitive**.

For ``--format``, the valid keywords are:
- ``RKEY`` 
- ``DID`` 
- ``HANDLE`` 
- ``TEXT`` 
- ``DISPLAY_NAME`` 

### Download Amount
When specifying the limit, this will be true for all types of post downloaded. For example: 
```bash
mdfb download --handle bsky.app -l 100 --like --repost --post ./media/
```
This would download 100 likes, reposts and post, totalling 300 posts downloaded.

Furthermore, you can archive whole accounts. For exmaple:
```bash
mdfb download --handle bsky.app --archive --like --repost --threads 3 --format "{DID}_{HANDLE}" ./media/
```

This would download all likes and reposts.

### Database
When downloading posts, `mdfb` inserts into the database some post identifiers. This allows for you to download only new posts from an account that you haven't downloaded yet. 

However, there are some constraints, if you delete a file, this is not reflected in the database and thus, if you use the ``--update`` flag, it will not redownload it. Furthermore, the posts identifiers are only committed to the database once all posts have been downloaded, so if `mdfb` topples over during downloading, none of the posts downloaded will be reflected into the database.

The database is stored in: (Linux) `~/.local/share/mdfb/`, (Windows) `C:\\Users\\$USER\\AppData\\Local\\mdfb` and (macOS) `/Users/$USER/Library/Application Support/mdfb`.

#### Example
```bash
mdfb db --delete_user bsky.app
``` 

### Feed
When using the ``feed`` subcommand ,there are a few quirks. One of them being that since it is a generator there is not guaranteed order that the posts will be returned. This has the implication of doing the same command will likely produce different sets of downloaded content. This is up the person who owns the feed and how they decide it is generated.

Furthermore, you need to login using the ``login`` subcommand, this requires you to generate a app password for the account you want to authenticate as. The subcommand ``login`` is only required when using the ``feed`` subcommand. The app password will be valid as long as the password for the account does not change or is revoked by the user. The subcommand ``feed`` will use the app password provided until changed.

There can be multiple accounts in the config yaml with their own app password.

You can generate an app password [here](https://bsky.app/settings/app-passwords).

The config yaml is stored in: (Linux) `~/.config/mdfb/`, (Windows) `C:\\Users\\$USER\\AppData\\Local\\mdfb` and (macOS) `/Users/$USER/Library/Application Support/mdfb`.

### Note
**IMPORTANT**: When using the ``feed`` subcommand, **None of the posts downloaded will be added to the database**. Meaning that the ``update`` flag cannot be used and if the same posts pops up on someone elses feed, it will be downloaded.

#### Example
```bash
mdfb feed --handle bsky.app --url 'https://bsky.app/profile/bsky.app/feed/whats-hot' --limit 100 media/ -t 3 
```

### Note
The maximum number of threads is currently 3, that can be changed in the ``mdfb/utils/constants.py`` file. Furthermore, there are more constants that can be changed in that file, such as delay between each request and the number of retries before marking that post as a failure and continuing.

## Subcommands and arguments
- ``download`` 
  - ``--handle``
    - The handle of the target account.
  - ``--did, -d``
    - The DID of the target account. 
  - ``--limit, -l``
    - The amount of posts that want to be downloaded.
  - ``--archive``
    - Downloads all posts from the selected post type.
  - ``--update, -u``
    - Downloads **all** of the latest posts that haven't been downloaded. 
  - ``directory``
    - Positional argument, where all the downloaded files are to be located. **Required**.
  - ``--threads, -t``
    - The amount of threads wanted to download posts more efficiently, maximum number of threads is 3.
  - ``--format, -f``
    - Format string that file's will use for their name. Furthermore the keywords used are **case-sensitive** and should be all upper case.
  - ``--like``
    - To retrieved liked posts
  - ``--repost``
    - To retrieved reposts
  - ``--post``
    - To retrieved posts
  - ``--media-types``
    - Only download posts that contain this specified type of media. Valid keywords are: **image, video and text**.
  - ``--include, -i``
    - Whether to include **only** json information or media from the post.
  - ``--restore``
    - Downloads all posts stored in the database, can optionally pass a did or handle to only restore posts from that account.
- ``db``
  - ``--delete_user``
    - Deletes all posts associated with the given user from the database. Have to pass the **handle** of the user. 
- ``login``
  - This is only a subcommand and is needed to use ``fetch`` subcommand, needed to add the app password which can be found [here](https://bsky.app/settings/app-passwords)
- ``feed``
  - ``--url``
    - The URL of the feed, e.g. https://bsky.app/profile/skyfeed.xyz/feed/mutuals. **Required**.
  - ``--handle``
    - Handle of the user to login in as. **Required**.
  - ``--limit, -l``
    - Number of posts to download. **Required**.
  - ``--media-types``
    - Only download posts that contain this specified type of media. Valid keywords are: **image, video and text**.
  - ``--include, -i``
    - Whether to include **only** json information or media from the post.
  - ``directory``
    - Positional argument, where all the downloaded files are to be located. **Required**.

  
- ``generic commands``
  - ``--resource, -r``
    - Logs resource usage for memory and cpu every 5 seconds. 

### Note
At least one of the flags: ``--like``, ``--repost``, ``--post`` are **required** (when using `download`).

Both (``--did, -d`` and ``--handle``) and (``--archive``, ``--limit, -l`` and ``--update``) are mutually exclusive, and one of each of them is **required** as well (when using `download`).

The argument ``--media-types`` **needs** to be either before or after any positional arguments. 
E.g. 
```bash
mdfb download --handle bsky.app --update --like --threads 3 --media-types image --format "{RKEY}_{HANDLE}" ./media/`
```

Furthermore, if you want to filter by text and image or media and then use `--include` by media, this would not include any post filter by text. E.g.
```bash
mdfb download --handle bsky.app --update --like --threads 3 --media-types image text -i media ./media/`
```
This would just download images only.

When using ``feed``, another example of a valid command is:
```bash
mdfb feed --handle bsky.app --url 'https://bsky.app/profile/bsky.app/feed/whats-hot' --limit 5 media/ -t 3 --media-types video --include media
```
This would download the first 5 posts that contain a video and only download the media, not the accompanying metadata json