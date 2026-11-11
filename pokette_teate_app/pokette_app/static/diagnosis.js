const qs=[...document.querySelectorAll('.question')]; let step=0;
const bar=document.getElementById('bar'), next=document.getElementById('next'), prev=document.getElementById('prev');
function render(){qs.forEach((q,i)=>q.classList.toggle('active',i===step));bar.style.width=((step+1)/4*100)+'%';prev.style.visibility=step?'visible':'hidden';next.textContent=step===3?'この内容で診断する':'次の質問';}
function val(name){return document.querySelector(`input[name="${name}"]:checked`)?.value}
function valid(){
 document.getElementById('error').textContent='';
 if(step===0&&!document.getElementById('prefecture').value) return '都道府県を選択してください。';
 if(step===1&&!val('children')) return '子どもの人数を選択してください。';
 if(step===2&&!val('income')) return '世帯年収を選択してください。';
 if(step===3&&!val('singleParent')) return 'ひとり親世帯かどうかを選択してください。';
}
next.onclick=async()=>{
 const e=valid(); if(e){document.getElementById('error').textContent=e;return}
 if(step<3){step++;render();return}
 const payload={prefecture:document.getElementById('prefecture').value,children:Number(val('children')),income:Number(val('income')),singleParent:val('singleParent')==='true'};
 const r=await fetch('/api/diagnose',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
 const data=await r.json();sessionStorage.setItem('diagnosis',JSON.stringify(data));location.href='/result';
};
prev.onclick=()=>{if(step>0){step--;render()}}; render();
