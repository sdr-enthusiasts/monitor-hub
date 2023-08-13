const path = require("path");
const webpack = require("webpack");

module.exports = {
  module: {
    rules: [{ test: /.ts$/, use: "ts-loader" }],
  },
  entry: "./src/index.ts",
  output: {
    path: path.resolve(__dirname, "dist"),
    filename: "index.bundle.js",
  },
  plugins: [
    new webpack.ProvidePlugin({
      $: "jquery",
      jQuery: "jquery",
    }),
  ],
};
