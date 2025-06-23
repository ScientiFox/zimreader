
//Clock for the sync loop
let clock;

//Timer variables
d = new Date();
i_time = d.getTime();
clock = 0 //d.getTime()-i_time;

//websocket message up her in global
let WSmessage;
WSmessage = "";

// State for the paredDown/full mode
let modeState;
modeState = 0;

//Make the actual websocket
sock = new WebSocket('ws://127.0.0.1:8080');

//websocket callbacks
sock.onopen = function(event){setElement("state","opened");};
sock.onmessage = function(event){onReply(event);};
sock.onclose = function(event){setElement("state","closed");};

//Start up the main loop at 10ms intervals
setInterval(tickTock,10);

function tickTock(){
	//Main loop

	d = new Date();
	clock = d.getTime()-i_time;
	document.getElementById('clock').innerHTML="Clocktime: "+(clock/1000.0)+"s";

}

function pass(){} //Just a doNothing for me

function checkLead(pattern,string){
	// Function to check the start of a string for a pattern
	let i = 0; 
	while (i<pattern.length){ //Loop over the pattern length
		if (pattern[i] == string[i]){pass();} //comapre the characters
		else{return(false)} //quit as soon as you see a false match
		i=i+1;
	}
	return(true) //Otherwise, the pattern is there!

}

function sendSearch(){
	//Function to send a search string to the server
	let searchString = document.getElementById('searchInput').value; //grab it from the box
	if (searchString != ""){sock.send("$"+searchString);} //send it through websocket
}

function onReply(event){
	//reply callback
	WSmessage=event.data; //grab the message data
	if (WSmessage[0] != '&'){ //if it starts with an &, it's an article text
		document.getElementById('textMain').innerHTML= WSmessage; //put it up
		window.scrollTo(0,0); //scroll to top of page
	}	 
}

function linkClicked(event){
	//function to handle a link click
	let clickedOn = event.target.id; //grabs id of trigger element, which will be 
					 // set to the target article title
	sock.send("%"+clickedOn); //Send an article request
}

function toggleMode(){
	//function to switch modes
	modeState = 1-modeState; //change the mode itself

	//Display the mode on the page
	if (modeState==0){document.getElementById('modeText').innerHTML = 'Pared Down';}
	else{document.getElementById('modeText').innerHTML = 'Full';}

	sock.send("&"+modeState); //Send the change request to the server
}
