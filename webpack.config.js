const path = require("path");
const webpack = require("webpack");
const TerserPlugin = require("terser-webpack-plugin");

module.exports = {
  module: {
    rules: [{ test: /.ts$/, use: "ts-loader" }],
  },
  devtool: "source-map",
  entry: "./src/index.ts",
  output: {
    path: path.resolve(__dirname, "dist"),
    filename: "index.bundle.js",
  },
  optimization: {
    minimize: true,
    minimizer: [new TerserPlugin({ parallel: true })],
  },
  plugins: [
    new webpack.ProvidePlugin({
      $: "jquery",
      jQuery: "jquery",
    }),
  ],
};
