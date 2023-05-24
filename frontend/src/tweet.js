const DOMPurify = require('dompurify');


export default function InsertTweets({ tweets }) {
  return (
    tweets.map(tweet => insertTweet({ tweet }))
  );
}

// Insert a tweet into the chatbox
// {/*<img src="profile_image_url" alt="Profile"></img>*/}
// {/*style={{ marginLeft: "10px" }}*/}

function insertTweet({ tweet }) {
  return (
    <>
      { /* <!--<hr style={{ height: "2px", color: "black", backgroundColor: "black" }} /> --> */}
      < hr style={{ height: 1, width: '100%', borderWidth: 1, borderColor: 'red', marginTop: "35px" }} />
      < div class="tweet" style={{ marginBottom: "20px" }}>
        <div class="tweet-header">
          <span class="tweet-author" >{tweet.author}</span>
          <span class="tweet-date" style={{ marginLeft: "10px" }}>
            {createStatusUrl({ ...tweet, text: new Date(tweet.created_at).toUTCString() })}</span>
        </div>
        <hr style={{ height: 1, width: '100%', borderWidth: 1, borderColor: 'red' }} />
        <div class="tweet-content">
          <p>{createTweetText(tweet)}</p>
          <img src="tweet_image_url" alt="Tweet Image"></img>
          <span style={{ marginLeft: "5px" }}> {createStatusUrl({ ...tweet, text: "" })}</span>
        </div>
      </div >
    </>
  );
}

function createStatusUrl({ text, author, id }) {
  return (
    <a href={`https://twitter.com/${author}/status/${id}`} style={{ textDecoration: "none", color: "black" }} target="_blank">{text}</a>
  );
}

function createTweetText({ in_reply_to, text, matching_words }) {
  // Sanitize the input
  text = DOMPurify.sanitize(text);
  matching_words = matching_words.map(word => DOMPurify.sanitize(word));

  // bold out any words in the text that the matching_words contains
  for (let word of matching_words) {
    const regex = new RegExp(word, 'g');
    text = text.replace(regex, `<b style="color: green;">${word}</b>`);
  }
  const prefix = in_reply_to ? `@${in_reply_to} ` : "";
  // without the dangerouslySetInnerHTML, the HTML tags would be escaped and displayed as text
  return <span dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(prefix + text) }} />;
}


// The matching_words are sent to user's browser from the server I own, although they were initially sent to my server by that same user.
// Still dangerous?

// Even if you trust your users not to intentionally attack your site, it's still possible for them to unintentionally provide input
// that could be harmful when interpreted as HTML or JavaScript. For example, what if a user wants to use a less-than symbol followed by
// a letter in their input (like <b)? In HTML, this would start a <b> tag, which is probably not what the user intended.
// Therefore, you should sanitize any user-supplied input before including it in HTML. There are libraries available for sanitizing HTML in
// JavaScript, such as DOMPurify.
