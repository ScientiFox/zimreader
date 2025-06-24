#Standards
import math,time,random

#File ops
import glob

#Internet things
import asyncio,websockets
import webbrowser
from urllib.parse import unquote
from html.parser import HTMLParser

#Archive specific things
from libzim.reader import Archive
from libzim.search import Query, Searcher
from libzim.suggestion import SuggestionSearcher


class MyHTMLParser(HTMLParser):
    #A parser- extends the base class
    #   Intended to strip HTML down to the bones so we can prep it
    #   for NLP stuff, but leaves things to sort sections and tables

    def make_vars(self):
        #Variables for a document parsing
        self.dat = []
        self.dat_out = []
        self.prev_tag = None
        
    def handle_starttag(self, tag, attrs):
        #Not using this part of the template
        pass

    def handle_endtag(self, tag):
        #Not using this part of the template
        pass

    def handle_data(self, data):
        #Basic handler to read things in and strip stuff we don't use

        #Grab the start
        tag_text = self.get_starttag_text()
        if tag_text != None: #While something's in there
            if not("<style " in tag_text): #avoid CSS stuff
                #For a new tag that's not basic formatting:
                if (tag_text != self.prev_tag) and (not(tag_text in ['<i>','<b>','<p>'])):
                    self.dat = self.dat + [[tag_text,data,""]] #Add in the tag, innerHTML, and ""
                else:
                    self.dat = self.dat + [["<>",data,tag_text]]#Save non-primary tags to latter element there
                self.prev_tag = tag_text #Keep track of the last tag
            else:
                pass #Do nothing for CSS
        else:
            pass #do nothing for empty tags, what even are they doing in there??

    def get_parsed(self,text):
        #The actual parser once the tag and data lists are made

        self.make_vars() #Setup the variables for this DOC
        self.feed(text) #Man, I wish I remember what this does

        #flags for preceeding newlines and tag types
        prev_nl = False
        prev_tag = None

        #Sequential variables
        curr_text = "" #Text you're working on
        sections = [] #Actual article sections
        curr_section = "" #current section being built
        curr_links = [] #Links found in this section
        title = None #Title of the article
        isData = False #Flag for if the text snip is data in a table

        #We format the output as raw HTML with internal lookup links made, using these bits
        buttonHTML1 = '<span id='
        buttonHTML2 = ' onclick="linkClicked(event);" style="color:blue;">'
        buttonHTML3 = '</span>'

        #Looping through all the tag/data/secondary tags:
        for a in self.dat:
            #print(a[0],"|",a[1][:15],"... |",a[2]) #Diagnostic.

            #Class that marks the start of a table zone
            if "mw-empty-elt" in a[0]:
                curr_text = curr_text + "--------\n" #mark off table space

            #Tage that denotes upcoming table data
            if 'class="fn"' in a[0]:
                isData=True

            #End of the table div, when we know we're in it, is the following paragraph
            if (isData) and (a[2] == '<p>'):
                curr_text = curr_text + "--------\n"
                isData = False
                
            #compactify down newlines, there's a lot of them
            if sum([(i in ['\n',' ']) for i in a[1]]) == len(a[1]):
                a[1] = '\n'

            #if there's not a newling before it, or there is but not another one in the current one, we
            # have a new line to parse into text
            if prev_nl == True:
                if not('\n' in a[1]):
                    to_add = True
                else:
                    to_add = False
            else:
                to_add = True

            #When we do have proper lines to add:
            if to_add:
                self.dat_out = self.dat_out + [a] #Save the output raw data for posterity

                #Found the page title, note it and start up the initial section
                if "<title>" == a[0]:
                    title = a[1]

                    curr_section = '<h2>' + a[1] + '</h2>'
                    curr_links = []
                    curr_text = ""

                #found a link- insert it into the pared down HTML
                elif 'a href' in a[0]:
                    lnk = a[0].split("=")[1]
                    curr_text = curr_text + buttonHTML1 + lnk + buttonHTML2 + a[1] + buttonHTML3 + " "
                    curr_links = curr_links + [lnk]

                #found a section header, pack off the previous section and make a new one
                elif 'h2 id' in a[0]:
                    sect = (curr_section,curr_text,curr_links)
                    sections = sections + [sect]

                    curr_section = '<h3>' + a[1] + '</h3>'
                    curr_links = []
                    curr_text = ""

                #A label in a table, add it with a spacing newline
                elif 'infobox-label' in a[0]:
                    curr_text = curr_text + "\n" + a[1] + " "

                #actual data from a table, go back, strip the whitespace, add a ":" to look nice-ish
                elif 'infobox-data' in a[0]:
                    if curr_text[-1] == " ":
                        curr_text = curr_text[:-1]
                    curr_text = curr_text + ": " + a[1]

                #Don't include table captions or the starting formatting in the actual text
                elif ('infobox-caption' in a[0]) or (('class="fn"') in a[0]) or ("mw-page-title-main" in a[0]):
                    pass

                #First element of a list! remove newlines and add a ':'
                elif '<li>' == a[0]:
                    if curr_text[-1] == '\n':
                        curr_text = curr_text[:-1] + ": "
                    curr_text = curr_text + a[1] + "\n"

                #Non-initial elements of lists, handle the commas
                elif (a[0] == '<>') and ('<li>' == a[2]):
                    if curr_text[-1] == '\n':
                        curr_text = curr_text[:-1] + ", "
                    curr_text = curr_text + a[1]

                #Everything else is just text
                else:
                    curr_text = curr_text + a[1]

            #Check if there's a newline there for the flag
            if '\n' in a[1]:
                prev_nl = True
            else:
                prev_nl = False
        #Return all the constructed sections
        return sections

class archive:
    #Object to wrap the archive, and keep track of searches and things

    def __init__(self,_location):
        #Start up by building all the needed assests

        self.parser = MyHTMLParser() #HTML parser from above
        self.location = _location #ZIM file address
        self.archive = Archive(self.location) #Make an actual zim archive
        self.searcher = Searcher(self.archive) #Make a zim searcher
        self.suggestor = SuggestionSearcher(self.archive) #make a zim suggestor

        #We have two modes: paredDown and full- the former uses the parser above to strip for NLP
        # the latter just returns wiki html for visibility.
        self.mode = "paredDown"

        self.queries = [] #query history for later

    def search(self,target,num=20):
        #Search for articles

        #Make a query for the supplied target string
        self.query = Query().set_query(target)
        self.queries = self.queries + [self.query] #update query history

        #Grab the search results and estimated matches
        self.results = self.searcher.search(self.query)
        self.search_count = self.results.getEstimatedMatches()

        #Return a proper list form of the results- up to the limit number specified
        return list(self.results.getResults(0,num))

    def suggestions(self,target,num=20):
        #Basic wrapper to snag article suggestions from a search string
        self.recommended = self.suggestor.suggest(target)
        return list(self.recommended.getResults(0,num))

    def pull_article(self,link):
        #wrapper to grab an article from a provided actual link
        entry = self.archive.get_entry_by_path(link)
        entry = bytes(entry.get_item().content).decode("UTF-8") #decode from TCPspeak
        return entry

    def grab_art(self,link):
        #Function to get an article, based on the mode
        entry = arc.pull_article(link)
        if self.mode == "paredDown":
            art_out = self.parser.get_parsed(entry) #apply the parser for this mode
        else:
            art_out = entry #return html standard for this one
        return art_out

    def get_link(self,link):
        #Function to grab an actual article link from list title

        elem = link.split(" ") #separate actual string from label
        humanTitle = elem[0][1:-1].replace("_"," ") #remove outer "" and swap _ for space
        if elem[-1] == 'title': #If it actually is a title, not a URL
            lnk = 'A/' + elem[0][1:-1] #Make it an article link
        else:
            return (False,elem[0][1:-1]) #otherwise it's something else, just return it whole

        hasOne = self.archive.has_entry_by_title(humanTitle) #Check if the article can be found
        if hasOne:
            return (hasOne,lnk) #If so, return it and the valid link
        else:
            return (hasOne,self.suggestions(humanTitle)) #otherwise, pull suggestions and return those

#Running server on localhost 
HOST = "127.0.0.1"
PORT = 8080

#To handle client requests
async def handle_client(websocket):
    global arc #Global for the archive object

    try: #mostly for checking open connection

        #For all the received messages
        async for message in websocket:
            print("received:",message) #Report the message- diagnostic

            resp = '' #Start off with nothing to respond, it will be the HTML to display

            #We use start characters to denote the message type
            #   & is for changing the display mode
            if message[0] == "&": 
                if message[1] == "1": #sending 1 sets it to full mode
                    arc.mode = "full"
                else: #0 sets it to pared down mode
                    arc.mode = "paredDown"
                resp = "&done" #Response is a formality here

            #When we're in pared down mode
            elif arc.mode == 'paredDown':

                #set the response to be a div with the half text type for spacing
                resp = '<div id="mainBlock" class="halfTxt">'

                #A $ indicates a search request
                if message[0] == '$':
                    suggest = arc.suggestions(message[1:]) #suggest from the search string
                    resp = resp + "<h4>Search hits:</h4> <br/>" #it'll be a list
                    for sugg in suggest: #Put each suggestion in a list as a clickable text chunk
                        s_txt = sugg[2:].replace("_"," ") #don't display the links with '_'s
                        resp = resp + "<span id=\""+sugg+"\" onclick=\"linkClicked(event);\" style=\"color:blue;\">" + s_txt + "</span> <br/>"

                # % indicates a link click
                elif message[0] == '%':
                    sections = arc.grab_art(unquote(message[1:])) #pull the article from the link ID clicked- unquote de-UTF8s it
                    resp = resp + ''
                    for sec in sections:#Add each section to the html
                        resp = resp + sec[0] + sec[1].replace("\n","<br/>")
                resp = resp + "</div>" #close the div!

            else: #In the full mode
                if message[0]=='$': #$  is still search, basically do exactly the same as before
                    suggest = arc.suggestions(message[1:])
                    resp = resp + "<h4>Search hits:</h4> <br/>"
                    for sugg in suggest:
                        s_txt = sugg[2:].replace("_"," ")
                        resp = resp + "<span id=\""+sugg+"\" onclick=\"linkClicked(event);\" style=\"color:blue;\">" + s_txt + "</span> <br/>"

                elif message[0] == '%':# Link clicks are different!
                    has = arc.archive.has_entry_by_path(message[1:]) #Check if we have the link in the archive
                    if has:
                        resp = arc.pull_article(message[1:]) #If so, grab it!
                    else: #otherwise, 
                        suggest = arc.suggestions(message[1:].replace("_"," ").split("#")[0]) #Get suggestions and list them
                        resp = resp + "<h4>No article, suggestions:</h4> <br/>" #Different feedback, rest is the same as the last two
                        for sugg in suggest:
                            s_txt = sugg[2:].replace("_"," ")
                            resp = resp + "<span id=\""+sugg+"\" onclick=\"linkClicked(event);\" style=\"color:blue;\">" + s_txt + "</span> <br/>"

            #Last clever bit- if we're in the full mode, we replace the native HTML a href links with our type:
            if arc.mode != 'paredDown':
                resp = resp.replace("a href","a style= \"color:blue;\" onclick=\"linkClicked(event);\" id")
            await websocket.send(resp) #Send the html

    except websockets.exceptions.ConnectionClosed:
        #If it's closed, oh well!
        print("CONNECTION CLOSED")
        pass


async def main():

    #Make an archive global for the async handler
    global arc

    #Grab zim files in this and parent directory
    zms = glob.glob("../*.zim")+glob.glob("*.zim")
    arc = archive(zms[0]) #Make the archive object

    #Fire up the server
    server = await websockets.serve(handle_client, HOST, PORT)
    webbrowser.open("zim_reader.html") #Open the viewer client in the browser
    await server.wait_closed()


if __name__ == '__main__':
    #do thing
    asyncio.run(main())    



