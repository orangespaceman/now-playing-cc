(function() {
  var lastData = null;

  function poll() {
    fetch(`static/data.json?${Math.random()}`)
      .then(function(response) { return response.json(); })
      .then(function(json) { updateDisplay(json); })
      .catch(function(e) { handleError(e); });

    setTimeout(poll, 5000);
  }

  function updateDisplay(data) {
    updateTitle(data.title);
    updateArtist(data.artist);
    updateAlbum(data.album_name);
    updateDatetime(data.last_updated);
    updateState(data);
    updateArtwork(data);

    lastData = data;
  }

  function updateTitle(title) {
    updateFieldValue('title', title);
  }

  function updateArtist(artist) {
    updateFieldValue('artist', artist);
  }

  function updateAlbum(album_name) {
    updateFieldValue('album_name', album_name);
  }

  function updateDatetime(last_updated) {
    updateFieldValue('last_updated', last_updated);
    const el = document.querySelector('.Debug-datetimeTextRevealer');
    el.classList.add('u-revealer');
    setTimeout(function() {
      el.classList.remove('u-revealer');
    }, 4800);
  }

  function updateState(data) {
    data.player_state = (data.player_state === 'PLAYING') ? 'Now playing' : 'Not playing';
    updateFieldValue('player_state', data.player_state);
  }

  function updateArtwork(data) {
    console.log(`Image: ${data.image || 'none'}`);
    const el = document.querySelector(`[data-field="image"]`);

    // same image as before, do nothing
    if (lastData && lastData.image && data.image === lastData.image) return;

    // no image, show particles
    if (!data || !data.image || data.image.length === 0) {
      el.classList.add('u-fadeOut');
      particles.restart();
      return;
    }

    // new image
    el.classList.add('u-fadeOut');
    const val = data.image;
    setTimeout(function() {
      updateAndFadeInImageEl(el, val);
    }, 500);
  }

  function updateFieldValue(field, val) {
    console.log(`${field}: ${val}`);
    if (lastData && val === lastData[field]) return;
    var els = document.querySelectorAll(`[data-field="${field}"]`);
    [].forEach.call(els, function(el) {
      el.classList.add('u-fadeOut');
      setTimeout(function() {
        updateAndFadeInTextEl(el, val);
      }, 500);
    });
  }

  function updateAndFadeInTextEl(el, val) {
    el.textContent = val;
    el.classList.remove('u-fadeOut');
  }

  function updateAndFadeInImageEl(el, val) {
    el.style.backgroundImage = `url(static/cache/${val})`;
    el.classList.remove('u-fadeOut');
    particles.stop();
  }


  function handleError(e) {
    console.log('ERROR', e);
  }

  particles.init();
  poll();
})();

window.addEventListener("touchmove", function(event) {
  event.preventDefault();
}, false);
