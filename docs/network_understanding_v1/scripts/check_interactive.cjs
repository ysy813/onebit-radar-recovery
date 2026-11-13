const fs=require("node:fs");
const path=require("node:path");
const {chromium}=require("C:/Users/yang/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright");
const here=path.resolve(__dirname,"..");
async function main(){
  const browser=await chromium.launch({headless:true,executablePath:"C:/Program Files/Google/Chrome/Application/chrome.exe"});
  const errors=[],rows=[];
  try{
    const page=await browser.newPage({viewport:{width:760,height:650}});
    page.on("pageerror",e=>errors.push(String(e)));
    await page.goto("file:///"+path.join(here,"reports/onebit-preview.html").replaceAll("\\","/"));
    const frame=page.frameLocator("iframe");
    await frame.locator("#onebit-relative-lesson").waitFor();
    for(const width of [760,360,320]){
      await page.setViewportSize({width,height:650});
      for(const beta of [.1,.3,.6]){
        await frame.locator("#onebit-beta").fill(String(beta));
        await frame.locator("#onebit-beta").dispatchEvent("input");
        const state=await frame.locator("#onebit-relative-lesson").evaluate(el=>{
          const svg=el.querySelector("svg"), vb=svg.viewBox.baseVal;
          const outside=[...svg.querySelectorAll("text")].map(t=>{
            const raw=t.getBBox(),m=svg.getScreenCTM().inverse().multiply(t.getScreenCTM());
            const corners=[[raw.x,raw.y],[raw.x+raw.width,raw.y],[raw.x,raw.y+raw.height],[raw.x+raw.width,raw.y+raw.height]]
              .map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
            const xs=corners.map(p=>p.x),ys=corners.map(p=>p.y);
            return {t:t.textContent,b:{x:Math.min(...xs),y:Math.min(...ys),width:Math.max(...xs)-Math.min(...xs),height:Math.max(...ys)-Math.min(...ys)}};
          })
            .filter(({b})=>b.x< -1||b.y< -1||b.x+b.width>vb.width+1||b.y+b.height>vb.height+1)
            .map(({t})=>t);
          return {beta:Number(el.dataset.beta),quantWeak:Number(el.dataset.quantWeak),
            symbolChange:Number(el.dataset.symbolChange),svgWidth:vb.width,
            noHorizontalOverflow:el.ownerDocument.documentElement.scrollWidth<=el.ownerDocument.documentElement.clientWidth+1,
            labelsOutsideSVG:outside};
        });
        if(beta<1/3&&(Math.abs(state.quantWeak)>1e-10||state.symbolChange!==0))throw Error("Expected identical symbols at "+beta);
        if(beta===.6&&state.symbolChange<=0)throw Error("Expected changed symbols");
        if(!state.noHorizontalOverflow||state.labelsOutsideSVG.length)throw Error("Layout "+JSON.stringify(state));
        rows.push({viewport:width,...state});
      }
      await page.screenshot({path:path.join(here,"reports/interactive-"+width+".png"),fullPage:true});
    }
    await frame.locator("#onebit-ref-toggle").click();
    const toggle=await frame.locator("#onebit-ref-toggle").getAttribute("aria-pressed");
    if(toggle!=="false")throw Error("Legend interaction failed");
    if(errors.length)throw Error(errors.join("\n"));
    const report={status:"PASS",scope:"Teaching visualization runtime and layout only",
      rows,browserErrors:errors,legendToggle:true,modelModified:false,boardAccessed:false};
    fs.writeFileSync(path.join(here,"reports/INTERACTIVE_CHECK.json"),JSON.stringify(report,null,2)+"\n");
    console.log(JSON.stringify(report));
  }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
