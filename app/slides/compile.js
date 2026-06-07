const pptxgen = require('pptxgenjs');
const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';

// Modern Tech & Cyberpunk palette (Space Dark + Neon Cyan + Clean Slate)
const theme = {
  primary:   'F8FAFC',   // Clean Off-white - main text
  secondary: '94A3B8',   // Slate Gray - secondary text
  accent:    '00EAFF',   // Neon Cyan - accents and highlights
  accent2:   'BD00FF',   // Neon Purple - accents
  light:     '0F172A',   // Slate Blue - card/panel background
  bg:        '020617',   // Deepest Space Blue - slide background
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

pres.writeFile({ fileName: 'C:/Users/aborb/.minimax-agent/projects/ai-engineer-portfolio/app/slides/output/ai-engineering-portfolio.pptx' })
  .then(() => console.log('Written: output/ai-engineering-portfolio.pptx'))
  .catch(e => { console.error(e); process.exit(1); });
