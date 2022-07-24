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

function enter() {
    if (input.value.trim().length === 0) {
        return
    }

    if (input.value.includes("inkblot") || input.value.includes('blot')) {
        chat.innerText = "That's right, that's what it is, but I want you to \
        tell me what might it be, what else does it look like?"
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
    if ((no === 1 ) && (verbatim.length === 1)) {
        chat.innerText = "If you take your time and look some more I think that \
        you will find something else too."
        return
    }

    if ((no === 4) && (verbatim.length === 1)) {
        fetch(`/api/R/${id}`, {
            method: 'POST'
        }).then(promise => { promise.json().then(R => {
            console.log("R: ", R)
            if (R === 3) {
                chat.innerText = "Wait, don't hurry through these. We are in no hurry, \
                take your time."
                return
            }
        })

        }).catch(err => {console.log(err)});
    }

    if (no === 10) {
        fetch(`/api/R/${id}`, {
            method: 'POST'
        }).then(promise => { promise.json().then(R => {
            console.log("R: ", R)
            if (R + length(verbatim) < 14) {
                if (window.confirm("Now you know how it's done. But there's a problem. \
                You didn't give enough answers for us to get anything out of the test. \
                So we will go through them again and this time I want you to make sure to \
                give me more answers. You can include the same ones you've already given if \
                you like but be sure to give me more answers this time.")) {
                    window.location.href = "/"
                } else {
                    window.location.href = "/"
                }

            }
        })

        }).catch(err => {console.log(err)});
    }


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
