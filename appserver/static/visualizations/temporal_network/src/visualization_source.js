/*
 * Visualization source
 */
define([
            'jquery',
            'underscore',
            'api/SplunkVisualizationBase',
            'api/SplunkVisualizationUtils',
            'd3'
            // Add required assets to this list
        ],
        function(
            $,
            _,
            SplunkVisualizationBase,
            vizUtils,
            d3
        ) {

      var isDarkTheme = vizUtils.getCurrentTheme && vizUtils.getCurrentTheme() === 'dark';

      // Extend from SplunkVisualizationBase
      return SplunkVisualizationBase.extend({
    
          initialize: function() {
              SplunkVisualizationBase.prototype.initialize.apply(this, arguments);
              this.$el = $(this.el);

              this.$el.addClass('splunk-scatter-overlay');
              if (isDarkTheme){
                this.$el.addClass('dark');
              }
              
              // Initialization logic goes here
          },

          _getEscapedProperty: function(name, config) {
              var propertyValue = config[this.getPropertyNamespaceInfo().propertyNamespace + name];
              return vizUtils.escapeHtml(propertyValue);
          },

          _getConfigParams: function(config) {
              this.mode = 'single';

              this.showLabels = vizUtils.normalizeBoolean(this._getEscapedProperty('showLabels', config), { default: true });
              this.showLegend = vizUtils.normalizeBoolean(this._getEscapedProperty('showLegend', config), { default: true });
              this.showTooltip = vizUtils.normalizeBoolean(this._getEscapedProperty('showTooltip', config), { default: true });

              //Custom Color Handling
              this.useColors = vizUtils.normalizeBoolean(this._getEscapedProperty('useColors', config), { default: true });
              this.colorMode = this._getEscapedProperty('colorMode', config) || 'categorical'; // or sequential
              this.minColor = this._getEscapedProperty('minColor', config) || '#d93f3c';
              this.maxColor = this._getEscapedProperty('maxColor', config) || '#3fc77a';
              this.numOfBins = this._getEscapedProperty('numOfBins', config) || 6;

              // this.useDrilldown = this._isEnabledDrilldown(config);

              this.showSelf = vizUtils.normalizeBoolean(this._getEscapedProperty('showSelf', config), { default: false });
              this.showBackwards = vizUtils.normalizeBoolean(
                this._getEscapedProperty('showBackwards', config),
                   { default: false }
              );
              this.styleBackwards = vizUtils.normalizeBoolean(
                  this._getEscapedProperty('styleBackwards', config),
                  { default: false }
              );
          },
          // Optionally implement to format data returned from search. 
          // The returned object will be passed to updateView as 'data'
          formatData: function(data, config) {

              // Format data 
              if(data.rows.length < 1) {
                      return false;
              }

              this._getConfigParams(config);

              var dataMap = data.rows.reduce(function(map, nodeArr) {

                  var point_time = nodeArr[0],
                      latency   = nodeArr[1],
                      trans_id  = nodeArr[2],
                      status    = nodeArr[3],
                      perc50    = nodeArr[4],
                      perc90    = nodeArr[5],
                      perc95    = nodeArr[6],
                      perc99    = nodeArr[7];

                  if (latency) {
                    var point_object = {
                        "date": point_time,
                        "ptime": point_time,
                        "latency": latency,
                        "id": trans_id,
                        "status": status
                    }
                    map.points.push(point_object);
                  } else {
                     var line_obj = {
                      "date": point_time,
                      "ptime": point_time,
                      "perc50": Number(perc50),
                      "perc90": Number(perc90),
                      "perc95": Number(perc95),
                      "perc99": Number(perc99)
                     };
                     map.lines.push(line_obj);
                  }

                  return map;
              }, {
                    "points": [],
                    "lines": [],
                }
              );
              return dataMap;
          },
    
          // Implement updateView to render a visualization.
          //  'data' will be the data object returned from formatData or from the search
          //  'config' will be the configuration property object
          updateView: function(data, config) {
            d3.selection.prototype.moveToFront = function() {
              return this.each(function(){
                this.parentNode.appendChild(this);
              });
            };

            d3.selection.prototype.moveToBack = function() {
              return this.each(function() {
                var firstChild = this.parentNode.firstChild;
                if (firstChild) {
                  this.parentNode.insertBefore(this, firstChild);
                }
              });
            };

            // values for all forces
            forceProperties = {
              center: {
                x: 0.5,
                y: 0.5
              },
              forceX: {
                  enabled: false,
                  strength: .1,
                  x: .5
              },
              forceY: {
                  enabled: false,
                  strength: .1,
                  y: .5
              },
              link: {
                enabled: true,
                distance: 60,
                iterations: 2
              },
              charge: {
                enabled: true,
                strength: -80,
                distanceMin: 1,
                distanceMax: 500
              },
              collide: {
                enabled: true,
                strength: 2,
                iterations: 2,
                radius: 4
              },
            }

            var run_status = true;
            var width = +d3.select('svgdiv').style('width').slice(0, -2)
            var height = +d3.select('svgdiv').style('height').slice(0, -2)

            var radius = 4.0;
            var color = d3.scaleOrdinal(d3.schemeCategory10);
            var temporal_net = $network_data;

            var hidden_link_strength = 0;
            var active_link_strength = 0.9;

            // create a dictionary with edges indexed by timestamps
            var edgesbytime = {};
            var time_stamps = temporal_net.links.map(link => link['time']);
            time_stamps.forEach(function(t) {
              edgesbytime[t] = [];
            });

            var mintime = d3.min(time_stamps);
            var maxtime = d3.max(time_stamps);

            var format = d3.timeFormat("%Y/%m/%d %H:%M:%S");
            var dt_from = format(new Date(mintime * 1000));
            var dt_to = format(new Date(maxtime * 1000));
            d3.select('#update').html('Animation has Started');

            jQuery('.slider-time').html(dt_from);
            jQuery('.slider-time2').html(dt_to);

            var min_val = Date.parse(dt_from)/1000;
            var max_val = Date.parse(dt_to)/1000;

            function zeroPad(num, places) {
              var zero = places - num.toString().length + 1;
              return Array(+(zero > 0 && zero)).join("0") + num;
            }

            function formatDT(__dt) {
              var year = __dt.getFullYear();
              var month = zeroPad(__dt.getMonth()+1, 2);
              var date = zeroPad(__dt.getDate(), 2);
              var hours = zeroPad(__dt.getHours(), 2);
              var minutes = zeroPad(__dt.getMinutes(), 2);
              var seconds = zeroPad(__dt.getSeconds(), 2);
              return year + '-' + month + '-' + date + ' ' + hours + ':' + minutes + ':' + seconds;
            };

            jQuery("#slider-range").slider({
              range: true,
              min: min_val,
              max: max_val,
              step: 10,
              values: [min_val, max_val],
              slide: function (e, ui) {
                var dt_cur_from = new Date(ui.values[0]*1000);
                jQuery('.slider-time').html(formatDT(dt_cur_from));

                var dt_cur_to = new Date(ui.values[1]*1000);
                jQuery('.slider-time2').html(formatDT(dt_cur_to));

                mintime = ui.values[0];
                maxtime = ui.values[1];

                restartAnimation()
              }
            });

            var formatTime = d3.timeFormat("%Y-%m-%dT%H:%M:%S.%L%Z");

            data = [];
            for (var i = 0; i < time_stamps.length; i++) {
              data.push(new Date(formatTime(time_stamps[i] * 1000)));
            }

            xScale = d3.scaleTime().domain(d3.extent(data))
              .range([0, width])
              .nice();

            var xAxis = d3.axisBottom(xScale);
            var svg_slider_label = d3.select("#slider-range-labels")
              .attr('width', width)
              .attr('height', 20);

            svg_slider_label.append("g")
              .call(xAxis)
              .style("text-anchor", "start");

            var svg = d3.select("#network_graph")
              .attr('width', width)
              .attr('height', height);

            // extract static links
            var links = [];
            var links_by_id = {};
            temporal_net.links.forEach(function(link) {
              id = String(link.source + '-' + link.target);
              edgesbytime[link.time].push(id);
              l = {
                'source': link.source,
                'target': link.target,
                'id': id,
                'strength': 0.0,
                'group': link.group
              };

              if (!contains(links, l)) {
                links.push(l);
                links_by_id[l.id] = l;
              }
            });

            // build the arrow.
            svg.append("svg:defs").selectAll("marker")
              .data(["end"])      // Different link/path types can be defined here
              .enter().append("svg:marker")    // This section adds in the arrows
              .attr("id", String)
              .attr("viewBox", "0 -5 10 10")
              .attr("refX", 22)
              .attr("refY", 0)
              .attr("markerWidth", 4)
              .attr("markerHeight", 4)
              .attr("orient", "auto")
              .append("svg:path")
              .attr("d", "M0,-5L10,0L0,5");

            var g = svg.append("g");

            var link = g.append("g")
              .attr("class", "tlinks")
              .selectAll("line")
              .data(links, function(d){return d.id;})
              .enter().append("line")
              .attr('stroke-opacity', 0.5)
              .attr("stroke", function(d) { return color(d.group); })
              .attr("id", function(d) { return d.id; })
              .attr("marker-end", "url(#end)");

            var node_g = g.append("g")
              .attr("class", "tnodes")
              .selectAll("circle")
              .data(temporal_net.nodes, function(d){return d.id;})
              .enter()
              .append("g");

            var node = node_g.append("circle")
              .attr('id', function(d) { return d.id; })
              .attr("r", radius)
              .attr("class", "tnodes")
              .call(d3.drag()
              .on("start", dragstarted)
              .on("drag", dragged)
              .on("end", dragended));

            node.append("title").text(function(d) { return d.id; });

            var text = node_g.append("text")
              .attr("x", [0, -8][0])
              .attr("y", [0, -8][1])
              .attr("id", function(d) {return d.id; })
              .text(function(d) { return d.id.replace(/(__.*)/, ''); })
              .attr("class", "active");

            var zoom_handler = d3.zoom()
              .on("zoom", zoom_actions);

            zoom_handler(svg);

            // build mapping to DOM objects once for performance reasons
            var time_step = d3.select('#timestep');
            var edges_to_dom = {};
            var nodes_to_dom = {};

            links.forEach(function(link) {
              edges_to_dom[link.id] = d3.select('svg #'+link.id);
            });

            temporal_net.nodes.forEach(function(n) {
              nodes_to_dom[n.id] = d3.select('svg #'+n.id);
            });

            // attach event handlers
            d3.select('#pause_btn').on("click", pauseAnimation);
            d3.select('#restart_btn').on("click", restartAnimation);

            // start animation
            var time = mintime;

            var intervl = setInterval(time_step_function, parseInt(document.getElementById("nMsPerFrame").value, 10));
            d3.select('#update').html('Animation has Started');
            console.log('Started animation.')

            var simulation = d3.forceSimulation();

            initializeSimulation();

            // set up the simulation and event to update locations after each tick
            function initializeSimulation() {
              simulation.nodes(temporal_net.nodes);
              initializeForces();
              simulation.on("tick", ticked);
            }

            // apply new force properties
            function updateForces() {
              // get each force by name and update the properties
              simulation.force("center")
                .x(width * forceProperties.center.x)
                .y(height * forceProperties.center.y);
              simulation.force("forceX")
                  .strength(forceProperties.forceX.strength * forceProperties.forceX.enabled)
                  .x(width * forceProperties.forceX.x);
              simulation.force("forceY")
                  .strength(forceProperties.forceY.strength * forceProperties.forceY.enabled)
                  .y(height * forceProperties.forceY.y);
              simulation.force("charge")
                .strength(forceProperties.charge.strength * forceProperties.charge.enabled)
                .distanceMin(forceProperties.charge.distanceMin)
                .distanceMax(forceProperties.charge.distanceMax);
              simulation.force("collide")
                .strength(forceProperties.collide.strength * forceProperties.collide.enabled)
                .radius(forceProperties.collide.radius)
                .iterations(forceProperties.collide.iterations);
              simulation.force("link")
                .id(function(d) {return d.id;})
                .distance(forceProperties.link.distance)
                .iterations(forceProperties.link.iterations)
                .links(forceProperties.link.enabled ? links : []);

              // updates ignored until this is run
              // restarts the simulation (important if simulation has already slowed down)
              simulation.alpha(1).restart();
            }

            // add forces to the simulation
            function initializeForces() {
              // add forces and associate each with a name
              simulation
                .force("forceX", d3.forceX())
                .force("forceY", d3.forceY())
                .force("link", d3.forceLink())
                .force("center", d3.forceCenter())
                .force("charge", d3.forceManyBody())
                .force("collide", d3.forceCollide());

              // apply properties to each of the forces
              updateForces();
            }

            // update the display based on the forces (but not positions)
            function updateDisplay() {
              node
                .attr("r", forceProperties.collide.radius)
                .attr("stroke-width", forceProperties.charge.enabled==false ? 0 : Math.abs(forceProperties.charge.strength)/15);

              link
                .attr("stroke-width", forceProperties.link.enabled ? 1 : .5)
                .attr("opacity", forceProperties.link.enabled ? 1 : 0);
            }

            // convenience function to update everything (run after UI input)
            function updateAll() {
              updateForces();
              updateDisplay();
            }

            // update the display positions after each simulation tick
            function ticked() {
              link
                .attr("x1", function(d) { return d.source.x; })
                .attr("y1", function(d) { return d.source.y; })
                .attr("x2", function(d) { return d.target.x; })
                .attr("y2", function(d) { return d.target.y; });

              text.attr("transform", transform);
              text.attr("cx", function(d) { return d.x; })
                .attr("cy", function(d) { return d.y; });

              node
                .attr("cx", function(d) { return d.x; })
                .attr("cy", function(d) { return d.y; });
            }

            // animates one time step
            function time_step_function() {
              var evPerFrame = parseInt(document.getElementById("nEvPerFrame").value, 10);
              var format = d3.timeFormat("%Y/%m/%d %H:%M:%S");
              var formatted_time_step_start = format(new Date(time * 1000))
              var formatted_time_step_end = format(new Date((time + evPerFrame) * 1000))
              time_step.html('Time Step: ' + formatted_time_step_start + " to " + formatted_time_step_end);

              // pause animation
              if(time > maxtime) {
                run_status = false;
                clearInterval(intervl);
                d3.select('#update').html('Animation has Completed');
                console.log('Animation has Completed')
              }

              // reset all links to hidden
              for (id in edges_to_dom) {
                try {
                  edges_to_dom[l.id].attr('class', 'links');
                  links_by_id[id].strength = hidden_link_strength;
                  // edges_to_dom[id].attr('class', 'hidden');
                }
                catch(err) {
                  console.log('Error: Could not find DOM object with id ' + id);
                }
              }

              // reset all nodes to inactive
              for (id in nodes_to_dom) {
                try {
                  nodes_to_dom[id].attr("class", "tnodes");
                }
                catch(err) {
                  console.log('Error: Could not find DOM object with id ' + id);
                }
              }

              var look_ahead = parseInt(document.getElementById("nLookAhead").value, 10);
              var look_behind = parseInt(document.getElementById("nLookBehind").value, 10);

              // change nodes and links in current time slice
              for (ti=Math.max(mintime, time - look_behind); ti<=time + look_ahead; ti++) {
                if (ti in edgesbytime) {
                  edgesbytime[ti].forEach(function(id) {
                    links_by_id[id].strength = active_link_strength;

                    // links that are currently active
                    time_update = time - parseInt(document.getElementById("nEvPerFrame").value, 10);
                    if (ti >= time_update+1 && ti <= time) {
                      node_ids = id.split('-');
                      try {
                        edges_to_dom[id].attr('class', 'active').moveToFront();
                      }
                      catch(err){
                        console.log('Error: Could not find DOM link with id ' + id);
                      }
                      try {
                        nodes_to_dom[node_ids[0]].attr('class', 'active').moveToFront();
                      }
                      catch(err){
                        console.log('Error: Could not find DOM node with id ' + node_ids[0]);
                      }
                      try {
                        nodes_to_dom[node_ids[1]].attr('class', 'active').moveToFront();
                      }
                      catch(err){
                        console.log('Error: Could not find DOM node with id ' + node_ids[1]);
                      }
                    }

                    // links in current time slice that are not active
                    else {
                      edges_to_dom[id].attr('class', 'tlinks');
                    }
                  });
                }
              }

              text.moveToFront();
              time += parseInt(document.getElementById("nEvPerFrame").value, 10);
            }

            function pauseAnimation() {
              if (run_status) {
                run_status = false;
                clearInterval(intervl);
                simulation.stop();
                d3.select('#update').html('Animation has Paused');
                d3.select('#pause_btn').html('Start');
                console.log('Paused animation.')
              } else {
                intervl = setInterval(time_step_function, parseInt(document.getElementById("nMsPerFrame").value, 10));
                run_status = true;
                simulation.restart();
                d3.select('#update').html('Animation has Resumed');
                d3.select('#pause_btn').html('Pause');
                console.log('Resumed animation.')
              }
            }

            function zoom_actions(){
              g.attr("transform", d3.event.transform)
            }

              // Init nEvPerFrame
              d3.select('#update').property('value', '25');

              // Register event handler for changes to nEvPerFrame
              d3.select("#nEvPerFrame").on("change", function() {
                d3.select('#nEvPerFrame').property('value', this.value);
                restartAnimation()
              })

            function restartAnimation() {
              if (run_status)
                clearInterval(intervl);
                time = mintime;

                var evPerFrame = parseInt(document.getElementById("nEvPerFrame").value, 10);
                var format = d3.timeFormat("%Y/%m/%d %H:%M:%S");
                var formatted_time_step_start = format(new Date(time * 1000))
                var formatted_time_step_end = format(new Date((time + evPerFrame) * 1000))

              time_step.html('Time Step: ' + formatted_time_step_start + " to " + formatted_time_step_end);
                d3.select('#pause_btn').html('Pause');
                run_status = true;
                intervl = setInterval(time_step_function, parseInt(document.getElementById("nMsPerFrame").value, 10));
                d3.select('#update').html('Animation has been Restarted');
                console.log('Restarted animation.')
              }

            function transform(d) {
              return "translate(" + d.x + "," + d.y + ")";
            }

            function dragstarted(d) {
              if (!d3.event.active)
                simulation.alphaTarget(0.3).restart();
              d.fx = d.x;
              d.fy = d.y;
            }

            function dragged(d) {
              d.fx = d3.event.x;
              d.fy = d3.event.y;
            }

            function dragended(d) {
              if (!d3.event.active)
                simulation.alphaTarget(0.01);
            }

            function contains(array, obj) {
              var i = array.length;
              while (i--) {
                if (array[i] === obj) {
                  return true;
                }
              }
              return false;
            }
          },

          // Search data params
          getInitialDataParams: function() {
              return ({
                  outputMode: SplunkVisualizationBase.ROW_MAJOR_OUTPUT_MODE,
                  count: 100000
              });
          },

          // Override to respond to re-sizing events
          reflow: function() {
              this.invalidateUpdateView();
          },
          _drilldown: function(d, i) {
              if(d3.event.defaultPrevented) {
                  return;
              }

              var payload = {
                  action: SplunkVisualizationBase.FIELD_VALUE_DRILLDOWN,
                  data: {}
              };

              payload.data["traceId"] = d.id;

              this.drilldown(payload, d3.event);

          }
    });
});