"use strict";

const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const webpack = require("webpack");

module.exports = {
    mode: "production",
    entry: "./assets/js/main.js",
    output: {
        path: path.resolve(__dirname, "static/dist"),
        filename: "bundle.js",
    },
    plugins: [
        new MiniCssExtractPlugin({
            filename: "bundle.css",
        }),
        new webpack.ProvidePlugin({
            bootstrap: "bootstrap",
            htmx: "htmx.org",
        }),
    ],
    module: {
        rules: [
            {
                test: /\.css$/,
                use: [MiniCssExtractPlugin.loader, "css-loader"],
            },
        ],
    },
};
