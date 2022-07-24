var doc = document.documentElement;
var form = document.getElementById('responseForm');
var chat = document.getElementById('chat');
var input = document.getElementById('responseInput');
var sendBtn = document.getElementById('sendButton');
const queryString = window.location.search;
const urlParams = new URLSearchParams(queryString);
const phase = urlParams.get('phase');
const no = parseInt(urlParams.get('no'));
const id = parseInt(urlParams.get('id'));
var verbatim = [];

var el = document.getElementById('c');


var ctx = el.getContext('2d');
var isDrawing = false;
var start = null;
var points = [];
var w = 500;
var h = 300;
var details = [];

make_base();
get_verbatim();

function make_base()
{
    imgObj = new Image();
    imgObj.src = `static/img/blot_${no}.jpg`
    imgObj.onload = function(){
        h = w * imgObj.height / imgObj.width

        el.height = h
        ctx.drawImage(imgObj, 0, 0, w, h)
  }
};

function get_verbatim() {
    //pass
}

el.onmousedown = function(e) {
  isDrawing = true;
  ClearSelection();
  start = {x: e.clientX, y: e.clientY} ;
  points = [];
  points.push(start);
  RenderSelection(points);
};

el.onmousemove = function(e) {
    if (isDrawing == false) {
        return;
    }
        points.push({x: e.clientX, y: e.clientY} );
        Render();

  };

  el.onmouseup = function() {
    isDrawing = false;
    points.push(start);
    SelectDetails();
    Render();
  };

  function Setup(){
    var locator = {
        1: {loc: "D1", x: 100, y: 100, selected: false},
        2: {loc: "D2", x: 200, y: 200, selected: false}
    };
    for (var d in locator) {
        details.push(d);
    }
}

function ClearSelection(){
	 for (var i = 0; i < Object.keys(details).length; i ++){
  	var detail = details[i];
    detail.selected = false;
  }
}

function SelectDetails(){
	for (var i = 0; i < details.length; i ++){
  	var detail = details[i];
    SetSelection(detail);
  }
}

function SetSelection(detail){
	if (points.length <= 1){
  	return;
  }
  detail.selected = false;
  var intercessionCount = 0;
  for (var i = 1; i < points.length; i ++){
			var start = points[i - 1];
      var end = points[i];
      var line = {start: start, end: end};


      var ray = {Start: {x: detail.x, y: detail.y}, End: {x: 99999, y: 0}};
      var segment = {Start: start, End: end};
      var rayDistance = {
      	x: ray.End.x - ray.Start.x,
        y: ray.End.y - ray.Start.y
      };
      var segDistance = {
      	x: segment.End.x - segment.Start.x,
        y: segment.End.y - segment.Start.y
      };

      var rayLength = Math.sqrt(Math.pow(rayDistance.x, 2) + Math.pow(rayDistance.y, 2));
      var segLength = Math.sqrt(Math.pow(segDistance.x, 2) + Math.pow(segDistance.y, 2));

      if ((rayDistance.x / rayLength == segDistance.x / segLength) &&
        (rayDistance.y / rayLength == segDistance.y / segLength)) {
        continue;
    	}

      var T2 = (rayDistance.x * (segment.Start.y - ray.Start.y) + rayDistance.y * (ray.Start.x - segment.Start.x)) / (segDistance.x * rayDistance.y - segDistance.y * rayDistance.x);
    	var T1 = (segment.Start.x + segDistance.x * T2 - ray.Start.x) / rayDistance.x;

        //Parametric check.
      if (T1 < 0) {
      	continue;
      }
      if (T2 < 0 || T2 > 1) {
      	continue
      };
      if (isNaN(T1)) {
      	continue
      }; //rayDistance.X = 0

      intercessionCount++;
  }

  if (intercessionCount == 0) {
  	detail.selected = false;
  	return;
  }
  console.log(intercessionCount);
  if(intercessionCount & 1){
  	console.log('Impar');
  	detail.selected = true;
  } else {
  	console.log('Par');
  	detail.selected = false;
  }
}

function Render(){
    ctx.clearRect(0, 0, 500, 500, 'white');
    ctx.save();
    RenderSelection(points);
    for (var i = 0; i < details.length; i ++){
  	    var detail = details[i];
        RenderDetail(detail);
    }
	ctx.restore();
}

function RenderDetail(detail){
    ctx.setLineDash([0]);
    ctx.beginPath();
    ctx.arc(detail.x, detail.y, 5, 0, 2 * Math.PI, false);
    ctx.fillStyle = detail.selected ? 'green' : 'yellow';
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'black';
    ctx.stroke();
    ctx.closePath();
}

function RenderSelection(points){
    if (points.length <= 1){
        return;
    }

    ctx.setLineDash([5,3]);
    ctx.strokeStyle = 'black';
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (var i = 0; i < points.length; i ++){
        var point = points[i];
      if (i == 0){
          ctx.moveTo(point.x, point.y);
      } else
      {
          ctx.lineTo(point.x, point.y);
      }
    }

    ctx.lineTo(start.x, start.y);
    ctx.fill();
    ctx.stroke();
    ctx.closePath();
  }

Setup();
Render();

function select_whole(){
    start = {x: 0, y: 0} ;
    points = [];
    points.push(start);
    points.push({x: w, y: 0});
    points.push({x: w, y: h});
    points.push({x: 0, y: h});
    points.push(start);
    SelectDetails();
    Render();
  }


function enter() {

    if (input.value.trim().length === 0) {
        return
    }

    if (input.value.includes("inkblot") || input.value.includes('blot')) {
        chat.innerText = "That's right, that's what it is, but I want you to tell me what might it be, what else does it look like?"
        return
    }

    if (verbatim.includes(input.value)) {
        return
    }

    verbatim.push(input.value);
    input.value = "";

    if (verbatim.length >= 1) {
        sendBtn.hidden = false;
    }

    if (verbatim.length === 5) {
        chat.innerText = "Alright, let's do the next one.";
        setTimeout(sendResponses, 2000);
    }

};

function sendResponses() {
    fetch('/api/response', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({"phase": phase, "no": no, "id": id, "verbatim": verbatim})
    }).then((response)=> {
        console.log(response)
        if (response.redirected) {
            window.location = response.url
        }
    }).catch(err => {console.log('Error: ', err);});
};

input.addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
      event.preventDefault();
      document.getElementById("responseButton").click();
    }
  });
