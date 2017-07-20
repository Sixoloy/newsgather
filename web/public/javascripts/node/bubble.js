/**
 * Created by sixoloy on 17-4-26.
 */
var mysql = require('mysql');
var async = require('async');

var mysql_config = {
    host     : 'localhost',
    user     : 'root',
    password : '88955211',
    database : 'news'
}

var create_json = function(callback){

    var connection = mysql.createConnection(mysql_config);

    connection.connect(function(err) {
        if (err) {
            console.error('error connecting: ' + err.stack);
            return;
        }
        console.log('connected as id ' + connection.threadId);
    });

    connection.query('SELECT * FROM cluster1_table ORDER BY cluster1ID desc LIMIT 0, 10', function (err, rows, fields) {
        async.map(rows,function(row,callback) {
            async.waterfall([
                function(callback) {
                    connection.query('SELECT COUNT(*) FROM news_table WHERE cluster1ID = ?', [row['cluster1ID']], function (err, result, fields) {
                        if (err)
                            consolg.log(err);
                        callback(null, result[0]['COUNT(*)']);
                    })
                },
                function(result, callback) {
                    //得到了大类的新闻数量
                    connection.query('SELECT * FROM cluster2_table WHERE cluster1ID = ?', [row['cluster1ID']], function (err, rows, fields) {
                        if (err)
                            consolg.log(err);
                        async.map(rows, function (row, callback) {
                            var small_cluster = {};
                            small_cluster.id1 = row['cluster1ID'];
                            small_cluster.id2 = row['cluster2ID'];
                            small_cluster.description = row['keywords'];
                            connection.query('SELECT COUNT(*) FROM news_table WHERE cluster1ID = ? AND cluster2ID = ?',
                                [row['cluster1ID'], row['cluster2ID']],
                                function (err, result, fields) {
                                    small_cluster.nums_of_news = result[0]['COUNT(*)'];
                                    small_cluster.children = [];
                                    callback(null, small_cluster);
                            });
                        }, function (err, map_result) {
                            if (err)
                                console.log(err);
                            callback(null, {"nums_of_news": result, "children": map_result});
                        });
                    })
                }
            ], function(err, result) {
                callback(null,{
                    "id1": row['cluster1ID'],
                    "id2": -1,
                    "description": row['keywords'],
                    "nums_of_news": result['nums_of_news'],
                    "children": result['children']
                })
            });
        },function(err,result) {
            var data = {};
            data.type = -1;
            data.id = -1;
            data.description = "";
            data.nums_of_news = 0;
            data.children = result;
            callback(data);
        });
    });
}


exports.create_json = create_json;