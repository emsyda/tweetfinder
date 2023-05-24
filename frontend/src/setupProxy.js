const { createProxyMiddleware } = require("http-proxy-middleware");

// Only used in development stage. In production set it up in nginx.conf instead

module.exports = function (app) {
    app.use(
        createProxyMiddleware("/api", {
            target: "http://localhost:3001/",
            pathRewrite: {
                '^/api': '/',     // remove base path
            },
        })
    );
};