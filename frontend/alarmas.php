<?php
$alarmas = [
["hora"=>"12:49:21","tipo"=>1,"estado"=>"ACTIVA","olt"=>"ZAC-STA.AEROPUERTO-M1TAMARAT-OLT1","puerto"=>"1/1/3","descripcion"=>"OLT sin respuesta (Node Down)","sitio"=>"Aeropuerto Sta. Marta","valor"=>"--"],
["hora"=>"12:31:10","tipo"=>2,"estado"=>"ACTIVA","olt"=>"ZAC-PER-CENTRO-CP1","puerto"=>"1/0/3","descripcion"=>"Alta tasa de errores de entrada","sitio"=>"Centro","valor"=>"15.8 %"],
["hora"=>"12:15:43","tipo"=>3,"estado"=>"ACTIVA","olt"=>"ZAC-BAR-SENA-OLT","puerto"=>"1/1/5","descripcion"=>"Temperatura de tarjeta alta","sitio"=>"Barrio SENA","valor"=>"70 °C"],
["hora"=>"12:08:02","tipo"=>1,"estado"=>"ACTIVA","olt"=>"ZAC-TOL-CUAU-48-2C-000","puerto"=>"1/2/3","descripcion"=>"Puerto caído (Link Down)","sitio"=>"Tolú","valor"=>"--"],
["hora"=>"11:58:39","tipo"=>2,"estado"=>"ACTIVA","olt"=>"ZAC-CUN-SJSECA-B1-C600","puerto"=>"1/1/11","descripcion"=>"Alto uso de ancho de banda","sitio"=>"Suesca","valor"=>"254 Mb/s"],
["hora"=>"11:43:17","tipo"=>3,"estado"=>"ACTIVA","olt"=>"ZAC-COL-ESTACION-M1-C600","puerto"=>"1/0/1","descripcion"=>"Incremento de errores CRC","sitio"=>"Estación","valor"=>"217 Mb/s"],
["hora"=>"10:52:33","tipo"=>1,"estado"=>"ACTIVA","olt"=>"ZAC-BOG-PRADO-DCM-M2-C600","puerto"=>"1/0/3","descripcion"=>"ONT fuera de línea","sitio"=>"Prado","valor"=>"--"],
["hora"=>"10:21:11","tipo"=>1,"estado"=>"ACTIVA","olt"=>"ZAC-CUN-PAR-LB-1-C500","puerto"=>"0/2/0","descripcion"=>"Nodo no disponible","sitio"=>"Pachuca","valor"=>"--"],
["hora"=>"10:11:54","tipo"=>3,"estado"=>"ACTIVA","olt"=>"ZAC-ANT-YARUMAL-B1-C600","puerto"=>"1/1/1","descripcion"=>"Temperatura de tarjeta alta","sitio"=>"Yarumal","valor"=>"49 °C"],
["hora"=>"09:48:27","tipo"=>2,"estado"=>"ACTIVA","olt"=>"ZAC-SAN-BELLO-B2-M3A200","puerto"=>"1/0/2","descripcion"=>"Pérdida de potencia óptica RX","sitio"=>"Bello","valor"=>"-3.2 dBm"]
];
$conteo=[1=>0,2=>0,3=>0]; foreach($alarmas as $a){$conteo[$a["tipo"]]++;} $total=count($alarmas);
?>
<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOC BOA</title>
<style>
:root{--bg:#000;--sidebar:#030303;--panel:#07090d;--panel2:#0a0d12;--line:#1c2834;--text:#f3f6fa;--muted:#98a6b3;--blue:#1499ff;--green:#15d97a;--yellow:#ffd028;--orange:#ff7a18;--red:#ff3048}
*{box-sizing:border-box}html,body{margin:0;background:var(--bg);color:var(--text);font-family:Segoe UI,Arial,sans-serif}body{min-height:100vh}
.app{display:grid;grid-template-columns:220px 1fr;min-height:100vh}.sidebar{position:fixed;inset:0 auto 0 0;width:220px;background:#020202;border-right:1px solid #151a20;padding:18px 12px}
.brand{display:flex;gap:10px;align-items:center;margin:0 8px 25px}.brand .ico{font-size:29px}.brand h2{margin:0;font-size:20px}.brand small{color:var(--muted)}
.nav a{display:flex;gap:11px;align-items:center;color:#dce6ef;text-decoration:none;padding:12px 14px;border-radius:7px;margin:5px 0}.nav a:hover,.nav a.active{background:#0a4c8d}.badge{margin-left:auto;background:var(--red);padding:2px 8px;border-radius:999px;font-weight:700;font-size:12px}
.user{position:absolute;bottom:18px;left:18px;color:#aab5bf;font-size:13px}.main{grid-column:2;padding:18px}.topbar{display:flex;justify-content:space-between;gap:20px;margin-bottom:18px}.title h1{margin:0;font-size:28px}.title p{margin:4px 0;color:#aeb9c5}.topstatus{display:flex;gap:12px}.statusbox{background:#05070a;border:1px solid #202c39;border-radius:8px;padding:10px 14px;text-align:center;min-width:145px}.live{color:#25df88}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--green);margin-right:6px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.card{background:linear-gradient(180deg,#080b0f,#040506);border:1px solid #1c2935;border-radius:10px;padding:16px;box-shadow:0 10px 20px rgba(0,0,0,.35)}.card h3{margin:0 0 12px;font-size:14px;color:#cbd6e0}.kpi{font-size:31px;font-weight:800}.subs{display:flex;gap:14px;flex-wrap:wrap;margin-top:12px;font-size:12px}
.alarm-card{border-color:#4f0c16}.alarm-card.alerting{animation:pulse 1s infinite}@keyframes pulse{0%,100%{box-shadow:0 0 0 rgba(255,48,72,0)}50%{box-shadow:0 0 34px rgba(255,48,72,.8);border-color:var(--red)}}
.charts{display:grid;grid-template-columns:1.1fr 1fr 1.2fr 1fr;gap:14px;margin-top:14px}.chart{height:200px}.donutwrap{height:145px;display:flex;align-items:center;gap:20px}.donut{width:130px;height:130px;border-radius:50%;background:conic-gradient(var(--green) 0 92.9%,var(--yellow) 92.9% 96.5%,var(--red) 96.5%);display:grid;place-items:center;position:relative}.donut:after{content:"";width:76px;height:76px;background:#05070a;border-radius:50%;position:absolute}.donuttext{z-index:1;text-align:center;font-size:24px;font-weight:800}.legend div{margin:8px 0;font-size:12px;color:#c6d2dd}
.bars{display:flex;align-items:flex-end;justify-content:space-around;height:130px;padding-top:20px}.bar{width:48px;border-radius:5px 5px 0 0;position:relative}.bar span{position:absolute;top:-22px;width:100%;text-align:center;font-weight:700}.labels{display:flex;justify-content:space-around;color:#9eacb9;font-size:11px}
.line{height:135px;border-left:1px solid #263747;border-bottom:1px solid #263747;background:linear-gradient(#101923 1px,transparent 1px),linear-gradient(90deg,#101923 1px,transparent 1px);background-size:100% 33px,55px 100%;position:relative;overflow:hidden}.line svg{position:absolute;inset:0;width:100%;height:100%}
.toplist .r{display:grid;grid-template-columns:1fr 110px 18px;gap:8px;align-items:center;margin:10px 0;font-size:12px}.track{height:14px;background:#111821}.fill{height:100%}
.tablecard{margin-top:14px;padding:0;overflow:hidden}.tablehead{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:12px 14px;border-bottom:1px solid #1c2935}.tablehead h3{margin:0 10px 0 0}.pill{padding:7px 10px;border:1px solid #314252;border-radius:7px;font-size:12px;background:#070a0e}.pill.red{background:#b3192b;border-color:#ff3048}.search{margin-left:auto;min-width:260px;background:#010101;color:#fff;border:1px solid #2b3a48;border-radius:7px;padding:8px 10px}
.scroll{overflow:auto}table{width:100%;min-width:1050px;border-collapse:collapse}th,td{padding:9px 10px;border-bottom:1px solid #17212a;font-size:12px;text-align:left}th{background:#030405;color:#9fafbc}tr.critical{background:rgba(255,48,72,.08)}.type{display:inline-block;padding:4px 8px;border-radius:4px;font-weight:800}.t1{background:#d71d35}.t2{background:#f06b10}.t3{background:#d6ae00;color:#111}.state{background:#d71d35;padding:4px 8px;border-radius:4px;font-weight:800}.d1{color:#ff4659}.d2{color:#ffad32}.d3{color:#ffda3d}.btn{background:#08111a;color:#dbe6ef;border:1px solid #2d4255;border-radius:5px;padding:5px 8px;cursor:pointer}
.toast{position:fixed;left:240px;bottom:22px;min-width:430px;background:#150407;border:1px solid var(--red);border-radius:12px;padding:14px 18px;display:flex;align-items:center;gap:14px;box-shadow:0 0 28px rgba(255,48,72,.6);z-index:99}.toast.alerting{animation:tp 1s infinite}@keyframes tp{0%,100%{transform:scale(1)}50%{transform:scale(1.015);box-shadow:0 0 44px rgba(255,48,72,.9)}}.bell{font-size:30px}.footer{display:flex;justify-content:space-between;color:#77838e;font-size:11px;margin-top:14px}
@media(max-width:1200px){.kpis,.charts{grid-template-columns:repeat(2,1fr)}}@media(max-width:760px){.app{display:block}.sidebar{position:relative;width:100%;height:auto}.main{padding:14px}.kpis,.charts{grid-template-columns:1fr}.topstatus{display:none}.toast{left:14px;right:14px;min-width:0}.search{margin-left:0;min-width:100%}}
</style>
</head>
<body>
<div class="app">
<aside class="sidebar">
<div class="brand"><div class="ico">📡</div><div><h2>NOC BOA</h2><small>Monitoreo GPON / OLT</small></div></div>
<nav class="nav">
<a href="#" class="active">🏠 <span>Inicio</span></a>
<a href="#">🔔 <span>Alarmas</span><span class="badge"><?=$total?></span></a>
<a href="#">📄 <span>Reportes</span></a>
<a href="#">⚙️ <span>Configuración</span></a>
</nav>
<div class="user">👤 Administrador</div>
</aside>

<main class="main">
<div class="topbar">
<div class="title"><h1>Vista General</h1><p>Estado en tiempo real de la infraestructura GPON</p></div>
<div class="topstatus"><div class="statusbox" id="clock"></div><div class="statusbox"><span class="dot"></span><span class="live">Tiempo real</span><br><small>Última actualización: hace 10 segundos</small></div><div class="statusbox">🗓 Últimas 24 horas</div></div>
</div>

<section class="kpis">
<div class="card"><h3>🗄 Total OLT</h3><div class="kpi">28</div><div class="subs"><span style="color:var(--green)">● 26 Activas</span><span style="color:var(--yellow)">● 1 Advertencia</span><span style="color:var(--red)">● 1 Caída</span></div></div>
<div class="card"><h3>🧩 Total Puertos</h3><div class="kpi">448</div><div class="subs"><span style="color:var(--green)">● 436 Activos</span><span style="color:var(--yellow)">● 10 Con alerta</span><span style="color:var(--red)">● 2 Caídos</span></div></div>
<div class="card"><h3>👥 Clientes ONT</h3><div class="kpi">8,325</div><div class="subs"><span style="color:var(--green)">● 8,312 Online</span><span style="color:var(--yellow)">● 198 Con alerta</span><span style="color:var(--red)">● 15 Offline</span></div></div>
<div class="card alarm-card alerting" id="alarmCard"><h3>🔔 Alarmas Activas</h3><div class="kpi"><?=$total?></div><div class="subs"><span style="color:var(--red)">● <?=$conteo[1]?> Críticas</span><span style="color:var(--orange)">● <?=$conteo[2]?> Mayores</span><span style="color:var(--yellow)">● <?=$conteo[3]?> Menores</span></div></div>
</section>

<section class="charts">
<div class="card chart"><h3>Estado de OLT</h3><div class="donutwrap"><div class="donut"><div class="donuttext">28<div style="font-size:11px;font-weight:400">OLT</div></div></div><div class="legend"><div><span style="color:var(--green)">●</span> Operativa 26 (92.9%)</div><div><span style="color:var(--yellow)">●</span> Advertencia 1 (3.6%)</div><div><span style="color:var(--red)">●</span> Caída 1 (3.6%)</div></div></div></div>
<div class="card chart"><h3>Alarmas por severidad</h3><div class="bars"><div class="bar" style="height:60px;background:var(--red)"><span><?=$conteo[1]?></span></div><div class="bar" style="height:90px;background:var(--orange)"><span><?=$conteo[2]?></span></div><div class="bar" style="height:75px;background:var(--yellow)"><span><?=$conteo[3]?></span></div></div><div class="labels"><span>Tipo 1</span><span>Tipo 2</span><span>Tipo 3</span></div></div>
<div class="card chart"><h3>Tendencia de alarmas (24h)</h3><div class="line"><svg viewBox="0 0 600 130" preserveAspectRatio="none"><polyline fill="none" stroke="#ff3048" stroke-width="3" points="0,90 35,80 70,55 100,70 130,60 165,75 200,85 230,65 265,55 300,25 335,60 370,40 405,72 445,65 475,78 510,63 545,48 600,82"/><polyline fill="none" stroke="#ffc928" stroke-width="3" points="0,110 40,108 80,95 120,105 155,98 190,107 225,93 260,102 300,75 335,95 365,83 400,103 430,90 470,100 505,86 545,96 600,92"/></svg></div></div>
<div class="card chart toplist"><h3>Top OLT con más alarmas</h3>
<?php $top=[["ZAC-TOL-CUAU-48-2C-000",6],["ZAC-STA-AEROPUERTO-M1",4],["ZAC-CUN-PAR-LB-1A-C500",3],["ZAC-BAR-SENA-OLT",2],["ZAC-ANT-YARUMAL-B1",2]]; foreach($top as $i=>$x){$c=$i===0?'var(--red)':($i===1?'var(--orange)':'var(--yellow)');$w=min(100,$x[1]*16); ?>
<div class="r"><div><?=$x[0]?></div><div class="track"><div class="fill" style="width:<?=$w?>%;background:<?=$c?>"></div></div><div><?=$x[1]?></div></div><?php } ?>
</div>
</section>

<section class="card tablecard">
<div class="tablehead"><h3>🔔 Alarmas en tiempo real</h3><div class="pill red">Todas <?=$total?></div><div class="pill">🔴 Tipo 1 - Críticas <?=$conteo[1]?></div><div class="pill">🟠 Tipo 2 - Mayores <?=$conteo[2]?></div><div class="pill">🟡 Tipo 3 - Menores <?=$conteo[3]?></div><input id="busqueda" class="search" placeholder="Buscar por OLT, nodo, descripción..."></div>
<div class="scroll"><table id="tabla"><thead><tr><th>#</th><th>Hora</th><th>Tipo</th><th>Estado</th><th>OLT</th><th>Puerto</th><th>Descripción</th><th>Nodo / Sitio</th><th>Valor</th><th>Acciones</th></tr></thead><tbody>
<?php foreach($alarmas as $i=>$a){ ?><tr class="<?=$a["tipo"]===1?'critical':''?>"><td><?=$i+1?></td><td><?=$a["hora"]?></td><td><span class="type t<?=$a["tipo"]?>">Tipo <?=$a["tipo"]?></span></td><td><span class="state"><?=$a["estado"]?></span></td><td><?=htmlspecialchars($a["olt"])?></td><td><?=$a["puerto"]?></td><td class="d<?=$a["tipo"]?>"><?=htmlspecialchars($a["descripcion"])?></td><td><?=htmlspecialchars($a["sitio"])?></td><td><?=$a["valor"]?></td><td><button class="btn detalle">Ver detalle ↗</button></td></tr><?php } ?>
</tbody></table></div>
</section>
<div class="footer"><span>NOC BOA | Monitoreo y Gestión GPON</span><span><span style="color:var(--green)">● Operativa</span> &nbsp; <span style="color:var(--yellow)">● Advertencia</span> &nbsp; <span style="color:var(--red)">● Crítica</span> &nbsp; v1.0.0</span></div>
</main></div>

<div class="toast alerting" id="toast"><div class="bell">🔔</div><div style="flex:1"><strong>Alarma activa: titilando hasta interactuar</strong><br><small>Se detiene al hacer clic, mover el mouse, presionar una tecla o tocar la página.</small></div><button class="btn" id="cerrar">✕</button></div>

<script>
const alarmCard=document.getElementById('alarmCard'),toast=document.getElementById('toast'); let ack=false;
function reconocer(){if(ack)return;ack=true;alarmCard.classList.remove('alerting');toast.classList.remove('alerting');}
['click','keydown','touchstart','mousemove'].forEach(e=>window.addEventListener(e,reconocer,{once:true,passive:true}));
document.getElementById('cerrar').onclick=()=>{reconocer();toast.style.display='none'};
document.getElementById('busqueda').addEventListener('input',function(){const q=this.value.toLowerCase();document.querySelectorAll('#tabla tbody tr').forEach(r=>r.style.display=r.innerText.toLowerCase().includes(q)?'':'none')});
document.querySelectorAll('.detalle').forEach(b=>b.onclick=()=>alert('Demo: aquí puedes abrir el detalle completo de la alarma.'));
function clock(){const d=new Date();document.getElementById('clock').innerHTML='🕒 '+d.toLocaleDateString('es-CO')+'<br><strong>'+d.toLocaleTimeString('es-CO')+'</strong>'}clock();setInterval(clock,1000);
alarmCard.addEventListener('dblclick',()=>{ack=false;alarmCard.classList.add('alerting');toast.style.display='flex';toast.classList.add('alerting')});
</script>
</body></html>