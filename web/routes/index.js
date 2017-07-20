var express = require('express');
var bubble = require('../public/javascripts/node/bubble');
var router = express.Router();

/* GET home page. */
router.get('/', function(req, res, next) {
  bubble.create_json(function (json_data) {
    res.render('index', { title: '新闻热点', data: JSON.stringify(json_data) });
  });
});

module.exports = router;

