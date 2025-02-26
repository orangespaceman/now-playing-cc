/*
 * Particles
 * https://github.com/orangespaceman/js-particles
 */
var particles = function() {

  "use strict";

  /*
   * global variables
   */
  var
      // HTML canvas element
      canvas,

      // canvas draw context
      ctx,

      // collection of existing particles
      particles = [],

      // run?
      isRunning = true,

      // configurable options
      config = {

          // number of particles to draw
          particleCount : 40,

          // minimum distance for each particle to affect another
          minimumAffectingDistance : 50
      };

  /*
   * init
   */
  function init () {
      drawCanvas();
      createParticles();
      loop();

      // resize canvas on page resize
      window.addEventListener("resize", function (event) {
          drawCanvas();
      });
  }


  /*
   * start redraw loop logic
   */
  function loop () {
      clear();
      update();
      draw();
      queue();
  }

  /*
   * wipe canvas ready for next redraw
   */
  function clear () {
      if (!isRunning) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  /*
   * update particle positions
   */
  function update () {
      if (!isRunning) return;

      // update each particle's position
      for (var count = 0; count < particles.length; count++) {

          var p = particles[count];

          // Change the velocities
          p.x += p.vx;
          p.y += p.vy;

          // Bounce a particle that hits the edge
          if(p.x + p.radius > canvas.width || p.x - p.radius < 0) {
              p.vx = -p.vx;
          }

          if(p.y + p.radius > canvas.height || p.y - p.radius < 0) {
              p.vy = -p.vy;
          }

          // Check particle attraction
          for (var next = count + 1; next < particles.length; next++) {
              var p2 = particles[next];
              calculateDistanceBetweenParticles(p, p2);
          }
      }
  }

  /*
   * update visual state - draw each particle
   */
  function draw () {
      if (!isRunning) return;
      for (var count = 0; count < particles.length; count++) {
          var p = particles[count];
          p.draw();
      }
  }

  /*
   * prepare next redraw when the browser is ready
   */
  function queue () {
    window.requestAnimationFrame(loop);
  }

  function stop () {
    isRunning = false;
    clear();
  }

  function restart () {
    if (!isRunning) {
      particles = [];
      createParticles();
      isRunning = true;
    }
  }

  // go!
  return {
    init,
    stop,
    restart
  };


/*
* Objects
*/

  /*
   * Particle
   */
  function Particle () {

      // Position particle
      this.x = Math.random() * canvas.width;
      this.y = Math.random() * canvas.height;

      // Give particle velocity, between -1 and 1
      this.vx = -1 + Math.random() * 2;
      this.vy = -1 + Math.random() * 2;

      // Give particle a radius
      this.radius = 4;

      // draw particle
      this.draw = function () {
          ctx.fillStyle = "white";
          ctx.beginPath();
          ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2, false);
          ctx.fill();
      }
  }

  /*
   * Draw canvas
   */
  function drawCanvas () {
      canvas = document.querySelector("canvas");
      ctx = canvas.getContext("2d");

      // set canvas to full page dimensions
      // canvas.width = window.innerWidth;
      // canvas.height = window.innerHeight;
      canvas.width = canvas.offsetWidth;
      canvas.height = canvas.offsetHeight;
  }

  /*
   * Create particles
   */
  function createParticles () {
      for(var i = 0; i < config.particleCount; i++) {
          particles.push(new Particle());
      }
  }


  /*
   * Distance calculator between two particles
   */
  function calculateDistanceBetweenParticles (p1, p2) {

      var dist,
          dx = p1.x - p2.x,
          dy = p1.y - p2.y;

      dist = Math.sqrt(dx*dx + dy*dy);

      // Check whether distance is smaller than the min distance
      if(dist <= config.minimumAffectingDistance) {

          // set line opacity
          var opacity = 1 - dist/config.minimumAffectingDistance;

          // Draw connecting line
          ctx.beginPath();
          ctx.strokeStyle = "rgba(255, 255, 255, " + opacity +")";
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
          ctx.closePath();

          // Calculate particle acceleration
          var ax = dx / 2000,
              ay = dy / 2000;

          // Apply particle acceleration
          p1.vx -= ax;
          p1.vy -= ay;

          p2.vx += ax;
          p2.vy += ay;
      }
  }
}();
