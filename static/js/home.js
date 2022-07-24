var doc = document.documentElement;
var form = document.getElementById('idForm');

// async function postData(url='', data={}) {
//     const response = await fetch(url, {
//         method: 'POST',
//         mode: 'cors',
//         cache: 'no-cache',
//         credentials: 'same-origin',
//         headers: {
//             'Content-Type': 'application/json'
//         },
//         redirect: 'follow',
//         referrerPolicy: 'no-referrer',
//         body: JSON.stringify(data)
//     });
//     return response.json()
// }
//function getWeather(lat, lng) {
//  fetch(
//    `https://api.openweathermap.org/data/2.5/weather?lat=${lat}&lon=${lng}&appid=${API_KEYS}&units=metric`
//  )
//    .then(function (response) {
//      return response.json();
//    })
//    .then(function (json) {
//      const temperature = json.main.temp;
//      const place = json.name;
//      weather.innerText = `${temperature}°C\n${place}`;
//    });
//}
var id = Date.now();
form.addEventListener('submit', event => {
    event.preventDefault();
    fetch(`/api/register/${id}`, {
        method: 'POST',
        body: 'None'
    }).then(response => {
        window.location.href = `/test?phase=response&no=1&id=${id}`;
    //     doc.requestFullscreen()
    //     .then((r) => {
    // }).catch(err => { console.log('Error: ', 'No Full Screen')});

    }).catch(err => {
        console.log('Error: ', err);
    })
});
