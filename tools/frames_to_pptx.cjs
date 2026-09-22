'use strict';
// Static final-frame PPTX, not editable shapes. HTML remains the source of truth.
const fs=require('node:fs');
const path=require('node:path');
const pptxgen=require('pptxgenjs');
async function main(){
  if(process.argv[2]==='--check')return;
  const [manifestFile,dest]=process.argv.slice(2);
  if(!manifestFile||!dest)throw new Error('Usage: node frames_to_pptx.cjs manifest.json output.pptx');
  const m=JSON.parse(fs.readFileSync(manifestFile,'utf8'));
  if(!Array.isArray(m.slides)||!m.slides.length)throw new Error('No frames');
  const pptx=new pptxgen();pptx.layout='LAYOUT_WIDE';pptx.author='html-slide';pptx.subject='Verified static final frames';pptx.title=m.source;
  for(const record of m.slides){
    const frame=path.resolve(record.frame),data=fs.readFileSync(frame);
    if(data.subarray(0,8).toString('hex')!=='89504e470d0a1a0a'||data.readUInt32BE(16)!==1920||data.readUInt32BE(20)!==1080)throw new Error('Invalid frame: '+frame);
    const slide=pptx.addSlide();slide.addImage({path:frame,x:0,y:0,w:40/3,h:7.5});
    slide.addNotes([record.title||'',...(record.sources||[]).map(s=>`${s.label}: ${s.url}`)]);
  }
  await pptx.writeFile({fileName:dest});
}
main().catch(e=>{console.error(e.message);process.exitCode=2;});
