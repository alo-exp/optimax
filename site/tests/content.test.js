import test from 'node:test';
import assert from 'node:assert/strict';
import {buildContent} from '../src/content.js';
const sample={articles:[{slug:'install',title:'Install',category:'Start',description:'Begin',keywords:['setup'],sections:[{heading:'Get started',paragraphs:['Use <script> safely'],bullets:['One']}]}]};
test('generates escaped pages and searchable matching anchors',()=>{
 const {pages,index}=buildContent(sample);
 assert.equal(pages[0].url,'/help/install/');
 assert.match(pages[0].html,/id="get-started"/);
 assert.match(pages[0].html,/&lt;script&gt;/);
 assert.deepEqual(index[0],{page:'Install',url:'/help/install/',anchor:'get-started',title:'Get started',text:'Begin setup Use <script> safely One'});
});
test('rejects invalid paths, duplicate slugs and duplicate anchors',()=>{
 assert.throws(()=>buildContent({articles:[{...sample.articles[0],slug:'../x'}]}));
 assert.throws(()=>buildContent({articles:[sample.articles[0],sample.articles[0]]}));
 assert.throws(()=>buildContent({articles:[{...sample.articles[0],sections:[sample.articles[0].sections[0],sample.articles[0].sections[0]]}]}));
});
