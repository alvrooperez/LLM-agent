const fs = require('fs');
const path = 'C:/Users/aborb/.minimax-agent/projects/ai-engineer-portfolio/phase-2-rag/slides';
const BAD = /[\u201c\u201d\u2018\u2019\u3001\u3002\uff0c\uff1b\uff1a\uff01\uff1f\uff08\uff09\u2014\u2013\u2026\u00a0]/g;
const M = {
  '\u2014': '-', '\u2013': '-',
  '\u201c': '"', '\u201d': '"',
  '\u2018': "'", '\u2019': "'",
  '\u2026': '...', '\u00a0': ' ',
  '\u3001': ',', '\u3002': '.',
  '\uff0c': ',', '\uff1b': ';',
  '\uff1a': ':', '\uff01': '!',
  '\uff1f': '?', '\uff08': '(', '\uff09': ')'
};
const files = fs.readdirSync(path).filter(f => f.endsWith('.js'));
let fixed = 0;
for (const f of files) {
  const src = fs.readFileSync(path + '/' + f, 'utf8');
  const out = src.replace(BAD, ch => M[ch] || '?');
  if (out !== src) {
    fs.writeFileSync(path + '/' + f, out);
    console.log('Fixed: ' + f);
    fixed++;
  }
}
console.log('Done: ' + fixed + ' files fixed');
