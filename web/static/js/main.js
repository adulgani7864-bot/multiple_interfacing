document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.use-template').forEach(btn=>{
    btn.addEventListener('click', (e)=>{
      const card = e.target.closest('.template-card');
      const id = card.dataset.id;
      alert('Template '+id+' selected (placeholder)');
    });
  });

  // carousel
  const carousel = document.getElementById('carousel');
  if (carousel){
    let pos = 0;
    const slideEl = carousel.querySelector('.slide');
    const computed = getComputedStyle(carousel);
    const gap = parseInt(computed.gap || computed.columnGap || '0', 10) || 0;
    const step = slideEl ? (slideEl.offsetWidth + gap) : 320;
    let timer = setInterval(()=>{ advance(); }, 2600);
    function advance(){
      pos += step;
      const max = carousel.scrollWidth - carousel.clientWidth;
      if (pos > max) pos = 0;
      carousel.scrollTo({left: pos, behavior: 'smooth'});
    }
    const prev = document.getElementById('prev');
    const next = document.getElementById('next');
    if (prev && next){
      prev.addEventListener('click', ()=>{ pos = Math.max(0, pos - step); carousel.scrollTo({left: pos, behavior:'smooth'}); resetTimer(); });
      next.addEventListener('click', ()=>{ advance(); resetTimer(); });
    }
    function resetTimer(){ clearInterval(timer); timer = setInterval(()=>{ advance(); }, 2600); }
  }

  // upload preview
  const fileInput = document.getElementById('fileInput');
  const preview = document.getElementById('uploadPreview');
  const previewImg = document.getElementById('previewImg');
  if (fileInput){
    fileInput.addEventListener('change', (e)=>{
      const f = e.target.files[0];
      if (!f) return;
      const url = URL.createObjectURL(f);
      previewImg.src = url;
      preview.style.display = 'block';
    });
  }

  // modal
  const modal = document.getElementById('templateModal');
  const modalImg = document.getElementById('modalImg');
  const modalClose = document.getElementById('modalClose');
  document.querySelectorAll('.preview-template').forEach(btn=>{
    btn.addEventListener('click', (e)=>{
      const card = e.target.closest('.template-card');
      const img = card.querySelector('img').src;
      modalImg.src = img; modal.style.display = 'flex';
    });
  });
  if (modalClose) modalClose.addEventListener('click', ()=> modal.style.display='none');
});
