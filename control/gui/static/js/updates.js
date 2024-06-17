$(document).ready(function () {
  // Tabs for settings and operation
  $("#tabs").tabs({heightStyle: "auto"});

  // Start up gain slider
  $("#gainslider").slider({
    value:2,
    min: 1,
    max: 4,
    step: 0.5,
    slide: function( event, ui ) {
      $("#gainval").text("Gain power: " + ui.value);
    }
  });
  $("#gainval").text("Gain power: " + $("#gainslider").slider("value"));

  // Set up time slider
  $("#timeslider").slider({
    range: true,
    values: [0, 10],
    min: 0,
    max: 20,
    step: 1,
    slide: function( event, ui ) {
      $("#timeval").text( "Time window: " + ui.values[0] + " - " + ui.values[1] + " \u03BCs");
    }
  });
  $("#timeval").text("Time window: " + $("#timeslider").slider("values", 0) +
      " - " + $("#timeslider").slider("values", 1) + " \u03BCs");

  // GNSS status update
  function update_gnss() {
    $.getJSON("/_get_gnss", {}, function (data) {
      $("td#fix").text(data.fix);
      $("td#date").text(data.date);
      $("td#time").text(data.time);
      $("td#lon").text(data.lon);
      $("td#lat").text(data.lat);
      $("td#hgt").text(data.hgt);
      
      // Set background color based on GNSS status
      if (data.tfix < 2 && data.twrite < 2 && data.fix == "3D fix") {
        $("table.gnss").css("background-color", "#36ff00");
      } else if (data.tfix < 10 && data.twrite < 10 && data.fix != "no fix") {
        $("table.gnss").css("background-color", "orange");
      } else {
        $("table.gnss").css("background-color", "red");
      }
    });
    return false;
  }

  // Radar status update
  function update_radar() {
    $.getJSON("/_get_radar", {}, function (data) {
      $("td#ntrc").text(data.ntrc);
      $("td#nbuf").text(data.nbuf);
      $("td#prf").text(data.prf);
      $("td#adc").text(data.adc);
    });
    return false;
  }
  
  // Start button
  $("#buttonStart").click(function() {
    var trigger = $("#trigger").val();
    var pretrig = $("#pretrig").val();
    var spt = $("#spt").val();
    var stack = $("#stack").val();
  
    $.post({
      url: "/_start",
      contentType: "application/json",
      data: JSON.stringify({
        trigger: trigger,
        pretrig: pretrig,
        spt: spt,
        stack: stack
      }),
      success: function(data) {}
    });
  });
  
  // Stop button
  $("#buttonStop").click(function() {
    $.post("/_stop", function (data) {});
  });

  update_radar();
  update_gnss();

  var interval = setInterval(update_radar, 1000);
  var interval = setInterval(update_gnss, 1000);

  // Set gain text
  //$('#gaintext').html( $('#gain').val();
});
