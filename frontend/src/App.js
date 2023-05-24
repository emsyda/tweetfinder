import React, { useState, useRef, useEffect } from 'react';

import InsertTweets from './tweet.js';
//import filterTweets from './utils.js';

const HEADERS = { 'headers': { 'Content-Type': 'application/json' } };
const TEXT_INSTRUCTIONS = "Enter your search query here\n@elonmusk said something about Starship a few months ago"

function App() {
  const [tweets, setTweets] = useState([]);
  const [myOwn, setMyOwn] = useState(false);
  const [quoteTweeted, setQuoteTweeted] = useState(false);
  const [retweetedOrLiked, setRetweetedOrLiked] = useState(false);
  const [loginStatus, setLoginStatus] = useState({ screen_name: null, user_id: null, logged_in: false, is_admin: false, openai_key_stored: false });
  const [bottomRedWarning, setBottomRedWarning] = useState("");
  const [serverURL, setServerURL] = useState("");
  const openAIApiKeyRef = useRef();
  const screenNameRef = useRef();
  const messageRef = useRef();

  function getRefValue(ref) {
    if (!ref.current) return null;
    return ref.current.value;
  }

  function getScreenName() {
    return getRefValue(screenNameRef) || loginStatus.screen_name;
  }

  function handleGetUrl() {
    //console.log("process.env.REACT_APP_BACKEND_URL: ", process.env.REACT_APP_BACKEND_URL);
    // res.url:  dev: http://localhost:3000/api/getLoginStatus  production: http://localhost/api/getLoginStatus
    // these are useless, as they are only the frontend to nginx's reverse proxy; nor is there any way to find out
    //   ---> will have to hardcode it in build process
    //console.log("res.url: ", res.url);
    fetch('/api/getUrl').then(res => res.json()).then(res => {
      console.log("url: ", res);
      if (res) {
        // replace the tweetfinder-backend with localhost, as browser doesn't like dockerized version
        const url = res.replace("//tweetfinder-backend:", "//localhost:");
        // process.env.REACT_APP_BACKEND_URL = serverUrl;  // React doesn't like this
        setServerURL(url);
      }
    });
  }

  function handleGetLoginStatus() {
    fetch('/api/getLoginStatus').then(res => res.json()).then(setLoginStatus);
  }

  useEffect(() => {
    handleGetLoginStatus();  // Check if the user is logged in
  }, []);

  useEffect(() => {
    handleGetUrl(); // Get the server URL
  }, []);

  function openSmallWindow(url) {
    return window.open(url, "newWindow", "width=600,height=600");
  }

  function handleLogIn() {
    // Remember that env variables are not available in the browser
    // however, we can include then in the build process
    // RUN REACT_APP_BACKEND_URL=http://localhost:5000 npm run build
    const url = serverURL || process.env.REACT_APP_BACKEND_URL;
    const loginWindow = openSmallWindow(url);
    setBottomRedWarning("When you're done close the OAuth window or refresh this page.");
    const checkLoginWindowContent = setInterval(() => {
      if (loginWindow.closed) {
        handleGetLoginStatus()
        clearInterval(checkLoginWindowContent);
        setBottomRedWarning("");
      }
    }, 500); // check every 500 milliseconds
  }

  function handleLogOut() {
    fetch('/api/logout').then(res => res.json()).then(setLoginStatus);
  }

  function handleSetOpenAIApiKey(e) {
    //postFetch('/api/setOpenAIApiKey', { openai_api_key: getRefValue(openAIApiKeyRef) })
  }

  async function postFetch(url, body) {
    const response = await fetch(url, {
      ...HEADERS,
      method: 'POST',
      body: JSON.stringify(body)
    });
    const resBody = await response.json();
    handleErrorMessage(resBody)
    return resBody;
  }

  function handleErrorMessage(body) {
    if (body.error) {
      popUpError(body.error);
      throw new Error(body.error);
    }
    return body;
  }

  function popUpError(error) {
    alert(error);
  }

  function handleKeyDown(e, callback) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault(); // Prevent the new line
      callback(e);
    }
  }

  // GET /pullTweets, body includes credentials and screenName
  function handlePullTweets(e) {
    postFetch(
      '/api/pullTweets',
      {
        screen_name: getScreenName(),
      }
    ).catch(console.error);
  }

  function handleSearchTweets(e) {
    postFetch(
      '/api/getNearestTweets',
      {
        query: getRefValue(messageRef),
        screen_name: getScreenName(),
        filters: {
          author: myOwn ? getScreenName() : null,
          is_quote: quoteTweeted || null,
          rtl: retweetedOrLiked || null,
        },
        k: 10,
        openai_api_key: getRefValue(openAIApiKeyRef),
        timezoneOffset: new Date().getTimezoneOffset() / 60, // -3 (yes, opposite to the actual) for Helsinki summertime
      }
    )
      .then(body => setTweets(body.tweets))
      .catch(console.error);
  }

  const OpenAIKeyInputProps = { openAIApiKeyRef, handleKeyDown, handlePullTweets, loginStatus }

  return (
    // F0F0F0 F2F2F2 E6E6E6 DCDCDC D3D3D3 f7f9f9 FFFFFF
    // box widths: 280 / 370
    <div style={{ background: "white" }}>
      <div style={{ maxWidth: "300px", background: "white", margin: "0 auto", padding: "0 8px" }}>
        <div>
          <textarea id="messageInput" ref={messageRef} onKeyDown={e => handleKeyDown(e, handleSearchTweets)} type="text" placeholder={TEXT_INSTRUCTIONS} style={{ width: "300px", height: "80px" }} />
        </div >
        <div style={{}/* { display: "flex", justifyContent: "center", alignItems: "center"*/} >
          <button id="searchTweetButton" onClick={handleSearchTweets} style={{ verticalAlign: "top", height: "30px", width: "100px" }}>Search tweet</button>
          <OpenAIKeyInput {...OpenAIKeyInputProps} />
        </div >
        <div>
          <CheckBox label="my own" checked={myOwn} toggleChange={setMyOwn} />
          <CheckBox label="retweeted/liked" checked={retweetedOrLiked} toggleChange={setRetweetedOrLiked} />
        </div>
        <div>
          <CheckBox label="quote tweeted" checked={quoteTweeted} toggleChange={setQuoteTweeted} />
        </div>
        <InsertTweets tweets={tweets} />
        {/*<Conversations />*/}
        <PullTweets screenNameRef={screenNameRef} handleKeyDown={handleKeyDown} handlePullTweets={handlePullTweets} loginStatus={loginStatus} />
        <LoginFields loginStatus={loginStatus} handleLogIn={handleLogIn} handleLogOut={handleLogOut} />
        <div style={{ color: "red", marginTop: "5px" }}>{bottomRedWarning}</div>
        <Scripts />
        <script src="App.js"></script>
      </div >
    </div >
  );
}


function CheckBox({ label, checked, toggleChange }) {
  return (
    <label>
      <input
        type="checkbox"
        checked={checked}
        onChange={() => toggleChange(!checked)}
      />
      {label}
    </label>
  );
}

function OpenAIKeyInput({ handleKeyDown, handleSetOpenAIApiKey, loginStatus, openAIApiKeyRef }) {
  return (
    <span style={{ marginLeft: "5px" }} >
      {!loginStatus.openai_key_stored ? (
        <input ref={openAIApiKeyRef} onKeyDown={e => handleKeyDown(e, handleSetOpenAIApiKey)} type="password" placeholder="OpenAI API key" style={{ height: "24px", textAlign: "center", color: "gray", background: "white" /*border: "none"*/ }} />
      ) : null}
    </span>
  );
}

function PullTweets({ screenNameRef, handleKeyDown, handlePullTweets, loginStatus }) {
  if (loginStatus.is_admin) {
    return (<>
      <input ref={screenNameRef} onKeyDown={e => handleKeyDown(e, handlePullTweets)} type="text" id="screenNameInput" placeholder="Enter a Twitter username" />
      <button id="loadTweets" onClick={handlePullTweets}>Pull user's tweets and likes</button>
    </>);
  }
}

function LoginFields({ loginStatus, handleLogIn, handleLogOut }) {
  return (
    <div style={{ marginTop: "5px" }}>
      {!loginStatus.logged_in ? (
        // textAlign doesn't work here, nor on the <a>
        <span style={{ textAlign: "right" }}>
          <a href="#" onClick={handleLogIn}>Log in with Twitter</a>
        </span>
      ) : (
        <a href="#" onClick={handleLogOut}>Logout</a>
      )}
    </div >
  );
}




// --------------------------------------------------------------------------------------------

function Conversations() {
  return (
    <div class="container">
      <header>
        {/* <!-- Add login button and authentication popup --> */}
      </header>
      <main>
        <div class="row">
          <div class="col-md-4">
            {/* <!-- Add conversation list and search box --> */}
          </div>
          <div class="col-md-8">
            {/* <!-- Add chatbox and message input -->} */}
          </div>
        </div>
      </main>
    </div>
  );
}

// Conversation listm searchg boxm and click event handler to load conversations

function conversation() {
  function loadConversation(conversationId) {
    // Implement the function to load the conversation data, replacing the current messages in the chatbox.
  }

  document.querySelectorAll('.conversation').forEach(conversation => {
    conversation.addEventListener('click', () => {
      const conversationId = conversation.dataset.conversationId;
      loadConversation(conversationId);
    });
  });
}

function Scripts() {
  return (
    <>
      <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script><>{ /* <!-- Traversing, event handling, animating, Ajax interactions - for rapid web development--> */}</>
      <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.3/dist/umd/popper.min.js"></script><>{ /* <!-- Tooltips, popovers, dropdowns--> */}</>
      <script src="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script><>{ /* <!-- For creating responsive websites--> */}</>
      <script src="https://cdn.jsdelivr.net/npm/axios/dist/axios.min.js"></script><>{ /* <!-- For requests from the browser--> */}</>
      <>{ /* <!-- Although popper isn't necessary for `alert()` and nor axios for `fetch()`--> */}</>
    </>
  );
}

export default App;
