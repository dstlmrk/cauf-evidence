"use strict";

const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const { WebpackManifestPlugin } = require("webpack-manifest-plugin");
const webpack = require("webpack");

// `npm run watch` passes --node-env development; production builds keep the
// default. In dev we ship readable source maps so browser debugging maps back
// to the original sources instead of the minified bundle.
const isProduction = process.env.NODE_ENV !== "development";

module.exports = {
    mode: isProduction ? "production" : "development",
    devtool: isProduction ? false : "eval-cheap-module-source-map",
    entry: {
        bundle: "./assets/js/main.js",
    },
    output: {
        path: path.resolve(__dirname, "static/dist"),
        filename: "bundle.[contenthash].js",
        publicPath: "/static/dist/",
        clean: true, // delete old builds
    },
    plugins: [
        new MiniCssExtractPlugin({
            filename: "bundle.[contenthash].css",
        }),
        new WebpackManifestPlugin({
            fileName: "manifest.json",
            publicPath: "/static/dist/",
        }),
        new webpack.ProvidePlugin({
            bootstrap: "bootstrap",
            // htmx.org ships as ESM (`export default htmx`); reference the
            // default export so the provided `htmx` is the instance with
            // helpers like `htmx.on`, not the module namespace object.
            htmx: ["htmx.org", "default"],
            // jQuery 4 ships as ESM (`export default jQuery`); reference the
            // default export so the provided `$`/`jQuery` is the callable
            // jQuery function, not the module namespace object.
            $: ["jquery", "default"],
            jQuery: ["jquery", "default"],
            Alpine: "alpinejs",
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
