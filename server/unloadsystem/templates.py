"""Template-uri HTML (login, change-password, consola, view). Functionale.
Polish-ul de UI e o faza separata (Faza 11)."""

_CSS = """
:root{--bg:#0e1218;--panel:#141b24;--panel2:#1a2430;--bd:#2a3542;--fg:#e9eef5;--mut:#8b98a9;
--blue:#4f8cff;--green:#33d17a;--red:#ef4b4b;--yellow:#f6c62e}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font-family:system-ui,Segoe UI,sans-serif;font-size:14px}
a{color:var(--blue)} button{font:inherit;cursor:pointer}
.btn{padding:9px 15px;border-radius:8px;border:0;font-weight:600}
.btn.p{background:var(--blue);color:#fff}.btn.g{background:#2a3542;color:var(--fg)}.btn.d{background:var(--red);color:#fff}
input,select{padding:10px;border-radius:8px;border:1px solid var(--bd);background:#0c1017;color:var(--fg);width:100%}
.err{color:var(--red);font-size:.85rem;margin-top:10px}
"""

LOGIN_HTML = """<!doctype html><html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>UnloadSystems Remote</title>
<style>""" + _CSS + """
body{height:100vh;display:flex;align-items:center;justify-content:center}
.box{background:var(--panel);border:1px solid var(--bd);border-radius:16px;padding:30px;width:330px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:1.3rem}
.mark{width:28px;height:28px;border-radius:8px;background:linear-gradient(145deg,var(--blue),var(--red))}
.sub{color:var(--mut);font-size:.85rem;margin:6px 0 18px} label{display:block;font-size:.8rem;color:var(--mut);margin:12px 0 6px}
button[type=submit]{width:100%;margin-top:18px;padding:12px;border:0;border-radius:9px;background:var(--blue);color:#fff;font-weight:600}
</style></head><body>
<form class="box" method="post" action="/login">
 <div class="brand"><span class="mark"></span>UnloadSystems Remote</div>
 <p class="sub">Consola de administrare</p>
 <label>Utilizator</label><input name="user" autofocus>
 <label>Parola</label><input name="password" type="password">
 <button type="submit">Autentificare</button>
 <!--ERR-->
</form></body></html>"""

CHANGEPW_HTML = """<!doctype html><html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Schimba parola</title>
<style>""" + _CSS + """
body{height:100vh;display:flex;align-items:center;justify-content:center}
.box{background:var(--panel);border:1px solid var(--bd);border-radius:16px;padding:30px;width:330px}
h2{margin:0 0 4px} .sub{color:var(--mut);font-size:.85rem;margin:0 0 14px} label{display:block;font-size:.8rem;color:var(--mut);margin:12px 0 6px}
</style></head><body>
<div class="box">
 <h2>Schimba parola</h2><p class="sub">Trebuie sa-ti setezi o parola noua.</p>
 <label>Parola actuala</label><input id="old" type="password">
 <label>Parola noua (min 6)</label><input id="new" type="password">
 <button class="btn p" style="width:100%;margin-top:16px" onclick="go()">Salveaza</button>
 <div class="err" id="msg"></div>
</div>
<script>
function go(){fetch('/change-password',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({old:document.getElementById('old').value,new:document.getElementById('new').value})})
 .then(r=>r.json()).then(x=>{if(x.ok){location.href='/';}else{document.getElementById('msg').textContent=x.error||'Eroare';}});}
</script></body></html>"""

CONSOLE_HTML = """<!doctype html><html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>UnloadSystems Remote</title>
<style>""" + _CSS + """
body{height:100vh;display:flex;flex-direction:column}
.top{display:flex;align-items:center;gap:14px;padding:12px 18px;border-bottom:1px solid var(--bd)}
.brand{display:flex;align-items:center;gap:9px;font-weight:700}
.mark{width:22px;height:22px;border-radius:6px;background:linear-gradient(145deg,var(--blue),var(--red))}
.tabs{display:flex;gap:4px;margin-left:12px}
.tab{padding:7px 13px;border-radius:8px;color:var(--mut);background:none;border:0}
.tab.active{background:var(--panel2);color:var(--fg)}
.who{margin-left:auto;color:var(--mut);font-size:.85rem}
.wrap{flex:1;overflow:auto;padding:18px}
.cards{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:12px;padding:14px 18px;min-width:120px}
.card .n{font-size:1.6rem;font-weight:700} .card .l{color:var(--mut);font-size:.8rem}
.row{display:flex;align-items:center;gap:14px;padding:12px 14px;border:1px solid var(--bd);border-radius:12px;margin-bottom:8px;background:var(--panel)}
.dot{width:10px;height:10px;border-radius:50%}.dot.on{background:var(--green);box-shadow:0 0 8px var(--green)}.dot.off{background:#44505f}
.nm{font-weight:600}.co{color:var(--mut);font-size:.8rem}
.badge{font-size:.68rem;color:var(--mut);border:1px solid var(--bd);border-radius:20px;padding:1px 7px;margin-left:4px}
.st{margin-left:auto;color:var(--mut);font-size:.8rem}
.iconbtn{background:#0c1017;border:1px solid var(--bd);color:var(--mut);border-radius:8px;padding:9px 11px}
table{width:100%;border-collapse:collapse}td,th{padding:8px 10px;border-bottom:1px solid var(--bd);text-align:left;font-size:.85rem}
.hidden{display:none}
</style></head><body>
<div class="top">
 <div class="brand"><span class="mark"></span>UnloadSystems Remote</div>
 <div class="tabs" id="tabs"></div>
 <div class="who">__USER__ · __ROLE__ · <a href="/logout">iesire</a></div>
</div>
<div class="wrap">
 <div id="v_machines">
   <div class="cards" id="stats"></div>
   <input id="search" placeholder="Cauta masina..." style="max-width:280px;margin-bottom:12px">
   <div id="list"></div>
 </div>
 <div id="v_users" class="hidden"></div>
 <div id="v_audit" class="hidden"></div>
</div>
<script>
var ROLE="__ROLE__", ME="__USER__", AG=[], Q="";
var RANK={read_only:10,technician:40,admin:70,super_admin:100}[ROLE]||0;
function esc(s){return(s||'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
// tabs by role
var TABS=[['machines','Masini']];
if(RANK>=70){TABS.push(['users','Utilizatori']);TABS.push(['audit','Audit']);}
var tb=document.getElementById('tabs');
TABS.forEach((t,i)=>{var b=document.createElement('button');b.className='tab'+(i==0?' active':'');b.textContent=t[1];
 b.onclick=function(){document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');show(t[0]);};tb.appendChild(b);});
function show(v){['machines','users','audit'].forEach(x=>document.getElementById('v_'+x).classList.add('hidden'));
 document.getElementById('v_'+v).classList.remove('hidden');
 if(v=='users')loadUsers(); if(v=='audit')loadAudit();}
// machines
function loadM(){fetch('/api/machines').then(r=>r.json()).then(d=>{AG=d.machines||[];renderM();}).catch(()=>{});}
function renderM(){
 var on=AG.filter(a=>a.online).length;
 document.getElementById('stats').innerHTML=
  '<div class="card"><div class="n" style="color:var(--green)">'+on+'</div><div class="l">Online</div></div>'+
  '<div class="card"><div class="n">'+(AG.length-on)+'</div><div class="l">Offline</div></div>'+
  '<div class="card"><div class="n">'+AG.length+'</div><div class="l">Total</div></div>';
 var list=AG.filter(a=>a.name.toLowerCase().indexOf(Q)>=0||a.company.toLowerCase().indexOf(Q)>=0);
 var L=document.getElementById('list');L.innerHTML='';
 if(!list.length){L.innerHTML='<div style="color:var(--mut);padding:30px;text-align:center">Nicio masina.</div>';return;}
 list.forEach(a=>{var r=document.createElement('div');r.className='row';
  var caps=a.capabilities||{};
  var pill=' <span class="badge">'+esc(a.platform)+'</span>';
  r.innerHTML='<span class="dot '+(a.online?'on':'off')+'"></span><div><div class="nm">'+esc(a.name)+pill+'</div><div class="co">'+esc(a.company)+'</div></div><span class="st">'+(a.online?'Online':'Offline')+'</span>';
  if(caps.remote_desktop){var go=document.createElement('button');go.className='btn p';go.textContent='Conecteaza';go.disabled=!a.online;
   go.onclick=function(){window.open('/view/'+a.device_id,'_blank');};r.appendChild(go);}
  if(RANK>=70){var ed=document.createElement('button');ed.className='iconbtn';ed.textContent='\\u270e';
   ed.onclick=function(){editM(a);};r.appendChild(ed);}
  L.appendChild(r);});
}
function editM(a){var name=prompt('Nume masina:',a.name);if(name===null)return;var co=prompt('Companie:',a.company==='Fara grup'?'':a.company);if(co===null)return;
 fetch('/api/machines/rename',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:a.device_id,name:name,company:co})}).then(()=>loadM());}
document.getElementById('search').addEventListener('input',function(e){Q=e.target.value.toLowerCase();renderM();});
// users
function loadUsers(){fetch('/api/users').then(r=>r.json()).then(d=>{if(d.error){return;}
 var h='<button class="btn p" onclick="addUser()">+ Utilizator</button><table style="margin-top:12px"><tr><th>Utilizator</th><th>Rol</th><th>Activ</th><th></th></tr>';
 (d.users||[]).forEach(u=>{h+='<tr><td>'+esc(u.username)+(u.username==ME?' (tu)':'')+'</td><td>'+esc(u.role_name)+'</td><td>'+(u.active?'da':'nu')+'</td><td>';
  h+='<button class="iconbtn" onclick="pwUser(\\''+esc(u.username)+'\\')">parola</button> ';
  if(u.username!=ME)h+='<button class="iconbtn" onclick="delUser(\\''+esc(u.username)+'\\')">sterge</button>';
  h+='</td></tr>';});
 h+='</table>';document.getElementById('v_users').innerHTML=h;});}
function addUser(){var u=prompt('Utilizator nou:');if(!u)return;var p=prompt('Parola (min 6):');if(!p)return;var role=prompt('Rol (read_only/technician/admin):','technician');
 fetch('/api/users/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:u,password:p,role:role})}).then(r=>r.json()).then(x=>{if(x.error)alert(x.error);loadUsers();});}
function delUser(u){if(!confirm('Stergi '+u+'?'))return;fetch('/api/users/del',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:u})}).then(r=>r.json()).then(x=>{if(x.error)alert(x.error);loadUsers();});}
function pwUser(u){var p=prompt('Parola noua pentru '+u+' (min 6):');if(!p)return;fetch('/api/users/passwd',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user:u,password:p})}).then(r=>r.json()).then(x=>{alert(x.error||'Parola schimbata');});}
// audit
function loadAudit(){fetch('/api/audit').then(r=>r.json()).then(d=>{if(d.error)return;
 var h='<table><tr><th>Cand</th><th>User</th><th>Actiune</th><th>Tinta</th></tr>';
 (d.logs||[]).forEach(l=>{h+='<tr><td>'+new Date(l.ts*1000).toLocaleString()+'</td><td>'+esc(l.username||'-')+'</td><td>'+esc(l.action)+'</td><td>'+esc(l.target||'')+'</td></tr>';});
 h+='</table>';document.getElementById('v_audit').innerHTML=h;});}
loadM();setInterval(loadM,4000);
</script></body></html>"""

VIEW_HTML = """<!doctype html><html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__NAME__ - UnloadSystems</title>
<style>""" + _CSS + """
html,body{height:100%;background:#000;overflow:hidden}
#bar{height:40px;background:var(--panel);display:flex;align-items:center;gap:12px;padding:0 12px;border-bottom:1px solid var(--bd);color:var(--fg)}
#bar .dot{width:9px;height:9px;border-radius:50%;background:var(--green)}
#bar select,#bar button{width:auto;padding:6px 10px}
#bar .sp{margin-left:auto}
#wrap{height:calc(100% - 40px);display:flex}
#screenbox{flex:1;display:flex;align-items:center;justify-content:center;overflow:hidden}
#screen{max-width:100%;max-height:100%;cursor:crosshair}
#files{width:300px;background:#0e1218;border-left:1px solid var(--bd);display:none;flex-direction:column;color:var(--fg)}
#files.show{display:flex} #files h4{margin:0;padding:12px;border-bottom:1px solid var(--bd);font-size:.95rem}
#drop{margin:12px;padding:16px;border:1px dashed var(--bd);border-radius:10px;text-align:center;color:var(--mut)}
#fl{flex:1;overflow:auto;padding:0 8px} .fe{display:flex;gap:8px;padding:7px 8px;border-radius:7px;cursor:pointer}.fe:hover{background:var(--panel2)}
#log{padding:8px 12px;border-top:1px solid var(--bd);max-height:120px;overflow:auto;font-size:.78rem;color:var(--mut)}
</style></head><body>
<div id="bar"><span class="dot"></span><b>__NAME__</b><span id="stat" style="color:var(--mut)">conectare...</span>
 <span class="sp"></span>
 <span id="monwrap" style="display:none">Monitor <select id="mon"></select></span>
 <button id="fbtn" class="btn g" style="display:none" onclick="toggleFiles()">Fisiere</button>
</div>
<div id="wrap">
 <div id="screenbox"><img id="screen" draggable="false"></div>
 <div id="files"><h4>Transfer fisiere</h4>
  <div id="drop">Trage fisiere aici (trimite pe Desktop)</div><input id="finput" type="file" multiple style="display:none">
  <div id="fl"></div><div id="log"></div></div>
</div>
<script>
var DID="__DID__", CAPS=__CAPS__, IMG=document.getElementById('screen'), last=0, dl={};
var ws=new WebSocket((location.protocol==='https:'?'wss':'ws')+'://'+location.host+'/view-ws/'+DID);
ws.binaryType='blob';
function S(ch,t,o){o=o||{};o.ch=ch;o.t=t;if(ws.readyState===1)ws.send(JSON.stringify(o));}
ws.onopen=function(){document.getElementById('stat').textContent='conectat';bind();
 if(CAPS.multi_monitor){S('system','monitors-req');}
 if(CAPS.file_transfer){document.getElementById('fbtn').style.display='';}};
ws.onclose=function(){document.getElementById('stat').textContent='deconectat';};
ws.onmessage=function(ev){ if(ev.data instanceof Blob){var u=URL.createObjectURL(ev.data);IMG.onload=function(){URL.revokeObjectURL(u);};IMG.src=u;return;}
 var m;try{m=JSON.parse(ev.data);}catch(e){return;}
 if(m.ch==='system'&&m.t==='monitors'){setMon(m.list||[]);}
 else if(m.ch==='files'){ if(m.t==='ls-res')showLs(m.path,m.entries||[]); else if(m.t==='up-ok')logL('Trimis: '+m.name);
  else if(m.t==='dl-begin'){dl[m.name]={parts:[]};logL('Descarc: '+m.name);} else if(m.t==='dl-chunk'){if(dl[m.name])dl[m.name].parts.push(m.data);}
  else if(m.t==='dl-end')finishDl(m.name); else if(m.t==='err')logL('Eroare: '+m.msg);}
};
function setMon(list){if(!list.length)return;var w=document.getElementById('monwrap'),s=document.getElementById('mon');
 s.innerHTML='';list.forEach(function(x){var o=document.createElement('option');o.value=x.i;o.textContent='Monitor '+x.i+' ('+x.w+'x'+x.h+')';s.appendChild(o);});w.style.display='';}
document.getElementById('mon').addEventListener('change',function(e){S('system','setmon',{i:parseInt(e.target.value,10)});});
// files
var CUR='';
function toggleFiles(){var f=document.getElementById('files');f.classList.toggle('show');if(f.classList.contains('show'))S('files','ls',{path:CUR});}
document.getElementById('drop').onclick=function(){document.getElementById('finput').click();};
document.getElementById('finput').onchange=function(e){[].forEach.call(e.target.files,up);e.target.value='';};
var dz=document.getElementById('drop');dz.ondragover=function(e){e.preventDefault();};dz.ondrop=function(e){e.preventDefault();[].forEach.call(e.dataTransfer.files,up);};
function up(file){var rd=new FileReader();var fid=Math.random().toString(36).slice(2);
 rd.onload=function(){var b=rd.result.split(',')[1]||'';S('files','up-begin',{fid:fid,name:file.name});
  for(var i=0;i<b.length;i+=60000)S('files','up-chunk',{fid:fid,data:b.slice(i,i+60000)});S('files','up-end',{fid:fid});logL('Trimit: '+file.name);};
 rd.readAsDataURL(file);}
function showLs(p,es){CUR=p;var fl=document.getElementById('fl');fl.innerHTML='';
 if(p){var u=document.createElement('div');u.className='fe';u.textContent='\\u21a9 ..';u.onclick=function(){S('files','ls',{path:parent(p)});};fl.appendChild(u);}
 es.forEach(function(e){var d=document.createElement('div');d.className='fe';d.textContent=(e.dir?'\\u{1F4C1} ':'\\u{1F4C4} ')+e.name;
  d.onclick=function(){if(e.dir)S('files','ls',{path:e.path});else S('files','dl',{path:e.path});};fl.appendChild(d);});}
function parent(p){var i=Math.max(p.lastIndexOf('/'),p.lastIndexOf('\\\\'));return i>0?p.slice(0,i):'';}
function finishDl(n){var d=dl[n];if(!d)return;var bin=atob(d.parts.join(''));var arr=new Uint8Array(bin.length);for(var i=0;i<bin.length;i++)arr[i]=bin.charCodeAt(i);
 var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([arr]));a.download=n;a.click();delete dl[n];logL('Descarcat: '+n);}
function logL(t){var l=document.getElementById('log');var d=document.createElement('div');d.textContent=t;l.appendChild(d);l.scrollTop=l.scrollHeight;}
// input
function norm(e){var r=IMG.getBoundingClientRect();return{x:Math.min(Math.max((e.clientX-r.left)/r.width,0),1),y:Math.min(Math.max((e.clientY-r.top)/r.height,0),1)};}
function mb(b){return b===0?0:(b===2?1:2);}
var SP={'Enter':'Return','Backspace':'BackSpace','Tab':'Tab','Escape':'Escape','Delete':'Delete','ArrowLeft':'Left','ArrowRight':'Right','ArrowUp':'Up','ArrowDown':'Down','Home':'Home','End':'End','PageUp':'Prior','PageDown':'Next','Insert':'Insert',' ':'space','F1':'F1','F2':'F2','F3':'F3','F4':'F4','F5':'F5','F6':'F6','F7':'F7','F8':'F8','F9':'F9','F10':'F10','F11':'F11','F12':'F12'};
function bind(){ if(!CAPS.remote_input)return;
 IMG.addEventListener('mousemove',function(e){var t=Date.now();if(t-last<30)return;last=t;var p=norm(e);S('input','move',p);});
 IMG.addEventListener('mousedown',function(e){e.preventDefault();var p=norm(e);p.b=mb(e.button);S('input','down',p);});
 IMG.addEventListener('mouseup',function(e){e.preventDefault();var p=norm(e);p.b=mb(e.button);S('input','up',p);});
 IMG.addEventListener('contextmenu',function(e){e.preventDefault();});
 IMG.addEventListener('wheel',function(e){e.preventDefault();var p=norm(e);p.dy=(e.deltaY>0?-1:1);S('input','scroll',p);},{passive:false});
 window.addEventListener('keydown',function(e){var k=e.key;if(k==='Shift'||k==='Control'||k==='Alt'||k==='Meta')return;e.preventDefault();
  if(e.ctrlKey||e.altKey||e.metaKey){var m=[];if(e.ctrlKey)m.push('ctrl');if(e.altKey)m.push('alt');if(e.shiftKey)m.push('shift');var base=SP[k]||(k.length===1?k.toLowerCase():k);S('input','key',{mode:'combo',v:m.concat([base]).join('+')});}
  else if(SP[k])S('input','key',{mode:'special',v:SP[k]});
  else if(k.length===1)S('input','key',{mode:'char',v:k});});
}
</script></body></html>"""
