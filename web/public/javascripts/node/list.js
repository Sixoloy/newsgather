/**
 * Created by sixoloy on 17-4-30.
 */
var mysql = require('mysql');
var async = require('async');

var mysql_config = {
    host     : 'localhost',
    user     : 'root',
    password : '88955211',
    database : 'news'
}

function create_one_news(rows) {
    var result = [];

    rows.forEach(function (val, index, arr) {
        var one = {
            "date_time": val.date_time,
            "url": val.url,
            "title": val.title,
            "content": val.content,
            "keywords": val.keywords,
            "keyphrases": val.keyphrases,
            "description": val.description
        };
        result.push(one);
    });
    return result;
}

var get_news = function(id1, id2, callback) {
    var connection = mysql.createConnection(mysql_config);

    connection.connect(function(err) {
        if (err) {
            console.error('error connecting: ' + err.stack);
            return;
        }
        console.log('connected as id ' + connection.threadId);
    });

    var result = [];

    //只有大类
    if (id2 == -1){
        connection.query('SELECT * FROM news_table WHERE cluster1ID = ? LIMIT 0, 20', [id1], function (err, rows, fields) {
            if (err)
                console.log(err);
            result = create_one_news(rows);
            callback(result);
        });
    }

    //大类小类都有
    else {
        connection.query('SELECT * FROM news_table WHERE cluster1ID = ? AND cluster2ID LIMIT 0, 20', [id1, id2], function (err, rows, fields) {
            if (err)
                console.log(err);
            result = create_one_news(rows);
            callback(result);
        })
    }
}

exports.get_news = get_news;