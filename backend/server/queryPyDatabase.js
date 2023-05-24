const fetch = require("node-fetch");

const HEADERS = { 'headers': { 'Content-Type': 'application/json' } };
const PORT = 3002;

async function postFetch(endpoint, body) {
    const url = `http://localhost:${PORT}` + endpoint;
    const response = await fetch(url, {
        ...HEADERS,
        method: 'POST',
        body: JSON.stringify(body)
    });
    const resBody = await response.json();
    //handleErrorMessage(resBody)
    return resBody;
}

async function testConn(msg) {
    //const response = await fetch('http://localhost:{PORT}');
    const response = await postFetch('/testConn', { msg: msg })
    return response;
}

async function filterTweetsNearest(message, screenName, retweeted, quoteTweeted, liked) {
    const response = await postFetch('/api/getNearestTweets');
    return response;
}


module.exports = {
    postFetch,
    testConn,
    filterTweetsNearest
}
