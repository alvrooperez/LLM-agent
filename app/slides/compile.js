const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';

// Tech & Night palette (deep blue + gold)
const theme = {
  primary:   'ffd60a',   // Gold - main text on dark bg
  secondary: '9a8c98',   // Muted - secondary text
  accent:    'ffc300',   // Bright gold - accents, highlights
  light:     '001d3d',   // Card/panel background
  bg:        '000814',   // Slide background
};

const slides = [
  require('./slide-01.js'),
  require('./slide-02.js'),
  require('./slide-03.js'),
  require('./slide-04.js'),
  require('./slide-05.js'),
  require('./slide-06.js'),
  require('./slide-07.js'),
  require('./slide-08.js'),
  require('./slide-09.js'),
  require('./slide-10.js'),
  require('./slide-11.js'),
  require('./slide-12.js'),
  require('./slide-13.js'),
  require('./slide-14.js'),
];

for (const mod of slides) {
  mod.createSlide(pres, theme);
}

pres.writeFile({ fileName: 'C:/Users/aborb/.minimax-agent/projects/ai-engineer-portfolio/phase-2-rag/slides/output/ai-engineering-portfolio.pptx' })
  .then(() => console.log('Written: output/ai-engineering-portfolio.pptx'))
  .catch(e => { console.error(e); process.exit(1); });
