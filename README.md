![Helios Logo](https://heliosmusic.io/application/files/4615/2807/9653/Helios-Logo.png "Helios Logo")

# Helios Client Utilities

This is a set of command line utilities for interacting with a [Helios](https://www.heliosmusic.io) server. You can use them to manage your music catalogue as well as perform similarity matches. They use the [python-helios-client](https://github.com/cartesiantheatre/python-helios-client) pure Python 3 module and can be used as examples for developing your own applications that use the Helios REST API.

## What is Helios?

Helios is a powerful B2B technology to allow searching of large commercial music libraries by using music itself as the search key. There are many uses, but here are a few examples:

- You have a commercial music library of any size. Perhaps you are a major record label, perhaps independent, or maybe you've amalgamated music from multiple labels, independent artists, or publishers. You need to assist your clients obtain synchronization licenses quickly for appropriate pieces of music for their film, TV, documentary, commercials, video games, or some other context.

- You have a digital jukebox in bars, restaurants, and pubs. You want venue patrons to be able to play more music like whatever they just paid to hear.

- You have a music catalogue management platform that publishers and labels use to track their digital assets. Your customers want to be able to search within their own catalogue using your slick platform.

- You have an online digital music store and you'd like to be able to make intelligent product recommendations to your customers based on what songs they've already got in their shopping cart before they check out.

- You have a streaming music service whose DJs need inspiration for coming up with either channel based or custom curated playlists faster.

- You market software for DJs, such as plugins to manage their library. While they're playing live a plugin in their favourite software suggests some tracks to mix or play next.

There are countless other examples, but let's talk about the first one. Nearly always your client approaches you with samples already in hand. "Hey, do you have anything like this?" This could be an MP3 or a YouTube video URL. Because Helios allows you to search the catalogue using music itself as the search key, you could use the customer's samples directly to help them find what they're looking for.

Traditionally, in the absence of such technology, the way this has been done for decades may surprise many. It is both costly and involves many hours or even days of manual human labour which delays the business process. The business must manually search, usually using [textual tags](https://heliosmusic.io/index.php/faq#tagging), and listen to a great deal of irrelevant music in the hopes of finding the one the client is actually willing to spend money on.

## Utilities Included

The following is a summary of the utilities included in this package. For detailed information on their usage consult their man page.

`helios-add-song`: Add a single song to a Helios server's catalogue.
`helios-delete-song`: Delete a remote song or songs on a Helios server.
`helios-download-song`: Download a song from a remote Helios server.
`helios-find-servers`: List all helios servers detected on your LAN.
`helios-get-song`: Query metadata for a song within a remote Helios server.
`helios-import-songs`: Batch import songs into Helios.
`helios-modify-song`: Tool to edit metadata of remote songs already analyzed on a Helios
`helios-similar`: Search for similar songs on a remote Helios server.
`helios-status`: Query the status of a remote Helios server.

## Licensing

This package is released under the terms of the [GPL 3](https://www.gnu.org/licenses/gpl-3.0-standalone.html) or greater. Copyright (C) 2015-2019 Cartesian Theatre. See [Copying](./Copying) for more information.

