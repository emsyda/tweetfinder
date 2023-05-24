const { Client } = require('pg');
require('dotenv').config();
const csv = require('csv-parser');

const { getClient, createTable, insertTweets, getTweets,
    getTweetsFromCsv, commitCsvToDb, getFirstAndLastTweetId, _dropTable } = require('../database');

const _time = (new Date()).getTime();
const tweets = [
    {
        id: '1',
        created_at: _time,
        author: 'john',
        text: 'Hello World!',
        is_retweet: false,
        is_quote: false,
        is_liked: false
    },
    {
        id: '2',
        created_at: _time + 1000,
        author: 'jane',
        text: 'Hi there!',
        is_retweet: false,
        is_quote: false,
        is_liked: false
    },
    {
        id: '5',
        created_at: _time + 2000,
        author: 'paul',
        text: 'Hello twitter!',
        is_retweet: false,
        is_quote: false,
        is_liked: false
    },
    {
        id: '10',
        created_at: _time + 1000,
        author: 'jane',
        text: 'My second tweet!',
        is_retweet: false,
        is_quote: false,
        is_liked: false
    }
];
/*
test('adds 1 + 2 to equal 3', () => {
    expect(sum(1, 2)).toBe(3);
});*/
beforeEach
beforeAll

describe('database', () => {
    it("testInsertTweets", async () => {
        await _dropTable('test_tweets');

        await createTable();

        await insertTweets(tweets);

        await getTweets().then(res => {
            expect(res.length).toBe(4);
            for (let i = 0; i < res.length; i++) {
                expect(res[i]).toEqual(tweets[i]);
            }
        });

        await getTweets('john').then(res => {
            expect(res.length).toBe(1);
            expect(res[0]).toEqual(tweets[0]);
        });

        await getTweets('jane').then(res => {
            expect(res.length).toBe(2);
            expect(res[0]).toEqual(tweets[1]);
            expect(res[1]).toEqual(tweets[3]);
        });

        await getFirstAndLastTweetId('jane').then(res => {
            expect(res).toEqual({ first_id: '2', last_id: '10' });
        });

        await getFirstAndLastTweetId('paul').then(res => {
            expect(res).toEqual({ first_id: '5', last_id: '5' });
        });
    });

    it("loadTweetsFromCSV", async () => {
        const tweets = await getTweetsFromCsv('paulfchristiano');
        console.log(`Before saving to sql: ${JSON.stringify(tweets[0])}, type of id: ${typeof tweets[0].id}`);
        //await commitCsvToDb(tweets);
        await insertTweets(tweets);
        const retrieved = await getTweets('paulfchristiano')
        console.log(`Retrieved from SQL: ${JSON.stringify(retrieved[0])}, type of id: ${typeof retrieved[0].id}`);
    });
});
