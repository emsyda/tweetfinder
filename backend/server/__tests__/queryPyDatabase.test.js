const { postFetch, testConn, queryTweets } = require('../queryPyDatabase');


describe('queryPyDatabase', () => {
    it("testInsertTweets", async () => {
        const response = await testConn(["xyz", "123"]);
        //expect(response).toEqual({  });
        console.log(`Received back from testConn:\n${JSON.stringify(response)}.\nIts type is '${typeof response}'`);
    });
});
