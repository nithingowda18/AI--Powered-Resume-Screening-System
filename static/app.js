document.addEventListener('DOMContentLoaded', () => {
 const input=document.getElementById('resumes'), list=document.getElementById('file-list'), zone=document.getElementById('dropzone');
 if(input && list){
  const render=()=>{ list.innerHTML=''; const files=Array.from(input.files||[]); if(!files.length){list.innerHTML='<span class="empty-files">No files selected yet</span>';return;}
   files.forEach(f=>{const row=document.createElement('div');row.className='file-row';const name=document.createElement('span');name.textContent=f.name;const size=document.createElement('small');size.textContent=(f.size/1024/1024).toFixed(2)+' MB';row.append(name,size);list.append(row);});
  }; input.addEventListener('change',render);
  if(zone){['dragenter','dragover'].forEach(e=>zone.addEventListener(e,event=>{event.preventDefault();zone.classList.add('dragover')}));['dragleave','drop'].forEach(e=>zone.addEventListener(e,event=>{event.preventDefault();zone.classList.remove('dragover')}));zone.addEventListener('drop',event=>{if(event.dataTransfer?.files?.length){input.files=event.dataTransfer.files;render()}})}
 }
 const jd=document.getElementById('job-description'), counter=document.getElementById('char-count'); if(jd&&counter)jd.addEventListener('input',()=>counter.textContent=jd.value.length);
 const form=document.getElementById('screen-form'), btn=document.getElementById('submit-btn'); if(form&&btn)form.addEventListener('submit',()=>{btn.disabled=true;btn.textContent='Analyzing resumes…';});
});
