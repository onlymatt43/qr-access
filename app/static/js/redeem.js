(() => {
  const opaqueFromUrl = document.getElementById('opaque')?.value || '';
  const deviceId = document.getElementById('device_id')?.value || '';
  const logEl = document.getElementById('log');
  const log = (m) => { if (logEl) logEl.textContent += m + '\n'; };

  // Extract opaque token from a raw QR payload.
  // Accepts absolute URLs, relative URLs (e.g. /redeem?c=...), or direct opaque strings.
  function extractOpaque(raw) {
    if (!raw) return '';
    const s = String(raw).trim();
    // Try URL with base (handles absolute and relative forms)
    try {
      let u;
      try { u = new URL(s); }
      catch { u = new URL(s, window.location.origin); }
      const c = u.searchParams.get('c');
      if (c) return c;
    } catch { /* not a URL */ }
    // Try regex extraction of ?c=
    const m = s.match(/[?&]c=([^&]+)/);
    if (m && m[1]) return decodeURIComponent(m[1]);
    // Fallback: treat the string as the opaque token itself
    return s;
  }

  async function redeem(opaque){
    try {
      const r = await fetch('/api/redeem', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ opaque, device_id: deviceId })
      });
      let data;
      try { data = await r.json(); }
      catch { data = { error: 'bad_response', status: r.status }; }
      if(!r.ok){ log('Erreur: ' + (data.error || JSON.stringify(data))); return; }
      log('OK, ouverture du contenu ' + data.content_id);

      // Récupère le HTML avec le token et affiche-le dans un iframe sandboxé
  const rr = await fetch('/api/content/' + data.content_id, {
        headers: { 'Authorization': 'Bearer ' + data.token }
      });
      const html = await rr.text();
      let frame = document.getElementById('content-frame');
      if (!frame) {
        frame = document.createElement('iframe');
        frame.id = 'content-frame';
        frame.setAttribute('sandbox', '');
        frame.style.width = '100%';
        frame.style.minHeight = '400px';
        document.body.innerHTML = '';
        document.body.appendChild(frame);
      }
      const doc = frame.contentDocument || frame.contentWindow?.document;
      if (doc) {
        doc.open();
        doc.write(html);
        doc.close();
      }
    } catch (e) {
      const msg = (e && e.message) ? e.message : String(e);
      log('Erreur réseau: ' + msg);
    }
  }

  // Si l'URL contient déjà ?c=..., tenter directement
  if (opaqueFromUrl) redeem(opaqueFromUrl);

  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  const ctx = canvas ? canvas.getContext('2d') : null;
  let mediaStream = null, ticking = false, detector = null;

  async function startCam(){
    if(!('BarcodeDetector' in window)){
      log("BarcodeDetector non supporté.");
      return;
    }
    try {
      detector = new BarcodeDetector({formats: ['qr_code']});
    } catch(e){ log('BarcodeDetector indisponible: ' + e); return; }
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment'}});
    } catch(e) {
      log('Impossible d\'accéder à la caméra : ' + (e.message || e));
      return;
    }
    if (video) {
      video.srcObject = mediaStream;
      await video.play();
    }
    ticking = true;
    scanLoop();
  }

  function stopCam(){
    ticking = false;
    if(mediaStream){ mediaStream.getTracks().forEach(t=>t.stop()); mediaStream=null; }
  }

  async function scanLoop(){
    if(!ticking || !video) return;
    try{
      const barcodes = await detector.detect(video);
      if(barcodes && barcodes.length){
        const raw = (barcodes[0].rawValue||'').trim();
        log('QR détecté');
        stopCam();
  // Si le QR contient ?c=..., extraire; sinon, prendre le texte brut
  const opaque = extractOpaque(raw);
        if(opaque){ return redeem(opaque); }
        log('Format QR non reconnu');
      }
    }catch(e){ /* ignore */ }
    if (ctx && canvas && video) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    }
    requestAnimationFrame(scanLoop);
  }

  const startBtn = document.getElementById('btn-start');
  const stopBtn = document.getElementById('btn-stop');
  if (startBtn) startBtn.onclick = startCam;
  if (stopBtn) stopBtn.onclick = stopCam;

  const fileInput = document.getElementById('file');
  if (fileInput) fileInput.addEventListener('change', async (e)=>{
    const file = e.target.files && e.target.files[0];
    if (!file) { log('Aucune image sélectionnée.'); return; }
    if (!canvas || !ctx) { log('Canvas indisponible.'); return; }

    const img = new Image();
    img.onload = async function() {
      try {
        canvas.width = img.width;
        canvas.height = img.height;
        ctx.drawImage(img, 0, 0, img.width, img.height);

        if (!('BarcodeDetector' in window)) {
          // Fallback serveur
          await uploadToServer(file);
          return;
        }
        if (!detector) {
          try { detector = new BarcodeDetector({ formats: ['qr_code'] }); }
          catch (e) { log('BarcodeDetector indisponible: ' + e); return; }
        }
        const barcodes = await detector.detect(canvas);
        if (barcodes && barcodes.length) {
          log("QR détecté dans l'image.");
          let raw = (barcodes[0].rawValue || '').trim();
          const opaque = extractOpaque(raw);
          if (opaque) { return redeem(opaque); }
          log('Format QR non reconnu');
        } else {
          // Fallback serveur si détection locale échoue
          await uploadToServer(file);
        }
      } catch (err) {
        log('Erreur lors du décodage: ' + (err?.message || err));
      }
    };
  img.onerror = function(){ log('Impossible de charger l\'image.'); };
    // Utiliser un Object URL pour charger rapidement l'image sélectionnée
    const url = URL.createObjectURL(file);
    img.src = url;
  });

  async function uploadToServer(file) {
    try {
      const fd = new FormData();
      fd.append('image', file, file.name || 'qr.png');
      const r = await fetch('/api/decode', { method: 'POST', body: fd });
      const data = await r.json();
      if (!r.ok) { log('Decode serveur: ' + (data.error || r.status)); return; }
      if (data && data.ok && data.raw) {
  let raw = String(data.raw).trim();
  const opaque = extractOpaque(raw);
        if (opaque) return redeem(opaque);
        log('Format QR non reconnu (serveur).');
      } else {
        log('Aucun QR détecté (serveur).');
      }
    } catch (e) {
      log('Erreur decode serveur: ' + (e.message || e));
    }
  }
})();
