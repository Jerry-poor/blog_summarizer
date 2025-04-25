// 简单本地存储历史
const historyList = document.getElementById('history-list');
const reportArea  = document.getElementById('report');
const messagesDiv = document.getElementById('messages');
const questionIn  = document.getElementById('question');
const sendBtn     = document.getElementById('send');
const imageInput  = document.getElementById('image-input');
const makePoster  = document.getElementById('make-poster');
const posterOut   = document.getElementById('poster-output');

let history = JSON.parse(localStorage.getItem('hf_history')||'[]');
function renderHistory(){
  historyList.innerHTML = '';
  history.forEach(date=>{
    const li = document.createElement('li');
    li.textContent = date;
    li.onclick = ()=> loadReport(date);
    historyList.append(li);
  });
}
function addHistory(date){
  if(!history.includes(date)){
    history.unshift(date);
    if(history.length>20) history.pop();
    localStorage.setItem('hf_history', JSON.stringify(history));
    renderHistory();
  }
}

// 加载日报并展示
async function loadReport(date){
  addHistory(date);
  reportArea.value = 'Loading...';
  const res = await fetch(`/api/report?date=${date}`);
  const md  = await res.text();
  reportArea.value = md;
  messagesDiv.innerHTML = '';
}

// 聊天问答
sendBtn.onclick = async ()=>{
  const q = questionIn.value.trim();
  if(!q) return;
  appendMessage('user', q);
  questionIn.value = '';
  const date = history[0]||new Date().toISOString().slice(0,10);
  const res = await fetch('/api/chat', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({question:q, date})
  });
  const {answer} = await res.json();
  appendMessage('bot', answer);
};
function appendMessage(who, text){
  const div = document.createElement('div');
  div.className = 'message '+who;
  div.textContent = text;
  messagesDiv.append(div);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// 生成海报
makePoster.onclick = async ()=>{
  const file = imageInput.files[0];
  if(!file) return alert('请选择一张图片');
  const date = history[0]||new Date().toISOString().slice(0,10);
  const fd = new FormData();
  fd.append('date', date);
  fd.append('image', file);
  posterOut.innerHTML = 'Generating poster...';
  const res = await fetch('/api/poster', { method:'POST', body: fd });
  const {url} = await res.json();
  posterOut.innerHTML = `<img src="${url}" alt="Poster">`;
};

// 初始化
renderHistory();
// 载入今天
loadReport(new Date().toISOString().slice(0,10));
