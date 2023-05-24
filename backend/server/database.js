const { Client } = require('pg');
require('dotenv').config();
const csv = require('csv-parser');

const IS_TEST = process.env.NODE_ENV === 'test';
console.log("IS_TEST: " + IS_TEST, "\nNODE_ENV: " + process.env.NODE_ENV);
console.log("DATABASE_URL: " + process.env.DATABASE_URL);
//console.log("PGUSER: " + process.env.PGUSER);
//console.log("PGPASSWORD: " + process.env.PGPASSWORD);
//process.env.PGUSER = "postgres";
//process.env.POSTGRESQL_PASSWORD = null; //"postgres";

let tableName = 'tweets';
if (IS_TEST) {
    tableName = 'test_tweets';
}

function setTableName(name) {
    tableName = name;
}

async function getClient() {
    const client = new Client({
        /*connectionString: process.env.DATABASE_URL,
        ssl: {
            rejectUnauthorized: false
        }*/
        "user": "dev",
        "password": "dev", //process.env.PGPASSWORD,
        "database": "postgres",
    });
    await client.connect();
    return client;
}

async function createTable() {
    const client = await getClient();
    // SERIAL = auto-incrementing unique integer
    // Note that the BIGINT is SELECT'ed as a string (to preserve precision)
    await client.query(`
        CREATE TABLE IF NOT EXISTS ${tableName} (
            id BIGINT PRIMARY KEY,
            created_at BIGINT NOT NULL,
            author VARCHAR(255) NOT NULL,
            text text NOT NULL,
            is_retweet BOOLEAN NOT NULL,
            is_quote BOOLEAN NOT NULL,
            is_liked BOOLEAN NOT NULL
        );
    `);
    await client.end();
}

async function insertTweets(tweets) {
    await createTable();
    const client = await getClient();
    const columns = ['id', 'created_at', 'author', 'text', 'is_retweet', 'is_quote', 'is_liked'];
    // does not have REPLACE INTO syntax
    let qry = `INSERT INTO ${tableName} (${columns.join(', ')}) VALUES\n`;
    for (let i = 0; i < tweets.length; i++) {
        const tweet = tweets[i];
        const ending = (i < tweets.length - 1) ? ',\n' : '\n';
        const tweetCopy = { ...tweet, author: `'${tweet.author}'`, text: `'${tweet.text.replace(/'/g, "''")}'` };
        qry += "    (" + columns.map(v => tweetCopy[v]).join(', ') + ")" + ending;
        //qry += `    (${tweet.id}, ${tweet.created_at}, ${tweet.author}, ${tweet.text}, ${tweet.is_retweet}, ${tweet.is_quote}, ${tweet.is_liked})${ending}`;
    }
    qry += `ON CONFLICT (id) DO UPDATE SET\n`; // DO NOTHING = ignore duplicates
    qry += columns.slice(1).map(v => "    " + v + " = EXCLUDED." + v).join(',\n') + ';';
    console.log(qry);
    await client.query(qry);
    await client.end();
}

// READ SQL
async function getTweets(author) {
    const client = await getClient();
    let qry = `SELECT * FROM ${tableName}`;
    if (author) {
        qry += ` WHERE author = '${author}'`;
    }
    qry += 'ORDER BY id DESC';
    const res = await client.query(qry);
    await client.end();
    for (let row of res.rows) {
        //row.id = parseInt(row.id);  // will result in loss of precision
        row.created_at = parseInt(row.created_at);
    }
    return res.rows;
}

// returns: {first_id, last_id}
async function getFirstAndLastTweetId(author) {
    const client = await getClient();
    const res = await client.query(`SELECT MIN(id) AS first_id, MAX(id) AS last_id FROM ${tableName} WHERE author = '${author}'`);
    await client.end();
    const row = res.rows[0];
    return { first_id: row.first_id, last_id: row.last_id };
}

//  ----------- CSV ---------------------

async function getTweetsFromCsv(author) {
    function _parseTweet(tweet) {
        // `id` is in string format
        // can't use `parseInt` as it will round it: '1302753476540162049' -> 1302753476540162000
        return {
            ...tweet,
            created_at: Date.parse(tweet.created_at),
            is_retweet: tweet.is_retweet.toLowerCase() === 'true',
            is_quote: tweet.is_quote.toLowerCase() === 'true',
            is_liked: tweet.is_liked.toLowerCase() === 'true',
        }; //, id: parseInt(tweet.id) };
    }
    const filePath = `./data/tweets_${author.toLowerCase()}.csv`;
    const fs = require('fs');
    const results = [];

    // Check if the file exists before trying to create the stream
    // (otherwise the app will crash, as 
    //    "the ENOENT (no such file or directory) error occurs immediately when the stream is created,
    //     before the error handlers have a chance to be set up")
    if (!fs.existsSync(filePath)) {
        throw new Error(`File ${filePath} does not exist`);
    }

    return await new Promise((resolve, reject) => {
        fs.createReadStream(filePath)
            .pipe(csv())
            .on('data', (data) => results.push(_parseTweet(data)))
            .on('end', () => {
                //console.log(results);
                resolve(results);
            }).on('error', reject)
    });
}

async function commitCsvToDb(author) {
    const tweets = await getTweetsFromCsv(author);
    await insertTweets(tweets);
}


//  -------------------------------------

// CLEANUP FOR TESTS
async function _dropTable(tableName) {
    const client = await getClient();
    //await client.query(`DELETE FROM ${tableName}`);
    await client.query(`DROP TABLE ${tableName}`);
    await client.end();
}


module.exports = {
    setTableName,
    getClient,
    createTable,
    insertTweets,
    getTweets,
    getFirstAndLastTweetId,
    getTweetsFromCsv,
    commitCsvToDb,
    _dropTable
};
