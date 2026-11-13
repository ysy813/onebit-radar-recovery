// Teaching geometry only; no radar arrays, feature extraction or neural inference.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { chromium } = require('C:/Users/yang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const here = path.resolve(__dirname,'..');
const project = path.resolve(here,'..');
const visual = 'C:/Users/yang/.codex/visualizations/2026/10/31/01a19048-6a4d-7101-874c-4be4ef20d10a/harmonic-query-map.html';
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const mod = (v,n) => ((v%n)+n)%n;
function inverse(h,n) { for(let i=1;i<n;i++) if(mod(h*i,n)===1) return i; throw Error('No inverse'); }
function expected(r,a,h,direction) {
  const child=[mod(h*r,1024),mod(h*a,512)];
  const exact=[mod(inverse(h,1024)*r,1024),mod(inverse(h,512)*a,512)];
  const support=new Set();
  const bound=(3*Math.abs(h)-1)/2;
  if(direction==='parent') {
    for(let er=-bound;er<=bound;er++) for(let ea=-bound;ea<=bound;ea++)
      support.add(`${mod(inverse(h,1024)*(r+er),1024)},${mod(inverse(h,512)*(a+ea),512)}`);
  } else {
    for(let dr=-1;dr<=1;dr++) for(let da=-1;da<=1;da++)
      support.add(`${mod(child[0]+dr,1024)},${mod(child[1]+da,512)}`);
  }
  return {child,exact,support};
}
function assert(ok,message) { if(!ok) throw Error(message); }
async function main() {
  const sourceReport=JSON.parse(fs.readFileSync(path.join(here,'reports/PARENT_QUERY_WALKTHROUGH.json'),'utf8'));
  assert(sourceReport.status==='PASS','Prerequisite source-coordinate check');
  for(const [file,hash] of Object.entries(sourceReport.source_sha256)) assert(sha(path.join(project,file))===hash,`Source changed: ${file}`);
  const literal=fs.readFileSync(visual,'utf8');
  assert(!literal.includes('\\n')&&!literal.includes('\\"'),'Escaped markup');
  assert(!/<(?:html|head|body)\b/i.test(literal),'Must remain a fragment');
  const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
  const errors=[], rows=[], geometryRows=[];
  try {
    const page=await browser.newPage({viewport:{width:760,height:900}});
    page.on('pageerror',error=>errors.push(String(error)));
    await page.goto('file:///'+path.join(here,'reports/harmonic-query-preview.html').replaceAll('\\','/'));
    const frame=page.frameLocator('iframe');
    const root=frame.locator('#harmonic-query-map');
    await root.waitFor();
    await root.evaluate(()=>{window.__saved=[];window.openai.setWidgetState=snapshot=>{window.__saved.push(snapshot);return Promise.resolve();};});
    async function setState(r,a,h,direction) {
      await root.evaluate((_,state)=>window.dispatchEvent(new CustomEvent('openai:set_globals',{detail:{globals:{widgetState:{modelContent:{harmonicQuery:state}}}}})),{r,a,h,direction});
      return await root.evaluate(node=>node.__geometry);
    }
    const points=[[0,0],[1023,511],[774,511],[131,37],[631,401],[472,208],[83,0],[511,255]];
    for(const h of [-3,5]) for(const direction of ['parent','child']) for(const [r,a] of points) {
      const actual=await setState(r,a,h,direction), ref=expected(r,a,h,direction);
      const support=new Set(actual.queries.map(p=>`${p.r},${p.a}`));
      assert(JSON.stringify(actual.child)===JSON.stringify(ref.child),'Child mismatch');
      assert(JSON.stringify(actual.exact)===JSON.stringify(ref.exact),'Exact inverse mismatch');
      assert(actual.queries.length===ref.support.size&&support.size===ref.support.size&&[...ref.support].every(p=>support.has(p)),'Full support set mismatch');
      if(direction==='parent') {
        assert(support.has(ref.exact.join(',')),'Exact inverse absent');
        for(const p of actual.queries) {
          const residual=[mod(h*p.r-r+512,1024)-512,mod(h*p.a-a+256,512)-256];
          assert(JSON.stringify(residual)===JSON.stringify(p.residual),'Residual mismatch');
        }
      }
      geometryRows.push({r,a,h,direction,supportCount:support.size,exact:actual.exact,child:actual.child,fullSetMatches:true});
    }
    let actual=await setState(774,511,-3,'parent');
    assert(JSON.stringify(actual.exact)==='[766,171]'&&JSON.stringify(actual.record)==='[83,0]','Existing trace mismatch');
    const winner=actual.queries.find(p=>p.r===83&&p.a===0);
    assert(winner&&JSON.stringify(winner.residual)==='[1,1]','Existing maximum support missing');
    assert(JSON.stringify(expected(131,37,-3,'child').child)==='[631,401]','Third theory example');
    assert(JSON.stringify(expected(131,37,5,'child').child)==='[655,185]','Fifth theory example');
    assert(await root.evaluate(()=>window.__saved.length===0),'Restoration must not save');
    await frame.locator('#hq-theory').click();
    actual=await root.evaluate(node=>node.__geometry);
    assert(actual.state.r===131&&actual.state.a===37&&actual.state.direction==='child','Theory preset');
    assert(await frame.locator('#hq-exact-key').isHidden()&&await frame.locator('#hq-record-key').isHidden(),'Legend hiding');
    await frame.locator('#hq-r').fill('-9');await frame.locator('#hq-r').press('Tab');
    assert(await frame.locator('#hq-r').inputValue()==='0','Lower bound');
    await frame.locator('#hq-a').fill('900');await frame.locator('#hq-a').press('Tab');
    assert(await frame.locator('#hq-a').inputValue()==='511','Upper bound');
    await frame.locator('#hq-r').fill('1029');await frame.locator('#hq-r').press('Tab');
    assert(await frame.locator('#hq-r').inputValue()==='1023','Range upper bound');
    await frame.locator('#hq-a').fill('-3');await frame.locator('#hq-a').press('Tab');
    assert(await frame.locator('#hq-a').inputValue()==='0','Doppler lower bound');
    await frame.locator('#hq-h').selectOption('5');
    await frame.locator('#hq-direction').selectOption('parent');
    actual=await root.evaluate(node=>node.__geometry);
    assert(actual.supportCount===225&&actual.state.h===5&&actual.state.direction==='parent','Select interaction');
    const saved=await root.evaluate(()=>window.__saved.at(-1));
    assert(saved.modelContent.harmonicQuery.h===5,'Saved state');
    await frame.locator('#hq-existing').click();
    await root.evaluate((_,snapshot)=>window.dispatchEvent(new CustomEvent('openai:set_globals',{detail:{globals:{widgetState:snapshot}}})),saved);
    actual=await root.evaluate(node=>node.__geometry);
    assert(actual.state.h===5&&actual.state.r===1023&&actual.state.a===0,'Restore saved selection');
    for(const scheme of ['light','dark']) {
      await page.emulateMedia({colorScheme:scheme,reducedMotion:'reduce'});
      for(const width of [760,360,320]) {
        await page.setViewportSize({width,height:900});
        for(const h of [-3,5]) for(const direction of ['parent','child']) {
          await setState(774,511,h,direction);
          const state=await root.evaluate(node=>{
            const svg=node.querySelector('svg'), view=svg.viewBox.baseVal;
            const boxes=Array.from(svg.querySelectorAll('text')).map(text=>{
              const raw=text.getBBox(), matrix=svg.getScreenCTM().inverse().multiply(text.getScreenCTM());
              const p=[[raw.x,raw.y],[raw.x+raw.width,raw.y],[raw.x,raw.y+raw.height],[raw.x+raw.width,raw.y+raw.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(matrix));
              return {text:text.textContent,x0:Math.min(...p.map(v=>v.x)),y0:Math.min(...p.map(v=>v.y)),x1:Math.max(...p.map(v=>v.x)),y1:Math.max(...p.map(v=>v.y))};
            });
            const outside=boxes.filter(p=>p.x0<0||p.y0<0||p.x1>view.width||p.y1>view.height);
            const collisions=[];
            for(let i=0;i<boxes.length;i++) for(let j=i+1;j<boxes.length;j++) {
              const a=boxes[i],b=boxes[j];
              if(Math.min(a.x1,b.x1)-Math.max(a.x0,b.x0)>-4&&Math.min(a.y1,b.y1)-Math.max(a.y0,b.y0)>-4) collisions.push([a.text,b.text]);
            }
            const frame=svg.querySelector('[data-chart-frame]').getBBox();
            const marksOutside=Array.from(svg.querySelectorAll('[data-kind]')).filter(mark=>{
              const p=mark.getBBox(), matrix=svg.getScreenCTM().inverse().multiply(mark.getScreenCTM());
              const a=new DOMPoint(p.x,p.y).matrixTransform(matrix),b=new DOMPoint(p.x+p.width,p.y+p.height).matrixTransform(matrix);
              return a.x<frame.x||a.y<frame.y||b.x>frame.x+frame.width||b.y>frame.y+frame.height;
            }).length;
            return {horizontalOverflow:document.documentElement.scrollWidth>document.documentElement.clientWidth+1,labelsOutside:outside,labelCollisions:collisions,marksOutside,
              minSvgTextSize:Math.min(...Array.from(svg.querySelectorAll('text')).map(p=>parseFloat(getComputedStyle(p).fontSize))),
              svgWidth:svg.getBoundingClientRect().width,viewBoxWidth:view.width,supportCount:node.__geometry.supportCount};
          });
          assert(!state.horizontalOverflow&&!state.labelsOutside.length&&!state.labelCollisions.length&&!state.marksOutside&&state.minSvgTextSize>=11,'Layout '+JSON.stringify(state));
          assert(Math.abs(state.svgWidth-state.viewBoxWidth)<1,'Responsive viewBox');
          rows.push({scheme,width,h,direction,...state});
        }
        await setState(774,511,-3,'parent');
        const contentHeight=await root.evaluate(node=>Math.ceil(node.getBoundingClientRect().bottom)+20);
        await page.locator('iframe').evaluate((node,height)=>{node.style.height=`${height}px`;},contentHeight);
        await page.screenshot({path:path.join(here,'reports',`harmonic-query-${width}-${scheme}.png`),fullPage:true});
      }
    }
    // Test nearest-point overlay and persistent pointer selection at the trace winner.
    await page.setViewportSize({width:760,height:900});
    await setState(774,511,-3,'parent');
    const record=frame.locator('[data-kind="record"]');
    const box=await record.boundingBox();
    await page.mouse.click(box.x+box.width/2,box.y+box.height/2);
    assert(await frame.locator('.hq-tooltip').isVisible(),'Tooltip missing');
    assert((await frame.locator('.hq-tooltip').textContent()).includes('(83,0)'),'Nearest winner tooltip');
    await page.mouse.move(0,0);
    assert(await frame.locator('.hq-tooltip').isVisible(),'Pinned tooltip vanished');
    assert(!errors.length,errors.join('\n'));
    const sourceFiles=['network_understanding_v1/reports/PARENT_QUERY_WALKTHROUGH.json',...Object.keys(sourceReport.source_sha256)];
    const report={status:'PASS',scope:'Frozen coordinate-query teaching; no new restoration-quality evidence',
      visual_path:visual,visual_sha256:sha(visual),source_sha256:Object.fromEntries(sourceFiles.map(file=>[file,sha(path.join(project,file))])),
      geometry_cases:geometryRows,layout_cases:rows,browserErrors:errors,
      full_support_sets_match_independent_modular_inverse:true,existing_record_matches:true,
      input_bounds_and_presets:true,saved_state_restoration:true,legend_visibility:true,pointer_selection:true,
      model_parameters_modified:false,training_run:false,radar_fft_run:false,feature_extraction_run:false,neural_inference_run:false,new_quality_test_run:false,board_accessed:false};
    fs.writeFileSync(path.join(here,'reports/HARMONIC_QUERY_INTERACTIVE_CHECK.json'),JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({status:report.status,geometryCases:geometryRows.length,layoutCases:rows.length,browserErrors:errors}));
  } finally { await browser.close(); }
}
main().catch(error=>{console.error(error);process.exitCode=1;});
