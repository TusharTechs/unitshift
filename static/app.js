const $=id=>document.getElementById(id);
let allCases=[],selected=null,current=null,busy=false,settings={};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function money(value,currency='USD'){
  if(value===null||value===undefined)return '—';
  if(!currency)return '—';
  const n=Number(value)/100;
  if(!Number.isFinite(n))return '—';
  try{return new Intl.NumberFormat('en-US',{style:'currency',currency,maximumFractionDigits:2}).format(n)}catch{return n.toFixed(2)}
}
async function api(path,payload){
  const response=await fetch(path,payload===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const result=await response.json();
  if(!response.ok)throw new Error(result.error||'Request failed.');
  return result;
}
function showError(message){$('error').textContent=message;$('error').hidden=false}
function clearError(){$('error').hidden=true}
function showPage(page){
  for(const name of ['review','sources','evidence'])$(name+'-page').hidden=name!==page;
  document.querySelectorAll('.nav').forEach(button=>button.classList.toggle('active',button.dataset.page===page));
  $('breadcrumb').textContent={review:'Invoice review',sources:'Source records',evidence:'Evidence & receipts'}[page];
}
async function loadStatus(){
  settings=await api('/api/status');
  for(const [key,id,label] of [['zetaris','zetaris-status','Zetaris'],['nebius','nebius-status','Nemotron'],['hmem','hmem-status','H-MEM'],['nightshift','nightshift-status','Nightshift']]){
    $(id).textContent=label+' · '+(settings[key]?(key==='hmem'?'installed':'configured'):'setup needed');
    $(id).className=settings[key]?'configured':'missing';
  }
  $('nightshift').disabled=!settings.nightshift||!current;
}
function sourceTables(data){
  if(!data)return;
  $('source-tables').innerHTML=Object.entries(data.sources).map(([name,rows])=>{
    const columns=[...new Set(rows.flatMap(row=>Object.keys(row)))];
    return `<h3>${esc(name.replaceAll('_',' '))}</h3><div class="table-wrap"><table><thead><tr>${columns.map(c=>`<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${columns.map(c=>`<td>${row[c]===null?'<em>missing</em>':esc(row[c])}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }).join('');
  $('po-count').textContent=data.sources.purchase_orders.length+' rows';
  $('invoice-count').textContent=data.sources.invoices.length+' rows';
  $('receiving-count').textContent=data.sources.receiving.length+' rows';
}
function resetResult(){
  current=null;
  for(const id of ['payable','baseline'])$(id).textContent='—';
  $('decision').textContent='Not reviewed';$('decision-detail').textContent='Run a real model review to see a result';
  $('lines').innerHTML='<tr><td colspan="5" class="empty"><span>◫</span>Choose a scenario and run a review.<small>Results come from real Nemotron calls and deterministic checks.</small></td></tr>';
  $('checks').innerHTML='<div class="empty compact">The evidence trail appears after a review.</div>';
  $('line-count').textContent='No run yet';$('run-time').textContent='';$('clarification').hidden=true;
  $('contract').textContent='Run a review to inspect its contract.';$('receipts').textContent='No run selected.';
  $('brief').textContent='';$('approve').disabled=true;$('export').disabled=true;$('nightshift').disabled=true;
  $('operator-note').hidden=true;
  $('memory-note').textContent='Approve a supported mapping to reuse it for this supplier and catalogue revision.';
}
async function chooseCase(){
  clearError();resetResult();
  selected=await api('/api/cases/'+encodeURIComponent($('case-select').value));
  $('case-description').textContent=selected.description;
  $('source-caption').textContent=selected.source_info?.backend==='zetaris'?'Synthetic exports queried through Zetaris · three registered sources in private S3 storage.':'Local synthetic records · this run does not query Zetaris.';
  sourceTables(selected.data);
}
function renderReview(run){
  current=run;const result=run.result;
  $('source-caption').textContent=run.data_source+' · '+(run.source_info?.backend==='zetaris'?'Real query receipts are available under Evidence & receipts.':'No live federation is claimed for this run.');
  $('payable').textContent=money(result.payable_minor,result.currency);
  $('decision').textContent=result.status==='supported'?'Supported':'Needs review';
  const holds=result.lines.filter(line=>line.status==='held').length;
  $('decision-detail').textContent=holds?`${holds} held line${holds===1?'':'s'} · evidence needed`:result.status==='held'?'Contract could not be validated':'Every invoice line passed the checks';
  $('baseline').textContent=money(run.baseline.payable_minor,result.currency);
  $('line-count').textContent=result.lines.length+' line'+(result.lines.length===1?'':'s');
  $('review-subtitle').textContent=run.supplier+' · '+run.revision;
  $('lines').innerHTML=result.lines.length?result.lines.map(line=>`<tr><td>${esc(line.id)}<small>${line.issues.map(esc).join('<br>')}</small></td><td>${esc(line.sku)}<small>${line.normalised_items?esc(line.normalised_items)+' normalised items':''}</small></td><td>${money(line.claimed_minor,line.currency||result.currency)}</td><td>${money(line.supported_minor,line.currency||result.currency)}</td><td><span class="status ${line.status==='supported'?'supported':'held'}">${line.status==='supported'?'✓ Supported':'! Hold'}</span></td></tr>`).join(''):`<tr><td colspan="5" class="empty">${result.issues.map(esc).join('<br>')}</td></tr>`;
  const checks=[...new Set(result.lines.flatMap(line=>line.checks||[]))];
  const issues=[...new Set([...result.issues,...result.lines.flatMap(line=>line.issues||[])])];
  $('checks').innerHTML=checks.map(text=>`<div class="check-item"><span>✓</span>${esc(text)}</div>`).join('')+issues.map(text=>`<div class="check-item issue-item"><span>!</span>${esc(text)}</div>`).join('');
  $('operator-note').hidden=!run.operator_brief;
  if(run.operator_brief)$('operator-note-text').textContent=run.operator_brief.text||('Provider unavailable: '+run.operator_brief.error);
  $('run-time').textContent=run.elapsed_s+'s · '+(run.reused_memory_id?'approved memory':'real Nemotron inference');
  $('contract').textContent=JSON.stringify({method:run.method,source_info:run.source_info,federated_diagnostic:run.federation,inspection:run.plan,contract:run.contract},null,2);
  $('memory-note').textContent=run.reused_memory_id?`Reused ${run.reused_memory_id} for this exact supplier, catalogue revision and schema.`:run.memory.stale_count?`${run.memory.stale_count} older mapping(s) excluded because the source scope changed.`:run.memory.warning||'Approve this supported mapping to reuse it for this supplier and catalogue revision.';
  $('approve').disabled=result.status!=='supported'||run.mode!=='agent'||!settings.hmem;
  $('approve').textContent='Approve mapping for reuse →';
  $('export').disabled=false;$('nightshift').disabled=!settings.nightshift;
  $('clarification').hidden=!run.clarification;
  if(run.clarification)$('clarification-question').textContent=run.clarification.question;
  sourceTables(run.source_data);
  refreshReceipts();
}
async function refreshReceipts(){if(current)$('receipts').textContent=JSON.stringify(await api('/api/receipts/'+current.run_id),null,2)}
async function runReview(packOverride){
  if(busy)return;
  busy=true;clearError();$('run').disabled=true;$('clarify').disabled=true;$('case-select').disabled=true;$('mode-select').disabled=true;$('progress').hidden=false;
  const start=Date.now();$('elapsed').textContent='0s';const timer=setInterval(()=>{$('elapsed').textContent=Math.round((Date.now()-start)/1000)+'s'},1000);
  try{
    const payload={case_id:$('case-select').value,mode:$('mode-select').value};
    if(packOverride!==undefined)payload.pack_override=packOverride;
    const run=await api('/api/review',payload);renderReview(run);
  }catch(error){showError(error.message)}finally{
    busy=false;clearInterval(timer);$('progress').hidden=true;$('run').disabled=false;$('clarify').disabled=false;$('case-select').disabled=false;$('mode-select').disabled=false;
  }
}
document.querySelectorAll('[data-page]').forEach(button=>button.addEventListener('click',()=>showPage(button.dataset.page)));
$('case-select').addEventListener('change',()=>chooseCase().catch(error=>showError(error.message)));
$('run').addEventListener('click',()=>runReview());
$('clarify').addEventListener('click',()=>{
  const value=Number($('pack-size').value);
  if(!Number.isInteger(value)||value<1||value>10000)return showError('Enter a supplier-confirmed integer from 1 to 10000.');
  runReview(value);
});
$('approve').addEventListener('click',async()=>{
  if(!current)return;
  $('approve').disabled=true;
  try{const r=await api('/api/approve',{run_id:current.run_id});$('memory-note').textContent='Approved as '+r.memory_id+'. Reuse is restricted to this supplier, catalogue revision and schema.';$('approve').textContent='✓ Mapping approved';await refreshReceipts()}
  catch(error){$('approve').disabled=false;showError(error.message)}
});
$('nightshift').addEventListener('click',async()=>{
  if(!current)return;
  $('nightshift').disabled=true;$('brief').textContent='Requesting an operator brief from the configured Nightshift provider…';
  try{const r=await api('/api/nightshift-brief',{run_id:current.run_id});$('brief').textContent=r.brief;await refreshReceipts()}
  catch(error){$('brief').textContent=error.message}finally{$('nightshift').disabled=false}
});
$('export').addEventListener('click',async()=>{
  if(!current)return;
  const receipts=await api('/api/receipts/'+current.run_id);
  const file=new Blob([JSON.stringify({...current,receipts},null,2)],{type:'application/json'});
  const url=URL.createObjectURL(file);const link=document.createElement('a');link.href=url;link.download='unitshift-review-'+current.run_id+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
async function init(){
  await loadStatus();allCases=await api('/api/cases');$('case-count').textContent=allCases.length;
  $('case-select').innerHTML=allCases.map(c=>`<option value="${esc(c.id)}">${esc(c.title)}${c.split==='demo'?' · demo':''}</option>`).join('');
  await chooseCase();
}
init().catch(error=>showError(error.message));
