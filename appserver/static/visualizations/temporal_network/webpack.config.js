var webpack = require('webpack');
var path = require('path');

module.exports = {
    entry: 'visualization_source',
    resolve: {
        root: [
            path.join(__dirname, 'src'),
        ],
        // alias: {
        //   // bind version of jquery-ui
        //   "jquery-ui": "jquery-ui/jquery-ui.js",      
        //   // bind to modules;
        //   // modules: path.join(__dirname, "node_modules"),
        // }
    },
    output: {
        filename: 'visualization.js',
        libraryTarget: 'amd'
    },
    externals: [
        'api/SplunkVisualizationBase',
        'api/SplunkVisualizationUtils'
    ],
    module: {
      rules: [
        {
          test: /\.css$/,
          loaders: ["style-loader","css-loader"]
        },
        {
          test: /\.(jpe?g|png|gif)$/i,
          loader:"file-loader",
          options:{
            name:'[name].[ext]',
            outputPath:'assets/images/'
            //the images will be emited to dist/assets/images/ folder
          }
        }
      ]
    },
    plugins: [
    /* Use the ProvidePlugin constructor to inject jquery implicit globals */
    new webpack.ProvidePlugin({
        $: "jquery",
        jQuery: "jquery",
        "window.jQuery": "jquery'",
        "window.$": "jquery"
    })
  ]
};