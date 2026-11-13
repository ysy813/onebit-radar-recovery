const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('C:/Users/yang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const here = path.resolve(__dirname,'..');
async function main() {
  const lesson = JSON.parse(fs.readFileSync(path.join(here,'reports/NETWORK_LEARNING_WALKTHROUGH.json'),'utf8'));
  const browser = await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const errors = [], rows = [];
  try {
    const page = await browser.newPage({viewport:{width:760,height:720}});
    page.on('pageerror',error => errors.push(String(error)));
    await page.goto('file:///'+path.join(here,'reports/network-gain-preview.html').replaceAll('\\','/'));
    const frame = page.frameLocator('iframe');
    await frame.locator('#network-gain-lesson').waitFor();
    for (const scheme of ['light','dark']) {
      await page.emulateMedia({colorScheme:scheme,reducedMotion:'reduce'});
      for (const width of [760,360,320]) {
        await page.setViewportSize({width,height:720});
        for (const stage of [0,1,2,3,4]) {
          await frame.locator('#network-gain-stage').selectOption(String(stage));
          const state = await frame.locator('#network-gain-lesson').evaluate(root => {
            const svg = root.querySelector('svg');
            const bounds = svg.viewBox.baseVal;
            const outside = Array.from(svg.querySelectorAll('text')).filter(text => {
              const raw = text.getBBox();
              const matrix = svg.getScreenCTM().inverse().multiply(text.getScreenCTM());
              const corners = [[raw.x,raw.y],[raw.x+raw.width,raw.y],[raw.x,raw.y+raw.height],[raw.x+raw.width,raw.y+raw.height]]
                .map(([x,y]) => new DOMPoint(x,y).matrixTransform(matrix));
              const xs = corners.map(point => point.x), ys = corners.map(point => point.y);
              return Math.min(...xs)<-1||Math.min(...ys)<-1||Math.max(...xs)>bounds.width+1||Math.max(...ys)>bounds.height+1;
            }).map(text => text.textContent);
            return {stage:Number(root.dataset.stage),gainA:Number(root.dataset.gainA),gainB:Number(root.dataset.gainB),
              marks:Array.from(svg.querySelectorAll('rect[data-value]')).map(rect => ({value:Number(rect.dataset.value),point:rect.dataset.point})),
              horizontalOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,
              labelsOutside:outside,
              minSvgTextSize:Math.min(...Array.from(svg.querySelectorAll('text')).map(node => parseFloat(getComputedStyle(node).fontSize))),
              detail:root.querySelector('#network-gain-detail').textContent,
              selectValue:Number(root.querySelector('select').value),
              rootWidth:root.getBoundingClientRect().width,
              source:'Two previously traced records only'};
          });
          if (state.stage!==stage||state.selectValue!==stage) throw Error('Stage selection failed');
          const points = lesson.visual_payload.points;
          if (state.gainA!==points[0].gains[Math.min(stage,3)]||state.gainB!==points[1].gains[Math.min(stage,3)]) throw Error('Gain mismatch');
          const expected = stage===0 ? Array.from({length:7},(_,i) => points.map(point => point.features_shown[i].value)).flat() :
            Array.from({length:Math.min(stage,3)+1},(_,i) => points.map(point => point.gains[i])).flat();
          if (stage===4) expected.push(...points.map(point=>point.reference_to_input_ratio));
          if (JSON.stringify(state.marks.map(mark => mark.value))!==JSON.stringify(expected)) throw Error('Plotted values differ from saved records');
          if (stage===4 && !points.every(point=>state.detail.includes(point.stage_absolute_errors[1].toPrecision(4))&&state.detail.includes(point.stage_absolute_errors[3].toPrecision(4)))) throw Error('Reference error detail mismatch');
          if (state.horizontalOverflow||state.labelsOutside.length||state.minSvgTextSize<11) throw Error('Layout '+JSON.stringify(state));
          rows.push({scheme,viewport:width,...state});
        }
        const contentHeight=await frame.locator('#network-gain-lesson').evaluate(root=>Math.ceil(root.getBoundingClientRect().height));
        await page.waitForFunction(height=>document.querySelector('iframe').clientHeight>=height,contentHeight);
        await frame.locator('#network-gain-lesson').evaluate(async()=>{await document.fonts.ready;await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
        await page.waitForTimeout(200);
        await page.screenshot({path:path.join(here,'reports',`network-gain-${width}-${scheme}.png`),fullPage:true});
      }
    }
    await frame.locator('#network-gain-lesson').evaluate(root => {
      window.dispatchEvent(new CustomEvent('openai:set_globals',{detail:{globals:{widgetState:{modelContent:{networkGainStage:4}}}}}));
    });
    const restored = await frame.locator('#network-gain-stage').inputValue();
    if (restored!=='4') throw Error('Saved stage restoration failed');
    if (errors.length) throw Error(errors.join('\n'));
    const report = {status:'PASS',scope:'Network teaching interaction, data fidelity and responsive layout only',
      rows,browserErrors:errors,savedStateRestoration:true,pairedReferenceCompared:true,
      modelModified:false,newNeuralInferenceRun:false,boardAccessed:false};
    fs.writeFileSync(path.join(here,'reports/NETWORK_LEARNING_INTERACTIVE_CHECK.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({status:report.status,statesChecked:rows.length,browserErrors:errors,savedStateRestoration:true}));
  } finally {
    await browser.close();
  }
}
main().catch(error => {console.error(error);process.exitCode=1;});
