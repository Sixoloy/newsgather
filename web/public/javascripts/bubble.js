/**
 * Created by sixoloy on 17-4-23.
 */

function set_r(data) {

    if (data.depth == 1)
        data.r = 40 * data.data.nums_of_news;
    else if (data.depth == 2)
        data.r = 30 * data.data.nums_of_news;

    data.x = data.x * 0.95;
    data.y = data.y * 0.75;

    if (data.depth == 2)
        return;

    for(var i = 0; i < data.children.length; i++){
        set_r(data.children[i]);
    }
}

function adjust_coordinate(data) {

    if (data.depth == 2)
        return;

    for (var i = 0; i < data.children.length; i++){
        var theta = (135 - i * 45 * (1 + 0.15 * i)) * Math.PI / 180;
        if (data.depth == 1){
            data.children[i].x = data.x + (data.r + data.children[i].r) * Math.cos(theta);
            data.children[i].y = data.y - (data.r + data.children[i].r) * Math.sin(theta);
        }
        adjust_coordinate(data.children[i]);
    }
}

function post(URL, PARAMS) {
    var temp = document.createElement("form");
    temp.action = URL;
    temp.method = "post";
    temp.style.display = "none";
    for (var x in PARAMS) {
        var opt = document.createElement("textarea");
        opt.name = x;
        opt.value = PARAMS[x];
        // alert(opt.name)
        temp.appendChild(opt);
    }
    document.body.appendChild(temp);
    temp.submit();
    return temp;
}

function create_bubble(json_data) {

    var svg = d3.select("svg"),
        width = +svg.attr("width"),
        height = +svg.attr("height");

    var color = d3.scaleOrdinal(d3.schemeCategory20c);

    var pack = d3.pack()
        .size([width, height])
        .padding(2);

    var data = pack(d3.hierarchy(json_data)
        .sum(function(d) { return 1; }));

    set_r(data);
    adjust_coordinate(data);

    console.log(data);
    console.log(data.descendants());

    var node = svg.selectAll(".node")
        .data(data.descendants())
        .enter().append("g")
        .attr("class", function(d) {
            if (d.depth == 0)
                return "root_node";
            else if (d.depth == 1)
                return "node";
            else
                return "leaf_node";
        })
        .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

    node.append("circle")
        .attr("id", function(d) { return d.id; })
        .attr("r", function(d) { return d.r })
        .style("fill", function(d) { return color(d.height); })
        .attr("cursor","pointer")
        .on("click", function(d,i) {
                post("/clusters", {id1: d.data.id1, id2: d.data.id2});
            });

    node.append("text")
        .attr("clip-path", function(d) { return "url(#clip-" + d.id + ")"; })
        .selectAll("tspan")
        .data(function(d) { return d.data.description; })
        .enter().append("tspan")
        .attr("x", function(d, i, nodes) { return 7.5 + (i - nodes.length / 2 ) * 20; })
        .attr("y", 0)
        .attr("cursor","pointer")
        .text(function(d) { return d; })
        .style("font-size", "2em");
}
