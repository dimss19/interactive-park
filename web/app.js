const state={config:null,media:null,status:null,areas:{},selected:null,drawing:false,dragIndex:null};
const $=id=>document.getElementById(id);

async function api(url,options={}){
  const response=await fetch(url,options);
  let body={};
  try{body=await response.json()}catch{}
  if(!response.ok)throw new Error(body.detail||`Request gagal (${response.status})`);
  return body;
}

function notify(message,error=false){
  $('notice').textContent=message;
  $('notice').className=`notice${error?' error':''}`;
  if(message)setTimeout(()=>{if($('notice').textContent===message)$('notice').textContent=''},5000);
}

function setBusy(button,busy,label='Memproses...'){
  if(busy){button.dataset.label=button.textContent;button.textContent=label;button.disabled=true}
  else{button.textContent=button.dataset.label||button.textContent;button.disabled=false}
}

document.querySelectorAll('.tab').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('.tab,.tab-panel').forEach(item=>item.classList.remove('active'));
  button.classList.add('active');
  $(`tab-${button.dataset.tab}`).classList.add('active');
  if(button.dataset.tab==='mapping')resizeCanvas();
}));

async function loadConfiguration(){
  [state.config,state.media]=await Promise.all([api('/api/config'),api('/api/media')]);
  state.areas=structuredClone(state.config.areas||{});
  renderSourceOptions();
  renderAreaOptions();
  renderSfxOptions();
}

function renderSourceOptions(){
  const current=String(state.config.video_source);
  const options=[{path:'0',name:'Webcam 0'},{path:'1',name:'Webcam 1'},...state.media.videos];
  $('sourceSelect').innerHTML=options.map(item=>`<option value="${escapeHtml(item.path)}">${escapeHtml(item.name)}</option>`).join('');
  if(options.some(item=>String(item.path)===current))$('sourceSelect').value=current;
}

function renderAreaOptions(preferred=null){
  const keys=Object.keys(state.areas);
  state.selected=preferred&&state.areas[preferred]?preferred:(state.selected&&state.areas[state.selected]?state.selected:keys[0]||null);
  $('areaSelect').innerHTML=keys.length?keys.map(key=>`<option value="${escapeHtml(key)}">${escapeHtml(state.areas[key].name||key)} · ${escapeHtml(state.areas[key].type||'')}</option>`).join(''):'<option value="">Belum ada area</option>';
  if(state.selected)$('areaSelect').value=state.selected;
  populateAreaForm();highlightPresetButtons();drawMapping();
}

function renderSfxOptions(){
  const items=Object.keys((state.config.audio||{}).sfx||{});
  const current=$('areaSfx').value;
  $('areaSfx').innerHTML='<option value="">Tanpa SFX</option>'+items.map(name=>`<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
  if(items.includes(current))$('areaSfx').value=current;
}

function populateAreaForm(){
  const area=state.areas[state.selected];
  $('areaId').value=state.selected||'';$('areaName').value=area?.name||'';$('areaType').value=area?.type||'plant';
  $('areaSfx').value=area?.audio||'';
}

function highlightPresetButtons(){
  document.querySelectorAll('.preset').forEach(button=>button.classList.toggle('selected',button.dataset.area===state.selected));
}

function escapeHtml(value){return String(value).replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]))}

async function refreshStatus(){
  try{
    const s=await api('/api/status');state.status=s;
    $('connection').textContent=s.source_ok?'ONLINE':s.running?'STARTING':'OFFLINE';
    $('connection').className=`badge${s.source_ok?' ok':''}`;
    $('sourceStatus').textContent=`${s.source_type}: ${s.source}`;
    $('resolution').textContent=s.frame_width?`${s.frame_width} × ${s.frame_height}`:'-';
    $('fps').textContent=s.fps;$('persons').textContent=s.person_count;
    $('interactionStatus').textContent=s.last_error||`Area aktif: ${s.active_areas.join(', ')||'-'} · Touch: ${s.active_touches.join(', ')||'-'}`;
    renderSfxList(s.audio);
  }catch(error){$('connection').textContent='ERROR';notify(error.message,true)}
}

function renderSfxList(audio){
  $('audioInfo').textContent=`Audio ${audio.enabled?'aktif':'nonaktif'} · Mixer ${audio.mixer_ready?'siap':'tidak siap'} · Master ${Math.round(audio.master_volume*100)}%`;
  $('sfxList').innerHTML=audio.items.map(item=>`<div class="list-item"><div><b>${escapeHtml(item.name)}</b><div class="${item.loaded?'state-ok':'state-bad'}">${item.loaded?'Siap':item.exists?'Mixer gagal':'File tidak ada'} · volume ${item.volume}</div></div><div class="list-actions"><button onclick="playSfx('${escapeHtml(item.name)}')">Tes</button><button class="secondary" onclick="stopSfx('${escapeHtml(item.name)}')">Stop</button><button class="danger" onclick="removeSfx('${escapeHtml(item.name)}')">Hapus</button></div></div>`).join('')||'<p class="hint">Belum ada SFX.</p>';
}

$('applySource').addEventListener('click',async()=>{
  const button=$('applySource');setBusy(button,true,'Mengganti...');
  try{await api('/api/source',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({source:$('sourceSelect').value})});notify('Sumber berhasil diganti');await loadConfiguration()}
  catch(error){notify(error.message,true)}finally{setBusy(button,false)}
});

$('videoUpload').addEventListener('submit',async event=>{
  event.preventDefault();const button=event.submitter;setBusy(button,true,'Mengupload...');
  const form=new FormData();form.append('file',$('videoFile').files[0]);
  try{const result=await api('/api/videos/upload',{method:'POST',body:form});state.media=await api('/api/media');renderSourceOptions();$('sourceSelect').value=result.path;notify('Video terupload. Klik Gunakan sumber untuk mengaktifkan.')}
  catch(error){notify(error.message,true)}finally{setBusy(button,false)}
});

$('checkSource').addEventListener('click',async()=>{
  $('sourceResult').textContent='Memeriksa...';
  try{const result=await api('/api/source/check');$('sourceResult').textContent=`${result.message} (${result.width} × ${result.height})`}
  catch(error){$('sourceResult').textContent=error.message}
});

const standardAreas={
  garden:{name:'AREA TAMAN',type:'garden',color:[0,210,70],points:[[.03,.05],[.97,.05],[.97,.95],[.03,.95]]},
  plant_left:{name:'TANAMAN KIRI',type:'plant',color:[0,120,255],points:[[.03,.18],[.33,.18],[.33,.82],[.03,.82]]},
  plant_right:{name:'TANAMAN KANAN',type:'plant',color:[255,110,0],points:[[.67,.18],[.97,.18],[.97,.82],[.67,.82]]},
  walkway:{name:'JALAN',type:'walkway',color:[210,210,210],points:[[.40,.08],[.60,.08],[.76,.95],[.24,.95]]}
};

function ensureStandardArea(key){
  if(!state.status?.frame_width||!state.status?.frame_height){notify('Tunggu resolusi video tersedia',true);return false}
  if(!state.areas[key]){
    const preset=standardAreas[key];
    const defaultSfx=Object.prototype.hasOwnProperty.call((state.config.audio||{}).sfx||{},'plant_touch')?'plant_touch':null;
    state.areas[key]={name:preset.name,type:preset.type,color:preset.color,show_overlay:true,
      polygon:preset.points.map(([x,y])=>[Math.round(x*state.status.frame_width),Math.round(y*state.status.frame_height)]),
      audio:preset.type==='plant'?defaultSfx:null};
  }
  return true;
}

function selectStandardArea(key){
  if(!ensureStandardArea(key))return;
  state.selected=key;state.drawing=false;renderAreaOptions(key);updateMappingMode();
  notify(`${standardAreas[key].name} dipilih. Seret titik bulat untuk menyesuaikan area.`);
}

document.querySelectorAll('.preset').forEach(button=>button.addEventListener('click',()=>selectStandardArea(button.dataset.area)));
$('setupStandard').addEventListener('click',()=>{
  if(!state.status?.frame_width)return notify('Tunggu video aktif sebelum membuat preset',true);
  Object.keys(standardAreas).forEach(ensureStandardArea);state.selected='garden';state.drawing=false;renderAreaOptions('garden');updateMappingMode();
  notify('Area Taman, Tanaman Kiri, Tanaman Kanan, dan Jalan sudah disiapkan. Sesuaikan titik lalu simpan mapping.');
});

$('areaSelect').addEventListener('change',event=>{state.selected=event.target.value;state.drawing=false;renderAreaOptions(state.selected);updateMappingMode()});

$('addArea').addEventListener('click',()=>{
  const id=$('areaId').value.trim();
  if(!/^[a-zA-Z0-9_-]+$/.test(id))return notify('Isi ID area yang valid terlebih dahulu',true);
  if(state.areas[id])return notify('ID area sudah digunakan',true);
  state.areas[id]={name:$('areaName').value.trim()||id.toUpperCase(),type:$('areaType').value,color:defaultColor($('areaType').value),show_overlay:true,polygon:[],audio:$('areaSfx').value||null};
  state.selected=id;state.drawing=true;renderAreaOptions(id);updateMappingMode();notify('Area ditambahkan. Klik titik-titik polygon pada video.')
});

$('updateArea').addEventListener('click',()=>{
  if(!state.selected)return notify('Pilih area terlebih dahulu',true);
  const newId=$('areaId').value.trim();
  if(!/^[a-zA-Z0-9_-]+$/.test(newId))return notify('ID area tidak valid',true);
  if(newId!==state.selected&&state.areas[newId])return notify('ID area sudah digunakan',true);
  const area=state.areas[state.selected];
  area.name=$('areaName').value.trim()||newId.toUpperCase();area.type=$('areaType').value;area.audio=$('areaSfx').value||null;
  if(newId!==state.selected){delete state.areas[state.selected];state.areas[newId]=area;state.selected=newId}
  renderAreaOptions(state.selected);notify('Data area diperbarui. Klik Simpan semua mapping untuk menerapkan.')
});

$('deleteArea').addEventListener('click',()=>{
  if(!state.selected||!confirm(`Hapus area ${state.selected}?`))return;
  delete state.areas[state.selected];state.selected=null;state.drawing=false;renderAreaOptions();updateMappingMode()
});

$('drawArea').addEventListener('click',()=>{
  if(!state.selected)return notify('Pilih atau tambah area terlebih dahulu',true);
  if(state.areas[state.selected].polygon?.length&&!confirm('Hapus titik lama dan gambar ulang?'))return;
  state.areas[state.selected].polygon=[];state.drawing=true;updateMappingMode();drawMapping()
});

$('resetPreset').addEventListener('click',()=>{
  if(!state.selected||!standardAreas[state.selected])return notify('Reset preset hanya tersedia untuk Taman, Tanaman Kiri/Kanan, dan Jalan',true);
  if(!state.status?.frame_width)return notify('Tunggu resolusi video tersedia',true);
  const preset=standardAreas[state.selected];
  state.areas[state.selected].polygon=preset.points.map(([x,y])=>[Math.round(x*state.status.frame_width),Math.round(y*state.status.frame_height)]);
  state.drawing=false;drawMapping();notify('Posisi preset dikembalikan. Seret titik untuk menyesuaikan, lalu simpan mapping.');
});

$('undoPoint').addEventListener('click',()=>{if(state.selected){state.areas[state.selected].polygon?.pop();drawMapping()}});
$('finishDraw').addEventListener('click',()=>{
  if(!state.selected)return;
  if((state.areas[state.selected].polygon||[]).length<3)return notify('Polygon membutuhkan minimal 3 titik',true);
  state.drawing=false;updateMappingMode();notify('Polygon selesai. Simpan mapping untuk menerapkan.')
});

$('saveMapping').addEventListener('click',async()=>{
  const button=$('saveMapping');setBusy(button,true,'Menyimpan...');
  try{updateAreaFromForm();await api('/api/mapping',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({areas:state.areas})});notify('Mapping tersimpan dan pipeline dimuat ulang');await loadConfiguration()}
  catch(error){notify(error.message,true)}finally{setBusy(button,false)}
});

function updateAreaFromForm(){
  if(!state.selected)return;const area=state.areas[state.selected];
  area.name=$('areaName').value.trim()||state.selected.toUpperCase();area.type=$('areaType').value;area.audio=$('areaSfx').value||null;
}
function defaultColor(type){return type==='garden'?[0,200,70]:type==='plant'?[0,170,255]:[200,200,200]}
function updateMappingMode(){$('mappingMode').textContent=state.drawing?'KLIK TITIK':'PILIH AREA';$('mappingMode').className=`badge ${state.drawing?'ok':'neutral'}`}

const canvas=$('mappingCanvas'),context=canvas.getContext('2d'),rawVideo=$('rawVideo');
function resizeCanvas(){const rect=rawVideo.getBoundingClientRect();if(!rect.width)return;canvas.width=Math.round(rect.width);canvas.height=Math.round(rect.height);drawMapping()}
new ResizeObserver(resizeCanvas).observe($('mappingStage'));rawVideo.addEventListener('load',resizeCanvas);
function sourcePoint(event){
  const rect=canvas.getBoundingClientRect();
  return [Math.round((event.clientX-rect.left)*state.status.frame_width/rect.width),Math.round((event.clientY-rect.top)*state.status.frame_height/rect.height)];
}
function pointInPolygon(point,polygon){
  let inside=false;const [x,y]=point;
  for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
    const [xi,yi]=polygon[i],[xj,yj]=polygon[j];
    if(((yi>y)!==(yj>y))&&(x<(xj-xi)*(y-yi)/(yj-yi)+xi))inside=!inside;
  }
  return inside;
}
canvas.addEventListener('click',event=>{
  if(!state.drawing||!state.selected)return;
  if(!state.status?.frame_width)return notify('Tunggu video dan resolusi sumber tersedia',true);
  state.areas[state.selected].polygon.push(sourcePoint(event));drawMapping();
});
canvas.addEventListener('pointerdown',event=>{
  if(state.drawing||!state.status?.frame_width)return;
  const point=sourcePoint(event),selected=state.areas[state.selected],scale=canvas.width/state.status.frame_width;
  if(selected){
    const index=(selected.polygon||[]).findIndex(vertex=>Math.hypot(vertex[0]-point[0],vertex[1]-point[1])*scale<=14);
    if(index>=0){state.dragIndex=index;canvas.setPointerCapture(event.pointerId);event.preventDefault();return}
  }
  const priority={plant:3,walkway:2,garden:1,ignore:0};
  const match=Object.entries(state.areas).filter(([,area])=>(area.polygon||[]).length>=3&&pointInPolygon(point,area.polygon))
    .sort((a,b)=>(priority[b[1].type]||0)-(priority[a[1].type]||0))[0];
  if(match){state.selected=match[0];renderAreaOptions(match[0]);updateMappingMode()}
});
canvas.addEventListener('pointermove',event=>{
  if(state.dragIndex===null||!state.selected)return;
  const point=sourcePoint(event);
  point[0]=Math.max(0,Math.min(state.status.frame_width,point[0]));point[1]=Math.max(0,Math.min(state.status.frame_height,point[1]));
  state.areas[state.selected].polygon[state.dragIndex]=point;drawMapping();event.preventDefault();
});
function finishDrag(event){if(state.dragIndex!==null){state.dragIndex=null;if(canvas.hasPointerCapture(event.pointerId))canvas.releasePointerCapture(event.pointerId);notify('Titik dipindahkan. Klik Simpan semua mapping untuk menerapkan.')}}
canvas.addEventListener('pointerup',finishDrag);canvas.addEventListener('pointercancel',finishDrag);

function drawMapping(){
  context.clearRect(0,0,canvas.width,canvas.height);
  if(!state.status?.frame_width)return;
  const sx=canvas.width/state.status.frame_width,sy=canvas.height/state.status.frame_height;
  Object.entries(state.areas).forEach(([key,area])=>{
    const points=area.polygon||[];if(!points.length)return;
    const bgr=area.color||[255,255,255],color=`rgb(${bgr[2]},${bgr[1]},${bgr[0]})`;
    context.beginPath();points.forEach((point,index)=>(index?context.lineTo(point[0]*sx,point[1]*sy):context.moveTo(point[0]*sx,point[1]*sy)));
    if(points.length>=3)context.closePath();context.strokeStyle=color;context.lineWidth=key===state.selected?4:2;context.stroke();
    if(points.length>=3){context.fillStyle=color.replace('rgb','rgba').replace(')',',0.16)');context.fill()}
    context.fillStyle=color;context.font='bold 14px system-ui';context.fillText(area.name||key,points[0][0]*sx+7,points[0][1]*sy-7);
    if(key===state.selected)points.forEach((point,index)=>{context.beginPath();context.arc(point[0]*sx,point[1]*sy,5,0,Math.PI*2);context.fill();context.fillText(String(index+1),point[0]*sx+7,point[1]*sy+5)});
  });
}

$('sfxUpload').addEventListener('submit',async event=>{
  event.preventDefault();const button=event.submitter;setBusy(button,true,'Mengupload...');
  const form=new FormData();form.append('name',$('sfxName').value.trim());form.append('volume',$('sfxVolume').value);form.append('loop',$('sfxLoop').checked);form.append('file',$('sfxFile').files[0]);
  try{await api('/api/sfx/upload',{method:'POST',body:form});notify('SFX tersimpan dan siap dipilih pada area tanaman');$('sfxUpload').reset();await loadConfiguration();await refreshStatus()}
  catch(error){notify(error.message,true)}finally{setBusy(button,false)}
});

async function playSfx(name){try{await api(`/api/sfx/${encodeURIComponent(name)}/play`,{method:'POST'})}catch(error){notify(error.message,true)}}
async function stopSfx(name){try{await api(`/api/sfx/${encodeURIComponent(name)}/stop`,{method:'POST'})}catch(error){notify(error.message,true)}}
async function removeSfx(name){if(!confirm(`Hapus konfigurasi SFX ${name}? File audio tidak akan dihapus.`))return;try{await api(`/api/sfx/${encodeURIComponent(name)}`,{method:'DELETE'});notify('Konfigurasi SFX dihapus');await loadConfiguration();await refreshStatus()}catch(error){notify(error.message,true)}}
window.playSfx=playSfx;window.stopSfx=stopSfx;window.removeSfx=removeSfx;

(async()=>{try{await loadConfiguration();await refreshStatus();setInterval(refreshStatus,1000)}catch(error){notify(error.message,true)}})();
