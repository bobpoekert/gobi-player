youtube-dl as an android library
---

When I say youtube-dl I literally mean youtube-dl. It packages the python interpreter as a jni extnesion and builds a sort of rpc interface on top of it to talk to youtube-dl.

As a user you don't need to think about python, though, all you have to do is call `PyBridige.resolveUrl`.

This lets you get all the information you need to be able to play videos from a huge list of websites without having to maintain your own scrapers.
