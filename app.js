// 后端基准地址
const API_BASE = 'http://localhost:8000';

const historyList = document.getElementById('history-list');
const reportArea  = document.getElementById('report');
const messagesDiv = document.getElementById('messages');
const questionIn  = document.getElementById('question');
const sendBtn     = document.getElementById('send');
const imageInput  = document.getElementById('image-input');
const makePoster  = document.getElementById('make-poster');
const posterOut   = document.getElementById('poster-output');

// 全局跟踪当前查看的日期
let currentDate = new Date().toISOString().slice(0,10);

let history = JSON.parse(localStorage.getItem('hf_history')||'[]');

// 渲染左侧历史列表
function renderHistory(){
  historyList.innerHTML = '';
  history.forEach(date=>{
    const li = document.createElement('li');
    li.textContent = date;
    li.onclick = ()=> loadReport(date);
    historyList.append(li);
  });
}

// 向 localStorage 添加历史
function addHistory(date){
  if(!history.includes(date)){
    history.unshift(date);
    if(history.length>20) history.pop();
    localStorage.setItem('hf_history', JSON.stringify(history));
    renderHistory();
  }
}

// 加载某天日报并展示
async function loadReport(date){
  addHistory(date);
  currentDate = date;
  reportArea.value = 'Loading...';
  messagesDiv.innerHTML = '';
  try {
    const res = await fetch(`${API_BASE}/api/report?date=${date}`);
    if (!res.ok) throw new Error();
    const md = await res.text();
    reportArea.value = md.trim() ? md : `未找到 ${date} 的日报`;
  } catch {
    reportArea.value = `未找到 ${date} 的日报`;
  }
}

// 刷新当天全流程：爬虫→摘要→切片→索引→报告
async function refreshToday(date) {
  try {
    await fetch(`${API_BASE}/api/refresh?date=${date}`, { method: 'POST' });
    console.log('Data refreshed for', date);
  } catch (e) {
    console.error('Refresh error:', e);
  }
}

// 把消息追加到聊天区
function appendMessage(who, text){
  const div = document.createElement('div');
  div.className = 'message '+who;
  div.textContent = text;
  messagesDiv.append(div);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// 发送按钮逻辑，含命令识别
sendBtn.onclick = async ()=>{
  const text = questionIn.value.trim();
  if(!text) return;

  // 1) 匹配 “X月Y日的报告”
  let m = text.match(/(\d{1,2})月(\d{1,2})日/);
  if(m){
    const year = currentDate.slice(0,4);
    const mm = m[1].padStart(2,'0');
    const dd = m[2].padStart(2,'0');
    const date = `${year}-${mm}-${dd}`;
    appendMessage('user', `查看 ${date} 日报`);
    questionIn.value = '';
    await loadReport(date);
    appendMessage('bot', ` 已切换到 ${date} 的日报`);
    return;
  }

  // 2) 匹配 “YYYY-MM-DD日报” 或纯 “YYYY-MM-DD”
  let iso = text.match(/^(\d{4}-\d{2}-\d{2})(日报)?$/);
  if(iso){
    const date = iso[1];
    appendMessage('user', `查看 ${date} 日报`);
    questionIn.value = '';
    await loadReport(date);
    appendMessage('bot', ` 已切换到 ${date} 的日报`);
    return;
  }

  // 3) 普通提问
  appendMessage('user', text);
  questionIn.value = '';
  // 确保有 currentDate
  if(!currentDate){
    appendMessage('bot', ' 请先加载一个日期的日报');
    return;
  }

  appendMessage('bot', ' 正在生成回答…');
  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method:'POST',
      headers:{ 'Content-Type':'application/json' },
      body: JSON.stringify({ question: text, date: currentDate })
    });
    if(!res.ok) throw new Error(`Server ${res.status}`);
    const { answer } = await res.json();
    appendMessage('bot', answer);
  } catch(e) {
    appendMessage('bot', ` 问答失败：${e.message}`);
  }
};

// 生成海报按钮
makePoster.onclick = async ()=>{
  const file = imageInput.files[0];
  if(!file) return alert('请选择一张图片');
  const fd = new FormData();
  fd.append('date', currentDate);
  fd.append('image', file);
  posterOut.innerHTML = 'Generating poster...';
  try {
    const res = await fetch(`${API_BASE}/api/poster`, { method:'POST', body: fd });
    if(!res.ok) throw new Error(`Server ${res.status}`);
    const { url } = await res.json();
    posterOut.innerHTML = `<img src="${url}" alt="Poster">`;
  } catch(e) {
    posterOut.innerHTML = ` 生成海报失败：${e.message}`;
  }
};

// 初始渲染与加载
renderHistory();
(async ()=>{
  await refreshToday(currentDate);
  await loadReport(currentDate);
})();
