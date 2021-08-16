![Helios Logo](https://heliosmusic.io/application/files/thumbnails/large/4615/2807/9653/Helios-Logo.png "Helios Logo")

# Helios Client Utilities

This is a set of command line utilities for interacting with a [Helios](https://www.heliosmusic.io) server. You can use them to manage your music catalogue as well as perform similarity matches. They use the [python-helios-client](https://github.com/cartesiantheatre/python-helios-client) pure Python 3 module and can be used as examples for developing your own applications that use the Helios REST API.

## What is Helios?

Helios is a powerful B2B technology to allow searching of large commercial music libraries by using music itself as the search key. There are many uses, but here are a few examples:

- You have a commercial music library of any size. Perhaps you are a major record label, perhaps independent, or maybe you've amalgamated music from multiple labels, independent artists, or publishers. You need to assist your clients with obtaining synchronization licenses quickly for appropriate pieces of music for their film, TV, documentary, commercial, video game, or some other context.

- Your business receives a new supply of music each month from artists. You need to be able to predict which new music is more likely to generate revenue based on how existing music in your catalogue already performed.

- You have a digital jukebox in bars, restaurants, and pubs. You want venue patrons to be able to play more music like the music they just paid to hear.

- You have a music catalogue management platform that publishers and labels use to track their digital assets. Your customers want to be able to search within their own catalogue using your slick platform.

- You have an online digital music store and you'd like to be able to make intelligent product recommendations to your customers based on what songs they already have in their shopping cart before they check out.

- You have a streaming music service for different venues or channels. You have in-house DJs that custom curate the playlists. You want to reduce their work as they create new ones.

- You have a streaming music service. The listener asked to skip the current track, but they also never want to hear anything similar again.

- You market software for DJs, such as plugins to manage their library. While they're performing live, a plugin in their favourite software suggests new tracks to mix or play next.

There are countless other examples, but let's talk about the first one. Nearly always, your client approaches you with samples already in hand. "Hey, do you have anything like this?" This could be an MP3 or a YouTube video URL. Because Helios allows you to search the catalogue using music itself as the search key, you could use the customer's samples directly to help them find what they're looking for.

Traditionally, in the absence of such technology, the way this has been done for decades may surprise many. It is both costly and involves many hours or even days of manual human labour which delays the business process. The business must manually search, usually using [textual tags](https://heliosmusic.io/index.php/faq#tagging), and listen to a great deal of irrelevant music in the hopes of finding the one the client is actually willing to spend money on.

## Utilities Included

The following is a summary of the utilities included in this package. For detailed information on their usage consult their man page.

| Command | Description |
|---------|-------------|
| `helios-add-song` | Add a single song to a Helios server's catalogue. |
| `helios-delete-song` | Delete a remote song or songs on a Helios server. |
| `helios-download-song` | Download a song from a remote Helios server. |
| `helios-find-servers` | List all helios servers detected on your LAN. |
| `helios-get-song` | Query metadata for a song within a remote Helios server. |
| `helios-import-songs` | Batch import songs into Helios. |
| `helios-provision-magnatune` | Download Magnatune catalogue and generate CSV for helios-import-songs(1). |
| `helios-modify-song` | Tool to edit metadata of remote songs already analyzed on a Helios server. |
| `helios-similar` | Search for similar songs on a remote Helios server. |
| `helios-status` | Query the status of a remote Helios server. |

## Quick installation

### Ubuntu
Packages already prepared for Ubuntu 19.04 (disco) and later are available on our Personal Package Archive (PPA) [here](https://launchpad.net/%7Ekip/+archive/ubuntu/helios-public). To get the package installed and be up and running in seconds, just run the following two commands:

```console
$ sudo add-apt-repository ppa:kip/helios-public
$ sudo apt install helios-client-utilities
$ man helios
```

If you have one or more Helios servers running on your local area network (LAN), you can probe for it like so:
```console
$ helios-find-servers
```

To verify your Helios server is operational, run the following:
```console
$ helios-status --host <some_host_name_or_ip>
```
If you remove the `--host` switch and its argument `helios-status(1)` will automatically query the first `heliosd(1)` server it finds on your network.

## Documentation

For more documentation see the `helios(7)` man page.

```console
$ man helios
```

## Licensing

This package is released under the terms of the [GPL 3](https://www.gnu.org/licenses/gpl-3.0-standalone.html) or greater. Copyright (C) 2015-2021 Cartesian Theatre. See [Copying](./Copying) for more information.

