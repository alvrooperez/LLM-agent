const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10 x 5.625 inches (16:9 standard)
pres.title = 'AI Engineering Portfolio';
pres.author = 'Alvaro';

// Light editorial palette — Stripe / Linear / Vercel docs inspired
const theme = {
  bg:        'FFFFFF',  // pure white
  surface:   'F8FAFC',  // very light gray
  border:    'E2E8F0',  // soft border
  text:      '0A2540',  // deep navy — primary text
  textSoft:  '64748B',  // slate — secondary text
  accent:    '0066FF',  // electric blue
  accentSoft:'EFF6FF',  // very light blue
  success:   '10B981',  // emerald
  warning:   'F59E0B',  // amber
  divider:   'CBD5E1',  // mid gray
};

const slides = [
  require('./slide-01-cover.js'),
  require('./slide-02-toc.js'),
  require('./slide-03-hero.js'),
  require('./slide-04-architecture.js'),
  require('./slide-05-rag.js'),
  require('./slide-06-rag-results.js'),
  require('./slide-07-finetuning.js'),
  require('./slide-08-finetuning-results.js'),
  require('./slide-09-agent.js'),
  require('./slide-10-performance.js'),
  require('./slide-11-auth.js'),
  require('./slide-12-closing.js'),
];

for (const mod of slides) {
  mod.createSlide(pres, theme);
}

pres.writeFile({ fileName: 'C:/Users/aborb/.minimax-agent/projects/ai-engineer-portfolio/app/slides/output/ai-engineering-portfolio.pptx' })
  .then(() => console.log('Written: output/ai-engineering-portfolio.pptx'))
  .catch(e => { console.error(e); process.exit(1); });
