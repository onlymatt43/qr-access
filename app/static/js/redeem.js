(() => {
  const opaqueFromUrl = document.getElementById('opaque')?.value || '';
  const deviceId = document.getElementById('device_id')?.value || '';
  const logEl = document.getElementById('log');
  const log = (m) => { if (logEl) logEl.textContent += m + '\n'; };

  async function redeem(opaque){
    try {
      const r = await fetch('/api/redeem', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ opaque, device_id: deviceId })
      });
      const data = await r.json();
      if(!r.ok){ log('Erreur: ' + (data.error || JSON.stringify(data))); return; }
      log('OK, ouverture du contenu ' + data.content_id);

      // Récupère le HTML avec le token et affiche-le dans un iframe sandboxé
      const rr = await fetch('/content/' + data.content_id, {
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
      log('Erreur réseau: ' + (e.message || e));
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
        // Si le QR est une URL avec ?c=..., extraire c ; sinon, prendre le texte brut
        let opaque = null;
        try {
          const u = new URL(raw);
          opaque = u.searchParams.get('c');
        } catch { opaque = raw; }
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
    log('Décodage d\'image non disponible sans lib externe (jsQR).');
  });
})();
