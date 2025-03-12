"use strict";

const path = require("path");
const MiniCssExtractPlugin = require("mini-css-extract-plugin");
const { WebpackManifestPlugin } = require("webpack-manifest-plugin");
const webpack = require("webpack");

module.exports = {
    mode: "production",
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
            htmx: "htmx.org",
            $: "jquery",
            jQuery: "jquery",
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
