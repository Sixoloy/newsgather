/**
 * Created by sixoloy on 17-4-30.
 */
var express = require('express');
var router = express.Router();
var list = require('../public/javascripts/node/list');

/* POST home page. */
router.post('/', function(req, res, next) {
    list.get_news(req.body.id1, req.body.id2, function (news_list) {
        res.render('clusters', { news_list: JSON.stringify(news_list) });
    });
});

module.exports = router;