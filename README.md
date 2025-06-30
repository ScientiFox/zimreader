![image](https://github.com/user-attachments/assets/b9fc7978-d46d-41a7-8fe3-85275aaa1868)

A basic ZIM reader that's built up as a test utility from some of the background work on REDWOLF.AIC

It interfaces with a ZIM archive (ostensibly an offline archive of wikipedia), and pulls data from it

It implements two modes: one that strips out HTML while formatting the sections into labeled segments, which is set up to make pulling content for NLP systems easier and cleaner, referred to as the 'paredDown' mode; and a full HTML mode which displays the original formatting as best as the local browser can without access to internet-based CSS stuff.

The classes handle linking, cross-links, search, references, and most lookup errors internally, which is especially handy for other systems using it.

The main trick of it, outside the parsing function, is rebuilding the HTML links to be internal links. We do that by tricking the HTML, replacing 'a href' with a button whos id is the article we want to link, labeled in the ZIM format, and a call to a generic callback that grabs that id from the event and uses it to call a subsequent article pull 

There's also a built-in search and suggest routine which blocks inaccessible links from crashing it.

The main point is to work with other projects, but it'll be fun for passing time on airplanes!

**requires a ZIM file archive, not stored here because even without images they're like 60GB**
