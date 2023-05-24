const { getTweets, getTweetsFromCsv, commitCsvToDb } = require('./database.js');
const { filterTweets } = require('./utils.js');


async function filterTweetsStrict(message, screenName, retweeted, quoteTweeted, liked) {
    //getTweets(screenName).then((tweets) => {
    return await getTweetsFromCsv(screenName)
        .catch(e => {
            res.json({ error: 'You must Pull the tweets first' });
            throw (e)
        })
        .then((tweets) =>
            filterTweets(tweets, message, retweeted, quoteTweeted, liked))
        .then((tweets) => {
            console.log(`Sending back ${tweets.length} tweets`);
            res.json({ tweets: tweets });
        })
        .catch(console.error);
}


// * Let the python process pull the tweets from twitter, then use this function
// * to commit them to the database
async function pullTweets(credentials, screenName) {
    inProgressProcesses[screenName] = true;
    //const { first_id, last_id } = await getFirstAndLastTweetId(screenName);
    const spawn = require("child_process").spawn;
    const extraArgs = [];
    const pythonProcess = spawn('.venv/bin/python3', [
        "./scripts/fetch_and_save_tweets.py", screenName, ...extraArgs, ...credentials,
    ]);
    /*pythonProcess.stdout.on('data', (data) => {
        commitCsvToDb(screenName);
    });*/
    await new Promise((resolve, reject) => {
        pythonProcess.stderr.on('data', (data) => {
            console.error(`Error: ${data}`);
        });

        // if pythonProcess exited with '0', then commitCsvToDb(screenName)
        pythonProcess.on('exit', (code) => {
            if (code == 0) {
                console.log(`Child exited with code ${code}`);
                commitCsvToDb(screenName)
                    .then(() => { resolve(code) })
                    .catch((e) => { reject(e) });
            } else {
                console.error(`Child exited with non-zero code ${code}`);
                reject(code);
            }
        });
    });
    inProgressProcesses[screenName] = false;
}


module.exports = {
    pullTweets,
    filterTweetsStrict,
};
