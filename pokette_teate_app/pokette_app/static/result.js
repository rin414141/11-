const data=JSON.parse(sessionStorage.getItem('diagnosis')||'{"count":0,"subsidies":[],"conditions":{}}');
const prefs={"01":"北海道","13":"東京都","23":"愛知県","27":"大阪府","26":"京都府","28":"兵庫県","40":"福岡県"};
const incomes={"1":"300万円未満","2":"300〜500万円","3":"500〜800万円","4":"800万円以上","5":"わからない"};
document.getElementById('count').textContent=data.count;
const c=data.conditions;
document.getElementById('conditionText').textContent=`${prefs[c.prefecture]||c.prefecture}・子ども${c.children}人・年収${incomes[c.income]||''}・ひとり親${c.singleParent?'はい':'いいえ'}`;
let current='all';
function difficulty(d){return d==='easy'?['簡単','easy']:d==='hard'?['難しい','hard']:['普通','normal']}
function daysLeft(deadline){if(!deadline)return null;const d=Math.ceil((new Date(deadline)-new Date())/86400000);return d}
function render(){
 const box=document.getElementById('cards');box.innerHTML='';
 const list=data.subsidies.filter(x=>current==='all'||x.category===current);
 document.getElementById('empty').hidden=list.length>0;
 list.forEach(x=>{
   const [label,cls]=difficulty(x.difficulty), left=daysLeft(x.deadline);
   const deadline=x.deadline?`${x.deadline.replaceAll('-','/')} ${left!==null&&left<=7?`（あと${Math.max(left,0)}日）`:''}`:'随時';
   const el=document.createElement('article');el.className='card';
   el.innerHTML=`<div class="card-top"><span class="tag ${cls}">${label}</span><span class="category">${x.category}</span><button class="star" data-id="${x.id}" aria-label="保存">☆</button></div>
   <h2>${x.name}</h2><p class="amount">${x.amount}</p><p class="deadline">申請期限：${deadline}</p>
   <a class="official" target="_blank" rel="noopener" href="${x.official_url}">公式サイトで申請方法を見る ↗</a>`;
   box.appendChild(el);
 });
 document.querySelectorAll('.star').forEach(b=>b.onclick=()=>{b.textContent=b.textContent==='☆'?'★':'☆';});
}
document.querySelectorAll('#tabs button').forEach(b=>b.onclick=()=>{document.querySelector('#tabs .active').classList.remove('active');b.classList.add('active');current=b.dataset.cat;render()});
render();
