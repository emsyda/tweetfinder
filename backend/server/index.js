const express = require('express');
const bodyParser = require('body-parser');

const { filterTweetsStrict, pullTweets } = require('./handlers.js');

const PORT = process.env.PORT || 3001;

const inProgressProcesses = {};

const app = express();
app.use(bodyParser.json()); // for parsing POST request's body
//support parsing of application/x-www-form-urlencoded post data
//app.use(bodyParser.urlencoded({ extended: true }));

app.get('/api', (req, res) => {
    // Choos one of the following 3 (only 1 response allowed):
    //res.send('Hello from server!');
    res.json({ message: 'Hello from server!' });
    // res.end();
});

// ------------------ API ------------------

app.post('/api/searchTweets', async (req, res) => {
    const { message, screenName, retweeted, quoteTweeted, liked } = req.body;
    console.log(req.body);
    if (!screenName) {
        res.json({ message: '`screenName` must be provided' });
        return;
    }
    const tweets = await filterTweetsStrict(message, screenName, retweeted, quoteTweeted, liked);
    res.json({ tweets: tweets });
});

app.post('/api/pullTweets', (req, res) => {
    //console.log(req.body);
    const credentials = req.body.credentials;
    const screenName = req.body.screenName;
    console.log("Credentials: " + credentials, "\nScreen name: " + screenName);
    if (!credentials || !screenName) {
        res.json({ message: 'Invalid request' });
        return;
    }
    if (inProgressProcesses[screenName]) {
        res.json({ message: 'Process already in progress' });
        return;
    }
    pullTweets(credentials, screenName)
        .then(() => console.log(`Finished pulling tweets for ${screenName}`))
        .catch((e) => { console.error(e) });

    res.json({ message: 'Process started' });
});


app.listen(PORT, () => {
    console.log(`Server listening on ${PORT}`);
});


